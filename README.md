# Product URL Crawler

This repository provides a **modular**, **object-oriented**, and **configurable** web crawler for discovering product URLs from multiple e-commerce sites. The core components are:

- **Crawler Configuration** (`crawler/config.py`):  
  Defines product URL patterns (e.g., `/product/`, `/item/`, `/p/`), maximum crawl depth, timeouts, etc.

- **Domain Crawler** (`crawler/domain_crawler.py`):  
  A class that handles crawling a single domain, following internal links up to a certain depth and collecting product URLs.

- **Crawler Manager** (`crawler/crawler_manager.py`):  
  Coordinates multiple domain crawlers concurrently using `asyncio` for performance and scalability.

## Installation

1. **Clone the Repository**
    ```bash
    git clone https://github.com/tanishqgpt/ecom_crawler.git
    cd ecom_crawler
    ```
2. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```
3. **Usage**
    ```bash
    # Option A: Provide domains as command-line arguments
    python main.py example1.com example2.com

    # Option B: Hard-code domains in main.py if you prefer
    python main.py
    ```
4. **Output**
    - The crawler will output a structured JSON file (named `product_urls.json` by default) that maps each domain to the list of discovered product URLs.
    - It will also print the discovered URLs to the console.

## Customization

- **Add/Modify Product URL Patterns**  
  In `crawler/config.py`, edit `PRODUCT_PATTERNS` to detect different or additional patterns (e.g., `/goods/`, `/store/`, etc.).
  
- **Adjust Depth**  
  In `crawler/config.py`, modify `MAX_DEPTH` to control how many levels of internal links are visited.

- **Handle Dynamic Websites**  
  This solution fetches static HTML. For infinite scrolling or JavaScript-heavy sites, you might need to integrate a headless browser (e.g., Selenium or Playwright).  
  1. Store the JavaScript-rendered HTML using a headless browser.  
  2. Pass the HTML to the same parsing logic in `DomainCrawler`.


