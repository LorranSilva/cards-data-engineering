# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class EditionItem(scrapy.Item):
    edition_id = scrapy.Field()
    edition_name = scrapy.Field()
    edition_acronym = scrapy.Field()
    edition_release_date = scrapy.Field()
    parent_edition_id = scrapy.Field()
    scraped_at = scrapy.Field()


class CardItem(scrapy.Item):
    id_external = scrapy.Field()
    collection_id = scrapy.Field()
    value_min = scrapy.Field()
    value_avg = scrapy.Field()
    value_max = scrapy.Field()
    name_EN = scrapy.Field()
    name_PT = scrapy.Field()
    scraped_at = scrapy.Field()
