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
        await page.close()  # Close the browser page after rendering

        product_links = response.css('p.font-bold > a::attr(href)').getall()

        for link in product_links:
            if link.startswith('/en-us/products/proteins-peptides'):
                url = response.urljoin(link)
                name = response.css(f'a[href="{link}"]::text').get().strip()
                yield scrapy.Request(
                    url,
                    meta={"playwright": True, "playwright_include_page": True, "name": name},
                    callback=self.parse_product
                )

    async def parse_product(self, response):
        page = response.meta["playwright_page"]
        await page.close()

        name = response.meta["name"]

        # Extract price from <div data-testid="base-price"><span>...</span></div>
        price = response.css('div[data-testid="base-price"] > span::text').get()

        # Extract size from the first <div data-cy="size-button-content">
        size = response.css('div[data-cy="size-button-content"]::text').get()

        # Extract purity from <div data-testid="purity"><dd>...</dd></div>
        purity = response.css('div[data-testid="purity"] dd::text').get()

        yield {
            'name': name,
            'price': price.strip() if price else 'N/A',
            'size': size.strip() if size else 'N/A',
            'purity': purity.strip() if purity else 'N/A',
        }
