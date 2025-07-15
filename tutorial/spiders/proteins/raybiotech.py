import scrapy
from urllib.parse import urlparse, urlunparse
from scrapy_playwright.page import PageMethod

async def stealth(page):
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = {runtime: {}};
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    """)

class RayBiotechSpider(scrapy.Spider):
    name = 'raybiotech'
    start_urls = ['https://www.raybiotech.com/proteins-and-peptides-products/recombinant-proteins?page=1']

    custom_settings = {
        "PLAYWRIGHT_ENABLED": True,
        "DOWNLOAD_DELAY": 30,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 1,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 30,
        "AUTOTHROTTLE_MAX_DELAY": 60,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
    }

    def block_resources(self, route, request):
        blocked_types = {"image", "media", "font", "stylesheet"}
        blocked_domains = [
            "analytics.google.com",
            "googletagmanager.com",
            "google-analytics.com",
            "clarity.ms",
            "cloudflare.com",
            "wp-admin/admin-ajax.php"
        ]

        if request.resource_type in blocked_types or any(d in request.url for d in blocked_domains):
            return route.abort()
        return route.continue_()

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        {
                            "method": "route",
                            "args": ["**/*"],
                            "kwargs": {"handler": self.block_resources}
                        },
                        {
                            "method": "set_viewport_size",
                            "args": [{"width": 1920, "height": 1080}]
                        },
                        {
                            "method": "wait_for_selector",
                            "args": ["h3.result-title"]
                        },
                    ],
                    "page_num": 1
                },
                callback=self.parse
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        await stealth(page)

        current_page_num = response.meta.get("page_num", 1)

        self.logger.info(f"Scraping listing page {current_page_num}: {response.url}")

        product_links = response.css("a.result").xpath('./h3[contains(@class,"result-title")]/ancestor::a/@href').getall()
        if not product_links:
            self.logger.warning("No products found. The page may not have fully rendered.")
            await page.close()
            return

        for link in product_links:
            full_url = response.urljoin(link)
            yield scrapy.Request(
                full_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        {
                            "method": "route",
                            "args": ["**/*"],
                            "kwargs": {"handler": self.block_resources}
                        },
                        {
                            "method": "set_viewport_size",
                            "args": [{"width": 1920, "height": 1080}]
                        },
                        {
                            "method": "wait_for_selector",
                            "args": ["span.base"]
                        },
                    ],
                },
                callback=self.parse_product
            )

        # Pagination
        next_page_num = current_page_num + 1
        if next_page_num > 15:
            self.logger.info("Page limit reached, stopping crawl.")
            await page.close()
            return

        parsed_url = urlparse(response.url)
        from urllib.parse import parse_qs, urlencode

        query_dict = parse_qs(parsed_url.query)
        query_dict['page'] = [str(next_page_num)]
        new_query = urlencode(query_dict, doseq=True)

        next_url = urlunparse(parsed_url._replace(query=new_query))

        self.logger.info(f"Going to next page: {next_url}")
        yield scrapy.Request(
            next_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    {
                        "method": "route",
                        "args": ["**/*"],
                        "kwargs": {"handler": self.block_resources}
                    },
                    {
                        "method": "set_viewport_size",
                        "args": [{"width": 1920, "height": 1080}]
                    },
                    {
                        "method": "wait_for_selector",
                        "args": ["h3.result-title"]
                    },
                ],
                "page_num": next_page_num
            },
            callback=self.parse,
            dont_filter=True
        )

        await page.close()

    async def parse_product(self, response):
        page = response.meta["playwright_page"]
        await stealth(page) 

        name = response.css("span.base::text").get(default="N/A").strip()

        sizes = []
        prices = []
        options = response.css("select#attribute169 option")[1:]  
        for opt in options:
            size = opt.css("::text").get(default="").strip()
            price = opt.attrib.get("value", "").strip()
            if size and price:
                sizes.append(size)
                prices.append(price)

        def extract_spec(row_class):
            return response.css(f"tr.{row_class} td span.final-data::text").get(default="N/A").strip()

        specs = {
            "species": extract_spec("species"),
            "protein_name": extract_spec("protein_name_/_synonyms"),
            "expressed_region": extract_spec("expressed_region"),
            "expression_system": extract_spec("expression_system"),
            "purity": extract_spec("purity"),
            "endotoxin_level": extract_spec("endotoxin_level"),
        }

        await page.close()

        yield {
            "name": name,
            "sizes": "/".join(sizes),
            "prices": "/".join(prices),
            **specs
        }
