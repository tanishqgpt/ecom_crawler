import asyncio
import logging
import random
import threading
import aiohttp
import os
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from .config import PRODUCT_PATTERNS, MAX_DEPTH, REQUEST_TIMEOUT, OUTPUT_JSON

logger = logging.getLogger(__name__)

class DomainCrawler:
    """
    Crawls a single domain, respecting robots.txt, picking a user agent,
    rate-limiting requests, handling 429 errors, and writing discovered product URLs
    to JSON in real time. Now includes a thread lock for file writes.
    """

    # A static (class-level) lock shared by all instances of DomainCrawler
    _file_write_lock = threading.Lock()

    def __init__(self, domain: str):
        parsed = urlparse(domain)
        self.scheme = parsed.scheme or "http"
        if parsed.netloc:
            self.base_netloc = parsed.netloc
        else:
            self.base_netloc = parsed.path

        # We'll store just the domain as the key
        self.domain = self.base_netloc
        self.base_url = f"{self.scheme}://{self.base_netloc}"

        logger.info(f"[DomainCrawler] Initialized crawler for domain: {self.domain}")

        self.visited_urls = set()
        self.product_urls = set()
        self.cache = {}
        self.robot_parser = RobotFileParser()
        self.effective_user_agent = None

    async def crawl(self):
        logger.info(f"[DomainCrawler] Starting crawl for domain: {self.domain}")
        await self._load_and_parse_robots_txt()
        async with aiohttp.ClientSession() as session:
            await self._crawl_url(self.base_url, depth=0, session=session)
        logger.info(f"[DomainCrawler] Finished crawl for domain: {self.domain}")

    async def _crawl_url(self, url: str, depth: int, session: aiohttp.ClientSession):
        if url in self.visited_urls:
            logger.debug(f"[DomainCrawler] Already visited: {url}")
            return
        if depth > MAX_DEPTH:
            logger.debug(f"[DomainCrawler] Max depth exceeded at: {url}")
            return

        if not self._can_fetch(url):
            logger.debug(f"[DomainCrawler] Disallowed by robots.txt: {url}")
            return

        self.visited_urls.add(url)
        logger.debug(f"[DomainCrawler] Fetching URL: {url} (depth={depth})")

        html_content = await self._fetch(url, session)
        if not html_content:
            logger.debug(f"[DomainCrawler] No HTML content returned for: {url}")
            return

        soup = BeautifulSoup(html_content, 'html.parser')
        for link_tag in soup.find_all('a', href=True):
            href = link_tag['href']
            absolute_url = urljoin(url, href)
            parsed_url = urlparse(absolute_url)

            # Follow only within the same domain
            if self.base_netloc not in parsed_url.netloc:
                logger.debug(f"[DomainCrawler] Skipping external link: {absolute_url}")
                continue

            # Check if it's a product URL
            if self._is_product_url(absolute_url):
                logger.info(f"[DomainCrawler] Product URL found: {absolute_url}")
                self.product_urls.add(absolute_url)
                self._write_realtime_result(absolute_url)

            await self._crawl_url(absolute_url, depth + 1, session)

    async def _fetch(self, url: str, session: aiohttp.ClientSession) -> str:
        if url in self.cache:
            logger.debug(f"[DomainCrawler] Cache hit: {url}")
            return self.cache[url]

        # rate-limit: random delay
        delay = random.uniform(1, 2)
        logger.debug(f"[DomainCrawler] Sleeping {delay:.2f}s before request to {url}")
        await asyncio.sleep(delay)

        max_retries = 3
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                headers = {"User-Agent": self.effective_user_agent or "MyDefaultAgent/1.0"}
                async with session.get(url, timeout=REQUEST_TIMEOUT, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        self.cache[url] = html
                        return html
                    elif response.status == 429:
                        retry_after = response.headers.get("Retry-After", "5")
                        logger.warning(
                            f"[DomainCrawler] 429 at {url}; waiting {retry_after}s "
                            f"before retry (attempt {attempt}/{max_retries})..."
                        )
                        await asyncio.sleep(int(retry_after))
                    else:
                        logger.warning(f"[DomainCrawler] Non-200 status {response.status} for {url}")
                        break
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"[DomainCrawler] Error fetching {url} (attempt {attempt}/{max_retries}): {e}")
                await asyncio.sleep(2)
        return ""

    def _is_product_url(self, url: str) -> bool:
        for pattern in PRODUCT_PATTERNS:
            if pattern in url:
                return True
        return False

    def get_product_urls(self) -> list:
        return sorted(self.product_urls)

    def _can_fetch(self, url: str) -> bool:
        if not self.effective_user_agent or not self.robot_parser.default_entry:
            return True
        return self.robot_parser.can_fetch(self.effective_user_agent, url)

    async def _load_and_parse_robots_txt(self):
        robots_url = f"{self.scheme}://{self.base_netloc}/robots.txt"
        logger.info(f"[DomainCrawler] Attempting to fetch robots.txt from {robots_url}")

        try:
            self.robot_parser.set_url(robots_url)
            self.robot_parser.read()
        except Exception as e:
            logger.warning(f"[DomainCrawler] Failed to load robots.txt for {self.domain}: {e}")
            return

        raw_robots = ""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url, timeout=5) as resp:
                    if resp.status == 200:
                        raw_robots = await resp.text()
        except Exception as e:
            logger.warning(f"[DomainCrawler] Could not manually fetch robots.txt for {self.domain}: {e}")

        chosen_agent = None
        potential_agents = []
        for line in raw_robots.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("user-agent:"):
                agent_value = line.split(":", 1)[1].strip()
                potential_agents.append(agent_value)

        if any("*" == ua or ua.lower() == "*" for ua in potential_agents):
            chosen_agent = "*"
        elif potential_agents:
            chosen_agent = potential_agents[0]
        else:
            chosen_agent = "*"

        self.effective_user_agent = chosen_agent
        logger.info(
            f"[DomainCrawler] Chose user-agent '{self.effective_user_agent}' based on {robots_url}"
        )

    def _write_realtime_result(self, product_url: str):
        
        """
        Immediately update output.json whenever a new product is found.
         a lock to prevent race conditions in a multi-thread scenario.
        """
        logger.info(f"[DomainCrawler] Updating {OUTPUT_JSON} with new product: {product_url}")

        # Acquire the class-level lock before reading/writing the file
        with self._file_write_lock:
            try:
                # 1) Load existing JSON
                if os.path.isfile(OUTPUT_JSON):
                    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                else:
                    existing_data = {}

                # 2) Append the product to this domain’s list
                if self.domain not in existing_data:
                    existing_data[self.domain] = []

                # Avoid duplicates
                if product_url not in existing_data[self.domain]:
                    existing_data[self.domain].append(product_url)

                # 3) Write back
                with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                    json.dump(existing_data, f, indent=4)

            except Exception as e:
                logger.error(f"[DomainCrawler] Failed to write {product_url} to {OUTPUT_JSON}: {e}")
