import asyncio
import logging

from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

from crawler.domain_crawler import DomainCrawler

logger = logging.getLogger(__name__)

def _crawl_domain_sync(domain: str):
    """
    Runs DomainCrawler for a single domain in its own event loop 
    (since DomainCrawler is async).
    
    :return: (domain, list_of_product_urls)
    """
    logger.info(f"[_crawl_domain_sync] Starting domain: {domain}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    crawler = DomainCrawler(domain)
    loop.run_until_complete(crawler.crawl())
    product_urls = crawler.get_product_urls()
    loop.close()

    logger.info(f"[_crawl_domain_sync] Finished domain: {domain} (found {len(product_urls)} products)")
    return domain, product_urls

class CrawlerManager:
    """
    Manages crawling across multiple domains in parallel using multiprocessing.
    """

    def __init__(self, domains: list, max_workers: int = None):
        """
        :param domains: List of domain strings to crawl.
        :param max_workers: Number of processes (defaults to CPU count).
        """
        self.domains = domains
        self.results = {}
        self.max_workers = max_workers or multiprocessing.cpu_count()

        logger.info(f"[CrawlerManager] Initialized with {len(domains)} domain(s), max_workers={self.max_workers}")

    def run_crawler(self):
        """
        Crawls all domains in parallel using a ProcessPoolExecutor. 
        Aggregates partial results in real time.
        """
        logger.info("[CrawlerManager] run_crawler started")
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_domain = {
                executor.submit(_crawl_domain_sync, domain): domain
                for domain in self.domains
            }

            # Collect results as soon as each domain finishes
            for future in as_completed(future_to_domain):
                domain = future_to_domain[future]
                try:
                    dom, product_urls = future.result()
                    self.results[dom] = product_urls
                    logger.info(f"[CrawlerManager] Domain completed: {dom}, products found: {len(product_urls)}")
                except Exception as exc:
                    logger.error(f"[CrawlerManager] {domain} raised an exception: {exc}")

        logger.info("[CrawlerManager] run_crawler finished")

    def get_results(self) -> dict:
        """
        Return the aggregated {domain: [product_urls]} after all crawls complete.
        """
        return self.results
