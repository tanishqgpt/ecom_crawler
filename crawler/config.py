"""
Global configuration settings for the product URL crawler.
"""

PRODUCT_PATTERNS = [
    r'pd_rd_r', # pattern for amazon
    r'iid=', #flipkart
    r'[0-9]{6,10}/buy',
    r'product/[^/]+/[0-9]{7,}', #snapdeal 
    r'/p/[0-9]{7,}'
]

# Outfile 
OUTPUT_JSON = 'product_urls.json'
# Maximum crawl depth: how many "hops" from the initial page the crawler will follow.
MAX_DEPTH = 4

# Timeout for each HTTP request (in seconds).
REQUEST_TIMEOUT = 10
