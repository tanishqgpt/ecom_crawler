import sys
import json
import os
import logging

from concurrent.futures import ProcessPoolExecutor, as_completed
from crawler.config import OUTPUT_JSON
from crawler.crawler_manager import CrawlerManager, _crawl_domain_sync

OUTPUT_FILE = OUTPUT_JSON

def setup_logging():
    """
    Configure Python's built-in logging with a basic format to stdout.
    You can adjust logging level, formatting, or use FileHandler, etc.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s - %(message)s"
    )

def read_existing_json(filepath: str) -> dict:
    """
    Read an existing JSON file if it exists, or return an empty dict.
    """
    if os.path.isfile(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def write_partial_results(domain: str, product_urls: list):
    """
    Write partial results to output.json in real time:
    1) Reads the current JSON (if any),
    2) Updates with the new domain's results,
    3) Writes it back to disk.
    """
    existing_data = read_existing_json(OUTPUT_FILE)
    existing_data[domain] = sorted(product_urls)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=4)

def main():
    """
    Entry point. 
    Usage:
        python main.py example1.com example2.com ...
    If no domains are provided, a default list is used.
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    if len(sys.argv) > 1:
        domains = sys.argv[1:]
    else:
        # Default domains if none are provided
        domains = [
            "amazon.com",
            "flipkart.com",
            "snapdeal.com"
        ]

    logger.info("Script started with domains: %s", domains)

    # Clear or create output.json so we start fresh
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)
    logger.info("Initialized empty output file: %s", OUTPUT_FILE)

    manager = CrawlerManager(domains=domains, max_workers=4)
    logger.info("Starting concurrent crawling...")

    # Manage partial writes ourselves to get real-time updates in output.json
    with ProcessPoolExecutor(max_workers=manager.max_workers) as executor:
        future_to_domain = {
            executor.submit(_crawl_domain_sync, domain): domain
            for domain in domains
        }

        for future in as_completed(future_to_domain):
            domain = future_to_domain[future]
            try:
                finished_domain, product_urls = future.result()
                manager.results[finished_domain] = product_urls

                # Real-time JSON write
                write_partial_results(finished_domain, product_urls)
                logger.info("[main] %s finished with %d products, partial results written.",
                            finished_domain, len(product_urls))
            except Exception as exc:
                logger.error("[main] %s generated an exception: %s", domain, exc)

    # After all domains are done
    logger.info("All domains have been crawled. Final results:")
    for d, urls in manager.results.items():
        logger.info("- %s: %d product URLs", d, len(urls))

if __name__ == "__main__":
    main()
