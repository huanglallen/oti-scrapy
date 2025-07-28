import scrapy
from scrapy_playwright.page import PageMethod


class RNDSpider(scrapy.Spider):
    name = "rnd"
    allowed_domains = ["rndsystems.com"]
    start_urls = [
        "https://www.rndsystems.com/search?keywords=protein&category=Proteins%20and%20Enzymes&species=Human&page=1"
    ]

    custom_settings = {
        "PLAYWRIGHT_ENABLED": True,
        "PLAYWRIGHT_ABORT_REQUEST": lambda req: "bam.nr-data.net" in req.url,
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "div#search-results"),  # container
                        PageMethod("wait_for_timeout", 2000),
                    ],
                },
                callback=self.parse
            )

    def parse(self, response):
        self.logger.info(f"[PAGE LOAD] {response.url}")

        product_links = response.css("a.ecommerce_link::attr(href)").getall()
        self.logger.info(f"Found {len(product_links)} product links.")

        for link in product_links:
            full_url = response.urljoin(link)
            yield scrapy.Request(
                full_url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "a.ecommerce_link"),
                        PageMethod("wait_for_timeout", 1000),
                    ],
                },
                callback=self.parse_product
            )

    async def parse_product(self, response):
        page = response.meta["playwright_page"]

        def extract_cleaned(selector):
            return response.css(selector).get(default="").strip()

        def extract_multiple(selector):
            return list(set([t.strip() for t in response.css(selector).getall() if t.strip()]))

        def extract_detail(label):
            row = response.xpath(f"//td[text()='{label}']/following-sibling::td/text()").get()
            return row.strip() if row else "N/A"

        catalog_no = response.url.split("_")[-1]
        name = extract_cleaned("h1.ds_title::text")
        sizes_prices = extract_multiple("span.size_price::text")

        purity = extract_detail("Purity")
        endotoxin = extract_detail("Endotoxin Level")
        activity = extract_detail("Activity")
        source = extract_detail("Source")

        await page.close()

        yield {
            "catalog_no": catalog_no,
            "name": name,
            "sizes_prices": "/".join(sizes_prices) if sizes_prices else "N/A",
            "purity": purity,
            "endotoxin_level": endotoxin,
            "activity": activity,
            "source": source,
            "url": response.url
        }
