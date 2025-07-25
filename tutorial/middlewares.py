# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from tutorial import signals
from itemadapter import is_item, ItemAdapter
import requests


class TutorialSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class TutorialDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)

class PlaywrightProxyMiddleware:

    def __init__(self):
        self.proxy = None
        self.request_counter = 0
        self.rotate_every = 50
        self.failed_fetch_attempts = 0
        self.max_fetch_attempts = 3

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        if "playwright" in request.meta:
            self.request_counter += 1

            if not self.proxy or self.request_counter >= self.rotate_every:
                self.proxy = self.fetch_gimmeproxy()
                self.request_counter = 0

            if self.proxy:
                request.meta["playwright_browser_context_args"] = {
                    "proxy": {"server": self.proxy}
                }

    def fetch_gimmeproxy(self):
        attempts = 0
        while attempts < self.max_fetch_attempts:
            try:
                response = requests.get("https://gimmeproxy.com/api/getProxy?protocol=http&supportsHttps=true&anonymityLevel=elite", timeout=10)
                if response.status_code == 200:
                    proxy = response.json().get("ipPort")
                    if proxy:
                        print(f"[Proxy] Rotated to new proxy: {proxy}")
                        return f"http://{proxy}"
            except Exception as e:
                attempts += 1
                print(f"[Proxy] Attempt {attempts}: Failed to fetch proxy: {e}")

        print("[Proxy] Failed to fetch proxy after retries. Reusing last proxy if available.")
        return self.proxy  # fallback to existing proxy