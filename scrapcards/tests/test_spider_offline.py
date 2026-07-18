"""Teste offline do MainSpider contra fixtures salvos (docs/*.html).

Não faz rede: constrói um HtmlResponse a partir do HTML salvo e chama os
métodos parse/parse_cards direto. É a prova de que o parsing funciona nos
4 jogos (estágio 1) e numa coleção (estágio 2), e a semente do CI da fase 3.

Rodar (de qualquer lugar):  uv run python scrapcards/tests/test_spider_offline.py
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]        # raiz do repositório
sys.path.insert(0, str(ROOT / 'scrapcards'))              # onde vive o pacote scrapcards
FIXTURES = ROOT / 'docs'

import scrapy
from scrapy.http import HtmlResponse
from scrapcards.items import EditionItem, CardItem
from scrapcards.spiders.main_spider import MainSpider


def response_from(fixture, url):
    body = (FIXTURES / fixture).read_bytes()
    return HtmlResponse(url=url, body=body, encoding='utf-8')


# Contagens confirmadas no diagnóstico: (total de edições, quantas têm pai).
EXPECTED = {
    'mtg.html':  (1489, 563),
    'poke.html': (779, 25),
    'ygo.html':  (1233, 42),
    'lor.html':  (19, 0),
}


def test_stage1_editions_all_games():
    spider = MainSpider(game='lor')  # o jogo não afeta o parsing, só a URL base
    for fixture, (total, com_pai) in EXPECTED.items():
        resp = response_from(fixture, 'https://www.ligalorcana.com.br/?view=cards/edicoes')
        out = list(spider.parse(resp))
        editions = [o for o in out if isinstance(o, EditionItem)]
        requests = [o for o in out if isinstance(o, scrapy.Request)]
        assert len(editions) == total, f"{fixture}: {len(editions)} edições != {total}"
        assert len(requests) == total, f"{fixture}: {len(requests)} requests != {total}"
        pais = sum(1 for e in editions if e['parent_edition_id'] is not None)
        assert pais == com_pai, f"{fixture}: com_pai {pais} != {com_pai}"
    print("estágio 1 OK:", EXPECTED)


def test_stage2_one_collection():
    """Uma coleção do Lorcana: 262 cartas, com a FK vinda do cb_kwargs."""
    spider = MainSpider(game='lor')
    resp = response_from('lor.html', 'https://www.ligalorcana.com.br/?view=cards/search&card=edid=17')
    cards = list(spider.parse_cards(resp, edition_id=17))
    assert all(isinstance(c, CardItem) for c in cards)
    assert len(cards) == 262, f"{len(cards)} != 262"
    c0 = cards[0]
    assert c0['collection_id'] == 17, "FK deve vir do cb_kwargs, não do payload"
    for f in ('id_external', 'value_min', 'value_avg', 'value_max', 'name_EN', 'name_PT', 'scraped_at'):
        assert f in c0, f"campo ausente: {f}"
    print("estágio 2 OK: 262 cartas | amostra =", dict(c0))


if __name__ == '__main__':
    test_stage1_editions_all_games()
    test_stage2_one_collection()
    print("\nTODOS OS TESTES PASSARAM")
