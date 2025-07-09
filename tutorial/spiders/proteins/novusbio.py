import scrapy
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class NovusBioSpider(scrapy.Spider):
    name = 'novusbio'
    start_urls = ['https://www.novusbio.com/search?category=Peptides%20and%20Proteins&keywords=protein&page=1']

    custom_settings = {
        "PLAYWRIGHT_ENABLED": True,
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 3,
        "AUTOTHROTTLE_MAX_DELAY": 10,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [429, 1015],
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
                            "kwargs": {"handler": self.block_resources}
                        }
                    ],
                    "page_num": 1
                },
                callback=self.parse
            )

    def block_resources(self, route, request):
        blocked_types = {"font", "stylesheet", "image", "media", "document"}
        blocked_domains = [
            "aa.agkn.com",
            "ade.clmbtech.com",
            "ad.tpmn.co.kr",
            "sync.outbrain.com",
            "ads.stickyadstv.com",
            "cm.g.doubleclick.net",
            "clarity.ms",
            "novusbio.com/ajax",
            "novusbio.com/distributors/ajax",
            "novusbio.com/products/ajax",
        ]
        blocked_extensions = [".gif"]

        if request.resource_type in blocked_types:
            return route.abort()
        if any(domain in request.url for domain in blocked_domains):
            return route.abort()
        if any(request.url.lower().endswith(ext) for ext in blocked_extensions):
            return route.abort()

        return route.continue_()

    async def parse(self, response):
        page = response.meta["playwright_page"]
        current_page_num = response.meta.get("page_num", 1)
        self.logger.info(f"Scraping page {current_page_num}: {response.url}")

        product_cards = response.css("div.catalog_number_wrapper.not3column")
        names = response.css("h2.col3_hdr::text").getall()

        if not product_cards:
            self.logger.info(f"No products found on page {current_page_num}, stopping crawl.")
            await page.close()
            return

        for card, name in zip(product_cards, names):
            catalog_no = card.css("a::text").get(default="N/A").strip()
            link = card.css("a::attr(href)").get()
            name = name.strip() if name else "N/A"
            if link:
                url = response.urljoin(link)
                yield scrapy.Request(
                    url,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_page_methods": [
                            {
                                "method": "route",
                                "args": ["**/*"],
                                "kwargs": {"handler": self.block_resources}
                            }
                        ],
                        "catalog_no": catalog_no,
                        "name": name,
                    },
                    callback=self.parse_product
                )

        next_page_num = current_page_num + 1
        if next_page_num > 3180:
            self.logger.info("Reached maximum page limit (3180). Stopping crawl.")
            await page.close()
            return

        parsed_url = urlparse(response.url)
        query_params = parse_qs(parsed_url.query)
        query_params['page'] = [str(next_page_num)]
        new_query = urlencode(query_params, doseq=True)
        next_url = urlunparse(parsed_url._replace(query=new_query))

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
                        "kwargs": {"handler": self.block_resources}
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

        # Size/Price table
        sizes = []
        prices = []
        for row in response.css("table.sticky-enabled tr.odd"):
            size = row.css("td:nth-child(1) div.atc_size::text").get(default="").strip()
            price = row.css("td:nth-child(3) div.price::text").get(default="").strip()
            if size:
                sizes.append(size)
            if price:
                prices.append(price)

        # ds_list table: Reactivity, Application, Format
        reactivity = response.css("table.ds_list tbody tr:nth-of-type(1) td:nth-of-type(2) span::text").get(default="N/A").strip()
        application = response.css("table.ds_list tbody tr:nth-of-type(2) td:nth-of-type(2) span::text").get(default="N/A").strip()
        format_ = response.css("table.ds_list tbody tr:nth-of-type(3) td:nth-of-type(2) div::text").get(default="N/A").strip()

        # ds_list.wide table: Gene, Purity, Endotoxin
        gene = response.css("table.ds_list.wide tbody tr:nth-of-type(7) td:nth-of-type(2) div::text").get(default="N/A").strip()
        purity = response.css("table.ds_list.wide tbody tr:nth-of-type(8) td:nth-of-type(2) div::text").get(default="N/A").strip()
        endotoxin = response.css("table.ds_list.wide tbody tr:nth-of-type(9) td:nth-of-type(2) div::text").get(default="N/A").strip()

        await page.close()

        yield {
            "catalog_no": catalog_no,
            "name": name,
            "sizes": "/".join(sizes) if sizes else "N/A",
            "prices": "/".join(prices) if prices else "N/A",
            "reactivity": reactivity,
            "application": application,
            "format": format_,
            "gene": gene,
            "purity": purity,
            "endotoxin": endotoxin,
        }
