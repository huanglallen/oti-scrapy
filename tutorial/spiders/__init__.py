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
        purity = "N/A"
        expression_system = "N/A"
        applications = "N/A"
        endotoxin_level = "N/A"

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

                    size = new_response.css('div[data-cy="size-button-content"]::text').get() or "N/A"
                    price = new_response.css('div[data-testid="base-price"] > span::text').get() or "N/A"

                    size = size.strip()
                    price = price.strip()

                    self.logger.info(f"[{name}] Size: {size}, Price: {price}")
        except Exception as e:
            self.logger.warning(f"[{name}] Failed to extract size/price: {e}")

        # Extract other metadata
        async def extract_text(selector):
            try:
                await page.wait_for_selector(f'div[data-testid="{selector}"] dd', timeout=3000)
                el = await page.query_selector(f'div[data-testid="{selector}"] dd')
                return (await el.inner_text()).strip() if el else "N/A"
            except:
                return "N/A"

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
