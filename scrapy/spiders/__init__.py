import scrapy

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
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]

        # Extract product links on the current page
        product_links = response.css('p.font-bold > a::attr(href)').getall()

        for link in product_links:
            if link.startswith('/en-us/products/proteins-peptides'):
                url = response.urljoin(link)
                name = response.css(f'a[href="{link}"]::text').get()
                if name:
                    name = name.strip()
                else:
                    name = "N/A"
                yield scrapy.Request(
                    url,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "name": name
                    },
                    callback=self.parse_product
                )

        # Pagination: Find the next page URL and yield request if it exists
        next_page = response.css('a.pagination__next::attr(href)').get()
        if next_page:
            next_page_url = response.urljoin(next_page)
            await page.close()
            yield scrapy.Request(
                next_page_url,
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse
            )
        else:
            await page.close()

    async def parse_product(self, response):
        page = response.meta["playwright_page"]
        name = response.meta["name"]

        # Utility async function to extract text safely with timeout
        async def extract_text(selector):
            try:
                await page.wait_for_selector(f'div[data-testid="{selector}"] dd', timeout=10000)
                el = await page.query_selector(f'div[data-testid="{selector}"] dd')
                return (await el.inner_text()).strip() if el else "N/A"
            except:
                return "N/A"

        # Wait for size and price selectors to load before extracting
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
