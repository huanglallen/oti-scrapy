import scrapy
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from scrapy_playwright.page import PageMethod


class NovusBioSpider(scrapy.Spider):
    name = 'novusbio'
    start_urls = [
        'https://www.novusbio.com/search?category=Peptides%20and%20Proteins&keywords=protein&page=1'
    ]

    custom_settings = {
        "PLAYWRIGHT_ENABLED": True,
        "DOWNLOAD_DELAY": 5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 1,
        "AUTOTHROTTLE_ENABLED": False,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [404, 429, 500, 503, 1015],
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": ["--disable-http2"]
        }
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta=self.get_playwright_meta(1),
                headers=self.get_headers(),
                callback=self.parse
            )

    def block_resources(self, route, request):
        #blocked_types = {"font", "stylesheet", "image", "media", "document"}
        blocked_types = {"font", "image"}
        blocked_domains = [
            "bam.nr-data.net", "googletagmanager.com", "google-analytics.com",
            "clarity.ms", "novusbio.com/ajax", "ads.", "doubleclick.net", "outbrain.com"
        ]
        if request.resource_type in blocked_types or any(domain in request.url for domain in blocked_domains):
            return route.abort()
        return route.continue_()

    def get_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def get_playwright_meta(self, page_num):
        return {
            "playwright": True,
            "playwright_include_page": True,
            "playwright_page_methods": [
                PageMethod("route", "**/*", self.block_resources),
                PageMethod("add_init_script", "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"),
                PageMethod("add_init_script", "window.chrome = { runtime: {} };"),
                PageMethod("add_init_script", "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]})"),
                PageMethod("add_init_script", "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})"),
                PageMethod("set_extra_http_headers", self.get_headers()),
            ],
            "playwright_page_goto_kwargs": {"wait_until": "load"},
            "page_num": page_num
        }

    async def parse(self, response):
        page = response.meta["playwright_page"]
        current_page_num = response.meta.get("page_num", 1)
        self.logger.info(f"Scraping page {current_page_num}: {response.url}")

        product_links = response.css("h2.col3_hdr > a.ecommerce_link")

        if not product_links:
            self.logger.info(f"No products found on page {current_page_num}.")
            await page.close()
            return

        for link in product_links:
            name = link.css("span::text").get(default="N/A").strip()
            url = response.urljoin(link.css("::attr(href)").get())
            catalog_no = link.attrib.get("data-id", "N/A")

            yield scrapy.Request(
                url,
                meta=self.get_playwright_meta(current_page_num),
                callback=self.parse_product,
                cb_kwargs={"catalog_no": catalog_no, "name": name},
                headers=self.get_headers()
            )

        next_page_num = current_page_num + 1
        if next_page_num > 3180:
            self.logger.info("Reached max page limit. Stopping.")
            await page.close()
            return

        parsed_url = urlparse(response.url)
        query_params = parse_qs(parsed_url.query)
        query_params["page"] = [str(next_page_num)]
        new_query = urlencode(query_params, doseq=True)
        next_url = urlunparse(parsed_url._replace(query=new_query))

        self.logger.info(f"Navigating to next page: {next_url}")
        yield scrapy.Request(
            next_url,
            meta=self.get_playwright_meta(next_page_num),
            callback=self.parse,
            headers=self.get_headers(),
            dont_filter=True
        )

        await page.close()

    async def parse_product(self, response, catalog_no, name):
        page = response.meta["playwright_page"]

        sizes = []
        prices = []
        for row in response.css("table.sticky-enabled tr.odd"):
            size = row.css("td:nth-child(1) div.atc_size::text").get(default="").strip()
            price = row.css("td:nth-child(3) div.price::text").get(default="").strip()
            if size and size not in sizes:
                sizes.append(size)
            if price and price not in prices:
                prices.append(price)

        reactivity = response.css("table.ds_list tbody tr:nth-of-type(1) td:nth-of-type(2) span::text").get(default="N/A").strip()
        application = response.css("table.ds_list tbody tr:nth-of-type(2) td:nth-of-type(2) span::text").get(default="N/A").strip()
        format_ = response.css("table.ds_list tbody tr:nth-of-type(3) td:nth-of-type(2) div::text").get(default="N/A").strip()

        gene = response.xpath("//table[contains(@class, 'ds_list') and contains(@class, 'wide')]//tr[td/strong[text()='Gene']]/td[2]/div/text()").get(default="N/A").strip()
        purity = response.xpath("//table[contains(@class, 'ds_list') and contains(@class, 'wide')]//tr[td/strong[text()='Purity']]/td[2]/div/text()").get(default="N/A").strip()
        endotoxin = response.xpath("//table[contains(@class, 'ds_list') and contains(@class, 'wide')]//tr[td/strong[contains(text(),'Endotoxin')]]/td[2]/div/text()").get(default="N/A").strip()

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
