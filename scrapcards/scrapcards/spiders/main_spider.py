import json
from datetime import datetime, timezone
import scrapy
from scrapcards.items import EditionItem, CardItem


class MainSpider(scrapy.Spider):
    name = 'main_spider'

    BASE_URLS = {
        'mtg': 'https://www.ligamagic.com.br',
        'ptcg': 'https://www.ligapokemon.com.br',
        'ygo': 'https://www.ligayugioh.com.br',
        'lor': 'https://www.ligalorcana.com.br',
    }

    def __init__(self, game='lor', *args, **kwargs):
        super().__init__(*args, **kwargs)
        if game not in self.BASE_URLS:
            raise ValueError(f"game deve ser um de {list(self.BASE_URLS)}, veio {game!r}")
        self.game = game
        base = self.BASE_URLS[game]
        self.allowed_domains = [base.split('//', 1)[1]]
        self.start_urls = [f'{base}/?view=cards/edicoes']

    def parse(self, response):
        script = response.xpath("//script[contains(., 'jsonEditions')]/text()").get()
        i = script.index("{", script.index("jsonEditions"))
        data, _ = json.JSONDecoder().raw_decode(script[i:])

        main_collections = data["main"]
        auxiliary_collections = [f for daughters in data["aux"].values() for f in daughters] if data["aux"] else []
        all_collections = main_collections + auxiliary_collections
        now = datetime.now(timezone.utc).isoformat()

        for collection in all_collections:
            yield EditionItem(
                edition_id=collection['id'],
                edition_name=collection['name'],
                edition_acronym=collection['acronym'],
                edition_release_date=collection['dtrelease'],
                parent_edition_id=collection['idgrouped'] if collection['idgrouped'] != "0" else None,
                scraped_at=now,
            )
            yield scrapy.Request(
                url=response.urljoin(f'?view=cards/search&card=edid={collection["id"]}%20ed={collection["acronym"]}'),
                callback=self.parse_cards,
                cb_kwargs={'edition_id': collection['id']},
            )

    def parse_cards(self, response, edition_id):
        script = response.xpath("//script[contains(., 'cardsjson')]/text()").get()
        i = script.index("[", script.index("cardsjson"))
        cards, _ = json.JSONDecoder().raw_decode(script[i:])
        self.logger.info(f"edition {edition_id}: {len(cards)} cards")

        now = datetime.now(timezone.utc).isoformat()
        for card in cards:
            yield CardItem(
                id_external=card['id'],
                collection_id=edition_id,
                value_min=card['p1a'],
                value_avg=card['p1b'],
                value_max=card['p1c'],
                name_EN=card['nEN'],
                name_PT=card['nPT'],
                scraped_at=now,
            )
