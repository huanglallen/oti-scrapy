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
        await page.close()

        product_links = response.css('p.font-bold > a::attr(href)').getall()

        for link in product_links:
            if link.startswith('/en-us/products/proteins-peptides'):
                url = response.urljoin(link)
                name = response.css(f'a[href="{link}"]::text').get().strip()
                yield scrapy.Request(
                    url,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "name": name
                    },
                    callback=self.parse_product
                )

    async def parse_product(self, response):
        page = response.meta["playwright_page"]
        name = response.meta["name"]

        size = "N/A"
        price = "N/A"

        try:
            await page.wait_for_selector('div.sizes-box_sizeList__Kr6Gg', timeout=10000)
            wrappers = await page.query_selector_all('div.sizes-box_sizeList__Kr6Gg > div')

            if wrappers:
                button = await wrappers[0].query_selector('button')
                if button:
                    await button.click()
                    await page.wait_for_timeout(1000)
                    await page.wait_for_selector('div[data-cy="size-button-content"]', timeout=5000)
                    await page.wait_for_selector('div[data-testid="base-price"] span', timeout=5000)

                    content = await page.content()
                    new_response = response.replace(body=content)

                    size = new_response.css('div[data-cy="size-button-content"]::text').get()
                    price = new_response.css('div[data-testid="base-price"] > span::text').get()

                    size = size.strip() if size else "N/A"
                    price = price.strip() if price else "N/A"

                    self.logger.info(f"[{name}] Size: {size}, Price: {price}")
        except Exception as e:
            self.logger.warning(f"[{name}] Failed to extract size/price: {e}")

        # Extract purity
        try:
            await page.wait_for_selector('div[data-testid="purity"] dd', timeout=5000)
            purity_el = await page.query_selector('div[data-testid="purity"] dd')
            purity = await purity_el.inner_text() if purity_el else None
        except:
            purity = None

        await page.close()

        item = {
            'name': name,
            'sizes': size,
            'prices': price,
            'purity': purity.strip() if purity else 'N/A',
        }
        yield item
