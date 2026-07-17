import scrapy
import re
import json

class MainSpider(scrapy.Spider):
    name = 'main_spider'
    allowed_domains = ['www.ligamagic.com.br', 'ligayugioh.com.br', 'ligapokemon.com.br', 'ligalorcana.com.br']
    start_urls = ['file:///D:/Projetos/cards-data-engineering/docs/mtg.html']
    # start_urls = ['https://www.ligamagic.com.br/?view=cards/home']


    def parse(self, response):
        raw_decode = response.xpath("//script[contains(., 'jsonEditions')]/text()").get()
        i = raw_decode.index("{", raw_decode.index("jsonEditions"))
        data, _ = json.JSONDecoder().raw_decode(raw_decode[i:])

        all_collections = data["main"] + [f for daughters in data["aux"].values() for f in daughters]

        for collection in all_collections:
            self.logger.info("collection: " + str(collection))
            yield {
                'edition_id': collection['id'],
                'edition_name': collection['name'],
                'edition_acronym': collection['acronym'],
                'edition_release_date': collection['dtrelease'],
                'parent_edition_id': collection['idgrouped'] if collection['idgrouped'] != 0 else None,
            }