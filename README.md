# Cards Data Engineering

Pipeline de engenharia de dados sobre coleções de cartas colecionáveis (Magic, Pokémon, Yu-Gi-Oh e Lorcana), a partir dos sites da Liga. Portfólio de estudos: um projeto iniciado em 2023, sendo reconstruído com práticas de engenharia de dados de ponta a ponta — extração, orquestração, transformação e visualização.

## Objetivo

Evoluir de um scraping manual (Scrapy → JSON → carga manual no Postgres) para um **pipeline orquestrado**, com camada de transformação (dbt), KPIs em dashboard (Streamlit) e uma API de leitura (FastAPI), tudo containerizado.

## Estado atual

Fase 1 (reconstrução da extração) concluída na parte offline: os sites passaram por redesign e o scraping foi refeito do zero. Os dados vêm **prontos no HTML server-side** (variáveis JS `jsonEditions` e `cardsjson`) — sem API interna, sem navegador. Um único spider parametrizado (`main_spider`) serve os 4 jogos em dois estágios: **dimensão** (edições, com hierarquia pai→filha) e **fato** (cartas).

Diagnóstico completo da fonte: [`docs/diagnostico-fonte.md`](docs/diagnostico-fonte.md).

## Stack alvo

| Camada | Ferramenta |
|---|---|
| Extração | Scrapy puro (dados server-side; Splash descontinuado) |
| Orquestração | Apache Airflow (Docker Compose) |
| Armazenamento | PostgreSQL |
| Transformação | dbt Core sobre o Postgres |
| Dashboard | Streamlit + Plotly |
| API | FastAPI + Uvicorn |
| CI/CD | GitHub Actions + GHCR |
| Infra | Docker Compose (stack completa) |

## Arquitetura (fluxo de dados)

1. **Spider** (`scrapcards/scrapcards/spiders/main_spider.py`) — estágio 1 parseia `jsonEditions` → `EditionItem`; estágio 2 raspa cada edição por `edid=` → `CardItem`. A identidade da edição viaja no `cb_kwargs`.
2. **Datasets** (`scrapcards/datasets/*.json`, gitignored) — saída via `FEEDS`, roteada por tipo de item (`editions.json`, `cards.json`).
3. **Carga** (`notebooks/`) — insere os JSONs no PostgreSQL.
4. **Banco** (`scripts/database-tables.sql`) — hierarquia `game` → `collection` → `card`.

## Como rodar

```bash
# Dependências (uv gerencia o ambiente; ver pyproject.toml / uv.lock)
uv sync

# Teste offline do spider (não faz rede — usa os fixtures em docs/*.html)
uv run python scrapcards/tests/test_spider_offline.py

# Crawl real — de scrapcards/, um jogo por vez, com retomada:
#   game = mtg | ptcg | ygo | lor
uv run scrapy crawl main_spider -a game=lor -s JOBDIR=crawls/lor
# -a limit=N  → (opcional) limita a N coleções, para smoke test
# use -o (append), nunca -O (overwrite), para não perder o já coletado ao retomar
```

> ⚠️ O `robots.txt` da fonte pede `Crawl-delay: 360` (6 min entre requisições). O `DOWNLOAD_DELAY = 360` respeita isso — um crawl completo leva dias. **Sites em sequência, nunca em paralelo** (origem compartilhada).

## Roadmap

O detalhamento de cada fase vive em [`.claude/fases/`](.claude/fases/) (entregas, conceitos e critérios de conclusão).

| # | Fase | Em uma linha |
|---|---|---|
| 1 | **Reconstrução da extração** | Diagnóstico do site novo; spider único parametrizado em dois estágios (dimensão/fato). ✅ offline |
| 2 | **Saneamento** | Notebook → módulos testáveis; padronizar campos; credenciais por variável de ambiente. |
| 3 | **CI** | GitHub Actions com ruff + pytest sobre fixtures salvas — nunca crawl real no CI. |
| 4 | **Dimensão temporal** | `scraped_at` em spiders e tabelas; cada execução vira um snapshot. |
| 5 | **Custo por linha e capacidade** | Bytes/linha no Postgres, projeção 1M; define frequência e retenção do crawl. |
| 6 | **Airflow** | DAG: crawls (em sequência) → validação que falha alto → carga → dbt. |
| 7 | **dbt** | Sources, staging e marts de KPI; testes de qualidade; `dbt build` no CI. |
| 8 | **Streamlit** | Dashboard lendo apenas os marts. |
| 9 | **API (FastAPI)** | Leitura sobre os marts, paginação obrigatória; KPI nunca calculado na API. |
| 10 | **Containerização + CD** | Dockerfiles + compose completo; imagens publicadas no GHCR a cada merge. |

## Documentação

- [`docs/diagnostico-fonte.md`](docs/diagnostico-fonte.md) — como a fonte funciona, campos, decisões de crawl (fonte da verdade operacional).
- [`docs/fase1-1-metodologia-exploracao-fonte.md`](docs/fase1-1-metodologia-exploracao-fonte.md) — método repetível para validar a fonte no scrapy shell antes de escrever o spider.
- [`docs/dicionario.md`](docs/dicionario.md) — vocabulário técnico do projeto.
