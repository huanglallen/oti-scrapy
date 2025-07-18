import scrapy
from urllib.parse import urlparse, urlunparse

class GenScriptSpider(scrapy.Spider):
    name = 'genscript'

    # Start at letter A, page 1
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

    # Alphabet letters to iterate through
    letters = [chr(c) for c in range(ord('A'), ord('Z') + 1)]

    def start_requests(self):
        # Start with first letter A, page 1
        start_letter = 'A'
        start_page = 1
        url = f'https://www.genscript.com/protein-list/{start_letter}/{start_page}.html'
        yield scrapy.Request(
            url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    {"method": "route", "args": ["**/*"], "kwargs": {"handler": self.block_resources}}
                ],
                "page_num": start_page,
                "letter_index": 0,
                "letter": start_letter,
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
        letter_index = response.meta.get("letter_index", 0)
        letter = response.meta.get("letter", "A")

        self.logger.info(f"Scraping letter {letter} page {current_page_num}: {response.url}")

        rows = response.css('tr.gridtable-tr')
        if not rows:
            self.logger.info(f"No products found on letter {letter} page {current_page_num}, moving to next letter.")
            await page.close()

            # Move to next letter
            next_letter_index = letter_index + 1
            if next_letter_index >= len(self.letters):
                self.logger.info("Completed all letters. Spider finished.")
                return

            next_letter = self.letters[next_letter_index]
            next_url = f'https://www.genscript.com/protein-list/{next_letter}/1.html'
            yield scrapy.Request(
                next_url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        {"method": "route", "args": ["**/*"], "kwargs": {"handler": self.block_resources}}
                    ],
                    "page_num": 1,
                    "letter_index": next_letter_index,
                    "letter": next_letter,
                },
                callback=self.parse,
                dont_filter=True,
            )
            return

        # Process each product row
        for row in rows:
            catalog_no = row.css('td:nth-child(1) div::text').get(default='N/A').strip()
            name = row.css('td:nth-child(2) a::text').get(default='N/A').strip()
            link = row.css('td:nth-child(2) a::attr(href)').get()
            url = response.urljoin(link)

            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        {"method": "route", "args": ["**/*"], "kwargs": {"handler": self.block_resources}}
                    ],
                    "catalog_no": catalog_no,
                    "name": name,
                },
                callback=self.parse_product,
            )

        # Next page for current letter
        next_page_num = current_page_num + 1
        if next_page_num > 15:
            self.logger.info(f"Reached page limit for letter {letter}, moving to next letter.")
            await page.close()

            next_letter_index = letter_index + 1
            if next_letter_index >= len(self.letters):
                self.logger.info("Completed all letters. Spider finished.")
                return

            next_letter = self.letters[next_letter_index]
            next_url = f'https://www.genscript.com/protein-list/{next_letter}/1.html'
            yield scrapy.Request(
                next_url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        {"method": "route", "args": ["**/*"], "kwargs": {"handler": self.block_resources}}
                    ],
                    "page_num": 1,
                    "letter_index": next_letter_index,
                    "letter": next_letter,
                },
                callback=self.parse,
                dont_filter=True,
            )
            return

        # Construct next page URL for the same letter
        parsed_url = urlparse(response.url)
        parts = parsed_url.path.split("/")
        parts[-1] = f"{next_page_num}.html"
        new_path = "/".join(parts)
        next_url = urlunparse(parsed_url._replace(path=new_path))

        self.logger.info(f"Going to next page {next_page_num} of letter {letter}: {next_url}")

        yield scrapy.Request(
            next_url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    {"method": "route", "args": ["**/*"], "kwargs": {"handler": self.block_resources}}
                ],
                "page_num": next_page_num,
                "letter_index": letter_index,
                "letter": letter,
            },
            callback=self.parse,
            dont_filter=True,
        )

        await page.close()

    async def parse_product(self, response):
        page = response.meta["playwright_page"]
        catalog_no = response.meta["catalog_no"]
        name = response.meta["name"]

        def clean_text(text):
            return text.replace('\xa0', ' ').replace('\xad', '').strip()

        purity = "N/A"
        endotoxin_level = "N/A"
        expression_system = "N/A"

        for row in response.css('table.gridtable tr'):
            label = row.css('td:first-child b::text').get()
            value = row.css('td.right-value::text, td.right-value *::text').getall()
            value_text = clean_text(" ".join([v for v in value if v.strip()]))

            if not label:
                continue

            label_lower = label.lower().strip()

            if "purity" in label_lower:
                purity = value_text
            elif "endotoxin" in label_lower:
                endotoxin_level = value_text
            elif "expression system" in label_lower:
                expression_system = value_text


        sizes = []
        prices = []
        for box in response.css('span.size-box'):
            size_text = box.css('label.size::text').get(default='').strip()
            price = box.attrib.get('data-price', '').replace('$', '').strip()

            if size_text:
                sizes.append(size_text)
            if price:
                prices.append(price)

        sizes_joined = "/".join(sizes)
        prices_joined = "/".join(prices)

        await page.close()

        yield {
            "catalog_no": catalog_no,
            "name": name,
            "sizes": sizes_joined,
            "prices": prices_joined,
            "purity": purity,
            "endotoxin_level": endotoxin_level,
            "expression_system": expression_system,
            "url": response.url,
        }
