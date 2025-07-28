import requests
import random

class PlaywrightProxyMiddleware:
    def __init__(self):
        self.proxy = None
        self.request_counter = 0
        self.rotate_every = 50
        self.failed_fetch_attempts = 0
        self.max_fetch_attempts = 3
        self.proxy_pool = []

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        if "playwright" in request.meta:
            self.request_counter += 1

            if not self.proxy or self.request_counter >= self.rotate_every:
                self.proxy = self.fetch_random_proxy()
                self.request_counter = 0

            if self.proxy:
                request.meta["playwright_browser_context_args"] = {
                    "proxy": {"server": self.proxy}
                }

    def fetch_random_proxy(self):
        attempts = 0
        while attempts < self.max_fetch_attempts:
            try:
                # Only fetch new proxy list if pool is empty
                if not self.proxy_pool:
                    print("[Proxy] Fetching new proxy list...")
                    response = requests.get("https://www.proxy-list.download/api/v1/get?type=http", timeout=10)
                    if response.status_code == 200:
                        self.proxy_pool = [
                            f"http://{proxy.strip()}"
                            for proxy in response.text.splitlines()
                            if proxy.strip()
                        ]
                        print(f"[Proxy] Loaded {len(self.proxy_pool)} proxies.")

                if self.proxy_pool:
                    proxy = random.choice(self.proxy_pool)
                    print(f"[Proxy] Rotated to: {proxy}")
                    return proxy

            except Exception as e:
                attempts += 1
                print(f"[Proxy] Attempt {attempts} failed: {e}")

        print("[Proxy] Failed to get proxy after retries. Reusing last known proxy.")
        return self.proxy
