import scrapy
from scrapy_playwright.page import PageMethod


class PTGLabSpider(scrapy.Spider):
    name = "ptglab"
    start_urls = ["https://www.ptglab.com/results?q=humankine"]

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
                        PageMethod("evaluate", """
                            async () => {
                                let prevHeight = 0;
                                let sameCount = 0;
                                while (sameCount < 5) {
                                    window.scrollBy(0, 2000);
                                    await new Promise(r => setTimeout(r, 1000));
                                    const currHeight = document.body.scrollHeight;
                                    if (currHeight === prevHeight) {
                                        sameCount++;
                                    } else {
                                        sameCount = 0;
                                        prevHeight = currHeight;
                                    }
                                }
                            }
                        """),
                        PageMethod("wait_for_timeout", 2000),
                    ],
                },
                callback=self.parse_listing,
            )

    async def parse_listing(self, response):
        page = response.meta["playwright_page"]

        product_links = response.css('div[data-category="HumanKine"] a::attr(href)').getall()
        for link in product_links:
            full_url = response.urljoin(link)
            yield scrapy.Request(
                full_url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "div.sizes-box_sizeList__Kr6Gg button"),
                        PageMethod("click", "div.sizes-box_sizeList__Kr6Gg button"),
                        PageMethod("wait_for_timeout", 2000),
                    ],
                },
                callback=self.parse_product
            )

        await page.close()

    async def parse_product(self, response):
        page = response.meta["playwright_page"]

        def sel_text(selector, default="N/A"):
            value = response.css(selector).get()
            return value.strip() if value else default

        name = sel_text("h1[role='heading']::text")
        cat_no = sel_text("div.catalog-number span::text")
        expression = sel_text("li:contains('Expression System') span::text")
        purity = sel_text("li:contains('Purity') span::text")
        endotoxin = sel_text("li:contains('Endotoxin Level') span::text")

        sizes = [s.strip() for s in response.css("div.magic-dropdown-box li::text").getall() if s.strip()]
        prices = [p.strip() for p in response.css("div.magic-dropdown-box li span::text").getall() if "$" in p]

        await page.close()

        yield {
            "name": name,
            "catalog_no": cat_no,
            "size": "/".join(sizes) if sizes else "N/A",
            "price": "/".join(prices) if prices else "N/A",
            "expression_system": expression,
            "purity": purity,
            "endotoxin_level": endotoxin,
            "url": response.url,
        }
