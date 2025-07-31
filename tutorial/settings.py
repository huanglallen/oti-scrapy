# Scrapy settings for tutorial project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import os

BOT_NAME = "tutorial"

SPIDER_MODULES = ["tutorial.spiders"]
NEWSPIDER_MODULE = "tutorial.spiders"

ROBOTSTXT_OBEY = False
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.129 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1"
}

DOWNLOAD_TIMEOUT = 600

# Prevent early closure due to inactivity
CLOSESPIDER_TIMEOUT = 0  # no auto-close timeout
CLOSESPIDER_PAGECOUNT = 0  # no limit on page count

# Optional: limit concurrency to avoid overloading
# CONCURRENT_REQUESTS = 4
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000  # 60 seconds

#playwright tags
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# Enable the middleware to launch browser
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
PLAYWRIGHT_BROWSER_TYPE = "chromium"  # optional (chromium / firefox / webkit)
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,  # <-- KEY CHANGE
    "slow_mo": 250,     # Optional, to mimic real user
    "args": ["--start-maximized"]
}

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"

DOWNLOADER_MIDDLEWARES = {
    'tutorial.middlewares.PlaywrightProxyMiddleware': 543,
    'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
}

LOG_ENABLED = True
LOG_LEVEL = 'DEBUG'  # or 'INFO', 'WARNING', etc.
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'log.txt')

LOG_ENABLED = True
LOG_LEVEL = 'DEBUG'  # or 'INFO' to reduce verbosity
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'log.txt')
