import requests
import re
import os

class PlaywrightProxyMiddleware:
    def __init__(self):
        self.proxies = self.load_proxies_from_file()
        self.proxy_index = 0
        self.request_counter = 0
        self.rotate_every = 30

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        if "playwright" in request.meta:
            self.request_counter += 1

            # Rotate proxy every N requests
            if self.request_counter >= self.rotate_every or not self.proxies:
                self.rotate_proxy()
                self.request_counter = 0

            current_proxy = self.proxies[self.proxy_index]
            request.meta["playwright_browser_context_args"] = {
                "proxy": {"server": current_proxy}
            }

            # Get current IP via external check
            ip = self.get_current_ip()

            # Get User-Agent from request headers or fallback
            user_agent = request.headers.get("User-Agent")
            if user_agent:
                user_agent = user_agent.decode('utf-8')
            else:
                user_agent = "N/A"

            if ip and spider:
                spider.logger.info(f"[Proxy] Using proxy: {current_proxy} | External IP: {ip} | User-Agent: {user_agent}")

    def load_proxies_from_file(self):
        # Look for proxy-list.txt in the project root
        proxy_file = os.path.join(os.path.dirname(__file__), '..', 'proxy-list.txt')
        if not os.path.exists(proxy_file):
            raise FileNotFoundError("proxy-list.txt not found in root directory.")

        with open(proxy_file, 'r') as f:
            proxies = [f"http://{line.strip()}" for line in f if line.strip()]
        if not proxies:
            raise ValueError("proxy-list.txt is empty.")
        return proxies

    def rotate_proxy(self):
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)

    def get_current_ip(self):
        try:
            response = requests.get("http://checkip.dyndns.org", timeout=5)
            if response.status_code == 200:
                match = re.search(r'Current IP Address: ([\d.]+)', response.text)
                if match:
                    return match.group(1)
        except Exception:
            pass
        return None
