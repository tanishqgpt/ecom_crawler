"""
Global configuration settings for the product URL crawler.
Adjust these to match your needs.
"""

PRODUCT_PATTERNS = [
    r'pd_rd_r',
    r'iid=',
]

# Outfile 
OUTPUT_JSON = 'product_urls.json'
# Maximum crawl depth: how many "hops" from the initial page the crawler will follow.
MAX_DEPTH = 4

# Timeout for each HTTP request (in seconds).
REQUEST_TIMEOUT = 10
