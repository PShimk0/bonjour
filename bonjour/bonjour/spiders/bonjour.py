import math

import chompjs
import scrapy
from scrapy.spiders import SitemapSpider, Spider


class BonjourSpider(Spider):
    name = "bonjour"
    custom_settings = {
        "LOG_LEVEL": "INFO",
    }
    start_urls = ["https://bonjour-dv.ru/"]

    def parse(self, response, **kwargs):
        data = response.xpath("//script[@id='__NEXT_DATA__']/text()").get()
        data = chompjs.parse_js_object(data)
        data = data["props"]["initialReduxState"]["categoriesMenu"]["tree"]
        categories_urls = [
            f"https://bonjour-dv.ru/category/{x['id']}?page=1" for x in data[:4]
        ]
        for url in categories_urls:
            yield scrapy.Request(
                url, callback=self.parse_category, cb_kwargs={"current_page": 1}
            )

    def parse_category(self, response, **kwargs):
        data = response.xpath("//script[@id='__NEXT_DATA__']/text()").get()
        data = chompjs.parse_js_object(data)
        data = data["props"]["initialReduxState"]["productsList"]
        product_urls = [
            f"https://bonjour-dv.ru/product/{x['id']}" for x in data["products"]
        ]
        for url in product_urls:
            yield scrapy.Request(
                url,
                callback=self.parse_product,
            )
        total_count = data["totalCount"]
        total_page_count = math.ceil(int(total_count) / 24)
        next_page = kwargs["current_page"] + 1
        if next_page < total_page_count:
            yield scrapy.Request(
                response.url.replace(
                    f"page={kwargs['current_page']}", f"page={next_page}"
                ),
                callback=self.parse_category,
                cb_kwargs={"current_page": next_page},
            )

    def parse_product(self, response, **kwargs):
        try:
            data = response.xpath("//script[@id='__NEXT_DATA__']/text()").get()
            data = chompjs.parse_js_object(data)
            data = data["props"]["pageProps"]["product"]["data"]["getProduct"]
            if data:
                item = dict()
                item["name"] = data.get("title")
                if data["category"]:
                    item["category"] = data["category"].get("name")
                else:
                    item["category"] = None
                item["barcode"] = data["barcode"].get("value")
                if data["brand"]:
                    item["brand"] = data["brand"].get("name")
                else:
                    item["brand"] = None
                item["id"] = data.get("id")
                if data["manufacturer"]:
                    item["manufacturer"] = data["manufacturer"].get("name")
                else:
                    item["manufacturer"] = None
                item["image_urls"] = [x["uri"] for x in data["images"]]
                item["base_price"] = data.get("base_price")
                item["offer_price"] = data.get("offer_price")
                promotion = response.xpath(
                    "//div/span[contains(text(), '%')]/preceding-sibling::text()"
                ).getall()
                if promotion:
                    item["promotion"] = f"{promotion[1]}"
                else:
                    item["promotion"] = None
                yield item
        except Exception as e:
            pass
