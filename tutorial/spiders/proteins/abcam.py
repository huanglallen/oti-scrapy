import scrapy
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class AbcamSpider(scrapy.Spider):
    name = 'abcam'
    start_urls = ['https://www.abcam.com/en-us/products/proteins-peptides?page=1']

    custom_settings = {
        "PLAYWRIGHT_ENABLED": True,
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
        if request.resource_type in blocked_types or any(
            ext in request.url for ext in [".svg", ".gif", ".png", ".woff", ".ttf", ".eot"]
        ):
            return route.abort()
        return route.continue_()

    async def parse(self, response):
        page = response.meta["playwright_page"]
        current_page_num = response.meta.get("page_num", 1)

        self.logger.info(f"Scraping page {current_page_num}: {response.url}")

        # Extract product links
        product_links = response.css('p.font-bold > a::attr(href)').getall()

        if product_links:
            for link in product_links:
                if link.startswith('/en-us/products/proteins-peptides'):
                    url = response.urljoin(link)
                    name = response.css(f'a[href="{link}"]::text').get()
                    name = name.strip() if name else "N/A"
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
                            "name": name
                        },
                        callback=self.parse_product
                    )

            next_page_num = current_page_num + 1

            #Set max pages 
            if next_page_num > 601:
                self.logger.warning("Page limit reached. Stopping.")
                await page.close()
                return

            parsed_url = urlparse(response.url)
            query_params = parse_qs(parsed_url.query)
            query_params['page'] = [str(next_page_num)]
            new_query = urlencode(query_params, doseq=True)
            next_page_url = urlunparse(parsed_url._replace(query=new_query))

            self.logger.info(f"Going to next page: {next_page_url}")
            yield scrapy.Request(
                next_page_url,
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
        else:
            self.logger.info(f"No products found on page {current_page_num}, stopping crawl.")

        await page.close()

    async def parse_product(self, response):
        page = response.meta["playwright_page"]
        name = response.meta["name"]

        async def extract_text(selector):
            try:
                await page.wait_for_selector(f'div[data-testid="{selector}"] dd', timeout=10000)
                el = await page.query_selector(f'div[data-testid="{selector}"] dd')
                return (await el.inner_text()).strip() if el else "N/A"
            except:
                return "N/A"

        try:
            await page.wait_for_selector('div.sizes-box_sizeList__Kr6Gg', timeout=20000)
            size_el = await page.query_selector('div[data-cy="size-button-content"]')
            price_el = await page.query_selector('div[data-testid="base-price"] > span')
            size = (await size_el.inner_text()).strip() if size_el else "N/A"
            price = (await price_el.inner_text()).strip() if price_el else "N/A"
        except Exception:
            size = "N/A"
            price = "N/A"

        expression_system = await extract_text("expression-system")
        purity = await extract_text("purity")
        endotoxin_level = await extract_text("endotoxin-level")
        applications = await extract_text("applications")

        await page.close()

        yield {
            'name': name,
            'expression_system': expression_system,
            'purity': purity,
            'endotoxin_level': endotoxin_level,
            'sizes': size,
            'prices': price,
            'applications': applications,
        }
