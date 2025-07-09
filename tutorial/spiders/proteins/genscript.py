import scrapy
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class GenScriptSpider(scrapy.Spider):
    name = 'genscript'
    start_urls = ['https://www.genscript.com/protein-list/A/1.html']

    custom_settings = {
        "PLAYWRIGHT_ENABLED": True,
        "DOWNLOAD_DELAY": 60,
        "RANDOMIZE_DOWNLOAD_DELAY": False,
        "CONCURRENT_REQUESTS": 1,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 60,
        "AUTOTHROTTLE_MAX_DELAY": 120,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        {
                            "method": "route",
                            "args": ["**/*"],
                            "kwargs": {
                                "handler": self.block_resources
                            }
                        }
                    ],
                    "page_num": 1
                },
                callback=self.parse
            )

    def block_resources(self, route, request):
        blocked_types = {"font", "stylesheet", "image", "media", "document"}
        if request.resource_type in blocked_types:
            return route.abort()

        blocked_domains = [
            "webanalytics.internet.genscript.com",
            "e.clarity.ms",
            "clarity.ms",
            "aria.microsoft.com",
            "browser.pipe.aria.microsoft.com"
        ]
        if any(domain in request.url for domain in blocked_domains):
            return route.abort()

        return route.continue_()

    async def parse(self, response):
        page = response.meta["playwright_page"]
        current_page_num = response.meta.get("page_num", 1)

        self.logger.info(f"Scraping page {current_page_num}: {response.url}")

        rows = response.css('tr.gridtable-tr')
        if not rows:
            self.logger.info(f"No products found on page {current_page_num}, stopping crawl.")
            await page.close()
            return

        for row in rows:
            catalog_no = row.css('td:nth-child(1) div::text').get(default='N/A').strip()
            name = row.css('td:nth-child(2) a::text').get(default='N/A').strip()
            link = row.css('td:nth-child(2) a::attr(href)').get()
            url = response.urljoin(link)

            options = row.css('td:nth-child(4) select option')
            sizes = []
            prices = []
            for opt in options:
                size = opt.css('::text').get(default='').strip()
                price = opt.attrib.get('price', '').strip()
                if size:
                    sizes.append(size)
                if price:
                    prices.append(price)

            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        {
                            "method": "route",
                            "args": ["**/*"],
                            "kwargs": {
                                "handler": self.block_resources
                            }
                        }
                    ],
                    "catalog_no": catalog_no,
                    "name": name,
                    "sizes": "/".join(sizes),
                    "prices": "/".join(prices),
                },
                callback=self.parse_product
            )

        # Go to next page
        next_page_num = current_page_num + 1
        if next_page_num > 15:  # Optional upper limit
            self.logger.info("Page limit exceeded.")
            await page.close()
            return

        parsed_url = urlparse(response.url)
        parts = parsed_url.path.split("/")
        parts[-1] = f"{next_page_num}.html"
        new_path = "/".join(parts)
        next_url = urlunparse(parsed_url._replace(path=new_path))

        self.logger.info(f"Going to next page: {next_url}")
        yield scrapy.Request(
            next_url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    {
                        "method": "route",
                        "args": ["**/*"],
                        "kwargs": {
                            "handler": self.block_resources
                        }
                    }
                ],
                "page_num": next_page_num
            },
            callback=self.parse,
            dont_filter=True,
        )

        await page.close()

    async def parse_product(self, response):
        page = response.meta["playwright_page"]
        catalog_no = response.meta["catalog_no"]
        name = response.meta["name"]
        sizes = response.meta["sizes"]
        prices = response.meta["prices"]

        def extract_tr_text(response, tr_index):
            try:
                td = response.css(f'tr:nth-of-type({tr_index}) td.right-value')
                if not td:
                    return "N/A"
                text = td.css("::text").getall()
                return "/".join([t.strip() for t in text if t.strip()])
            except:
                return "N/A"

        purity = extract_tr_text(response, 3)
        endotoxin_level = extract_tr_text(response, 4)
        expression_system = extract_tr_text(response, 6)

        await page.close()

        yield {
            "catalog_no": catalog_no,
            "name": name,
            "sizes": sizes,
            "prices": prices,
            "purity": purity,
            "endotoxin_level": endotoxin_level,
            "expression_system": expression_system,
        }
