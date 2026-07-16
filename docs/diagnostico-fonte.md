# Diagnóstico da fonte — Liga (Magic / Pokémon / Yu-Gi-Oh / Lorcana)

**Levantado em:** 2026-07-15
**Contexto:** fase 1 do roadmap. Os sites passaram por redesign e os spiders antigos (Splash + `.edc-nm-*`) estão quebrados. Este documento decide qual ferramenta usar e como a extração deve ser desenhada.

> Diagnóstico de site é perecível. Se a data acima tiver mais de alguns meses, reconfirme antes de confiar.

---

## Veredito

**Scrapy puro.** Sem Splash, sem Playwright, sem navegador.

Os dados das cartas vêm **prontos no HTML** servido pelo servidor, dentro de uma variável JavaScript (`var cardsjson`). Nenhum XHR carrega dado de carta. O JavaScript da página só **renderiza** o que já chegou.

Consequência direta: o Splash nunca foi necessário — o spider antigo renderizava a página inteira para depois ler o texto de uma tag `<script>` que já estava lá desde o primeiro byte.

**Ressalva que limita o veredito:** `Crawl-delay: 360` no `robots.txt` (ver [Restrições da fonte](#restrições-da-fonte)). A ferramenta está resolvida; o ritmo do crawl é o problema real.

---

## Escopo do que foi verificado

Investigação completa em **LigaMagic**. Nos demais, apenas confirmação de que o formato é o mesmo.

| Verificação | Magic | Pokémon | Yu-Gi-Oh | Lorcana |
|---|---|---|---|---|
| `cardsjson` no HTML cru | sim | sim | sim | sim |
| Mesmos nomes de campo | referência | sim | sim | sim |
| `robots.txt` conferido | sim | sim | sim | sim |
| `g_iTCG` | `1` | `2` | `3` | `9` |
| Hierarquia de edições | sim | sim | sim | sim |
| Rótulo "(Agrupada)" | sim | **não** | **não** | **não** |
| "EXIBIR MAIS" na lista de edições | sim | sim | sim | não |

Fixtures salvas em `tests/fixtures/` (mover de `docs/` — HTML de amostra é fixture de teste, não documentação).

---

## Restrições da fonte

### `robots.txt` — idêntico nos quatro sites conferidos

```
User-agent: CloudflareBrowserRenderingCrawler
Disallow: /

User-agent: *
Crawl-delay: 360
Disallow: /index.php
Disallow: /b/
Disallow: /decks/
Disallow: /dks/
Disallow: /*?view=user
Disallow: /*?view=cards/pricehistory
Disallow: /*?view=prod/pricehistory
Disallow: /*?view=dks/baixar
Disallow: /*?view=dks/comparar
Disallow: /*?view=dks/download
Disallow: /*?view=dks/editar
Disallow: /*?view=dks/evento
Disallow: /*?view=dks/export
Disallow: /*?view=dks/exportar
Disallow: /*?view=dks/import
Disallow: /*?view=dks/impressao
Disallow: /*?view=dks/imprimir
Disallow: /*?view=dks/imprimirpkm
Disallow: /*?view=dks/meus
Disallow: /*?view=dks/novo
Disallow: /*?view=dks/print
Disallow: /*?view=dks/versoes
Disallow: /*?view=dks/decks*filtro_nome_deck*
Disallow: /*?view=dks/decks*filtro_nome_jogador*
Disallow: /*?view=ref2/
Disallow: /*?view=bzr/
Disallow: /*?view=colecao/
Disallow: /*?view=ecom/
Disallow: /*?view=torneios/
Disallow: /*?view=forum/leiloes
Disallow: /*?view=forum/rss
Disallow: /*?view=mp/showcase/home*tcg*
Disallow: /*?view=mp/showcase/home*prod*
```

**As rotas necessárias estão liberadas:** `?view=cards/search` e `?view=cards/edicoes` não aparecem em nenhum `Disallow`. `ROBOTSTXT_OBEY = True` continua viável.

Três pontos que merecem registro:

- **`Crawl-delay: 360`** — seis minutos entre requisições. É a restrição que mais afeta o projeto.
- **`/*?view=cards/pricehistory` é bloqueado.** A fonte não quer que se raspe histórico de preço pronto. As nossas rotas estão liberadas e não há violação — mas este projeto constrói histórico a partir de snapshots, e a intenção do dono do site fica registrada aqui em vez de ser descoberta depois.
- **`CloudflareBrowserRenderingCrawler: Disallow: /`** — navegador headless é bloqueado nominalmente. Reforça a escolha do caminho sem Playwright.

### Infraestrutura

Os quatro sites são **a mesma aplicação parametrizada, com origem compartilhada**.

Evidência: todo o JS/CSS vem de `lmcorp.com.br`; o `robots.txt` é idêntico; a variável `g_iTCG` no `<head>` identifica o jogo; os assets seguem o padrão `tcg_<n>` (`advsearch/tcg_1_*.js`, `logo_tcg_1.png`).

**`g_iTCG`** — código interno do jogo na Liga, presente no `<head>` de toda página. Identifica de qual das Ligas a página veio; é o parâmetro que torna os quatro sites "a mesma aplicação". Valores **observados**: Magic=`1`, Pokémon=`2`, Yu-Gi-Oh=`3`, Lorcana=`9`. Não são sequenciais — é o id que a Liga atribui ao jogo (provavelmente ordem de lançamento dos sites), não uma contagem nossa. O rodapé lista outras Ligas (One Piece, FAB, RiftBound) que devem ocupar os números 4–8, não verificados.

O DNS **não** confirma isso: os sites estão atrás de Cloudflare (`172.66.x`, `2606:4700::/32`) e o IP de origem é invisível. IPs diferentes por site, portanto `CONCURRENT_REQUESTS_PER_IP` não serve para limitar o ritmo entre sites.

**Risco conhecido:** Cloudflare na frente significa que pode surgir bot protection. Hoje não há (requisições com `curl` passam limpas, sem challenge). Se o spider passar a receber `403` ou página de desafio, a causa é essa — e a resposta é reduzir o ritmo ou contatar a Liga, não contornar.

---

## Como a fonte funciona

### Ponto de entrada

`?view=cards/edicoes` — lista de edições com nome, sigla e hierarquia (pai → filhas). É daqui que o crawl parte.

**A árvore inteira vem no HTML cru.** Confirmado: cliquei em "EXIBIR MAIS" com o Network aberto e nenhuma requisição nova apareceu → é client-side, todas as edições já estão no HTML. O estágio 1 do spider é uma requisição só, sem paginação.

<!-- PREENCHER (verificar ao construir o estágio 1): a hierarquia pai→filha (as setas ↳) está codificada de forma parseável no HTML (aninhamento real), ou é só espaçamento visual? A estratégia de "marcar grupos internamente" depende disso. -->

### Duas formas de URL

```
Edição isolada:   ?view=cards/search&card=edid=<id>%20ed=<sigla>     (todos os sites)
Grupo mesclado:   ?view=cards/search&card=group=<id_da_base>          (só Magic)
```

- **`edid=<id>`** retorna **uma** edição isolada, em qualquer site. É a URL que o crawl usa (ver [Decisões tomadas](#decisões-tomadas)).
- **`group=<id>`** retorna o grupo inteiro mesclado (todas as sub-edições numa resposta). **Existe apenas no Magic**, acessível pelo link "(Agrupada)". Usa o id da edição base como âncora (Foundations base = `480601`, tokens = `480602`, grupo = `group=480601`).

**A distinção entre `edid=` e `group=` é por link, não por texto nem por id.** Na lista de edições, cada edição do Magic tem **dois** links: o do nome da coleção → `edid=` (a base isolada), e o do rótulo "(Agrupada)" → `group=` (o grupo mesclado). O mesmo número acessado pelas duas formas dá resultados diferentes: `edid=480601` = só a FDN base (291 cards); `group=480601` = as 11 sub-edições mescladas.

**Fora do Magic não existe `group=`.** Pokémon, Yu-Gi-Oh e Lorcana têm a mesma hierarquia pai→filha na árvore, mas sem o link "(Agrupada)" e sem página mesclada. Confirmado em Pokémon: o pai (Sparkling Fable, `edid=799 ed=CSV8C`) e suas filhas têm cartas **diferentes** — o pai por `edid=` não mescla nada. Para cobrir esses sites, cada edição (pai e filhas) é raspada individualmente por `edid=`.

Existem também edições **avulsas** — sem filhas e sem grupo (ex.: "Foundations Commander / FDC"). Pela estratégia uniforme (`edid=` para tudo) elas não são caso especial: são só mais uma edição na lista.

### Onde estão os dados

No fim do `<body>`, dentro de `$(document).ready()`:

```html
<script type='text/javascript'>
    $(document).ready(function() {
        var cardsjson = [{ ... }, { ... }];
        ...
        edc.init(cardsjson);
    });
</script>
```

Evidências de que é server-side e não renderizado:

- Os contêineres do grid (`#card-estoque`, `.grid-cardsinput`) vêm **vazios** no HTML. Nenhuma carta existe no DOM inicial.
- As 35 requisições Fetch/XHR da página somam **6,8 kB** — tudo Google Tag Manager, GA4 e telemetria. Nenhum dado de carta trafega por XHR.
- `curl` sem JavaScript retorna o `cardsjson` completo.

**Pegadinha:** os preços na tela aparecem como `R$ 0,95`, mas no payload são `"0.95"`. A vírgula é formatação criada pelo JS na renderização e **não existe no HTML**. Buscar pelo valor exibido não encontra nada.

### Cabeçalho da coleção

O seletor do spider antigo **sobreviveu ao redesign**:

```html
<div class='tb-ed'>
    <b>Foundations</b>
    <font class='tb-ed-sigla'>(FDN)</font>
</div>
```

Funciona igual em página de grupo e de edição avulsa. Note que a sigla vem **com parênteses** — `(FDN)` — e a coluna `collection.acronym` espera `FDN`.

### Paginação

**Não existe.** O botão "Mostrar mais" chama `edc.renderMore()`, que só renderiza mais itens do array já carregado. A coleção inteira vem numa requisição.

### Desenho do spider: a regra e a exceção

**A estratégia (a regra):** raspar cada edição individualmente por `edid=`, varrendo a lista de edições. Funciona nos quatro sites com um só caminho de código — cada edição é uma requisição, uma `collection`. O parentesco pai→filha é capturado como **dado** (ex.: `parent_edition_id`), lido da árvore da lista de edições, independente de existir `group=` ou não.

Isso separa o spider em dois estágios:

1. `parse` de `?view=cards/edicoes` → dicionário `{idE: (nome, sigla, id_do_pai)}`, incluindo o vínculo hierárquico de todos os sites
2. `parse` de cada edição (`edid=`) → emitir os itens, casando o `idE` com o dicionário para preencher nome, sigla e pai

(Repare: é a separação entre dimensão e fato aparecendo por necessidade do scraping, antes do dbt.)

**A otimização Magic-only (a exceção), NÃO implementada por ora:** o `group=` do Magic mescla as filhas numa requisição. Confirmado: `group=480601` retorna **11 `idE` distintos** (480601–480614) de uma vez, cortando o crawl do Magic em ~10×.

Por que fica de fora agora:

- O ganho é real, mas cobra imposto de complexidade: exige **separar** o `cardsjson` mesclado por `idE` (a página do grupo só nomeia o grupo no `.tb-ed`) e **deduplicar** — não raspar as filhas por `edid=` se já veio pelo grupo.
- A cadência é mensal, com folga de tempo de sobra. O desconto resolve um problema de tempo que provavelmente não temos.
- Otimizar antes de medir compra um segundo caminho de código a crédito. Se a fase 5 (capacidade) mostrar que o crawl do Magic dói, adiciona-se o `group=` **depois**, com número na mão.

Racional (decisão do dono do projeto): a Liga teve trabalho para agrupar o Magic e pode agrupar os outros sites no futuro. Capturando o parentesco como dado desde já, uma eventual chegada de `group=` nos demais sites vira só tratamento de valores — o histórico já tem o vínculo e nada quebra retroativamente. **Um spider da regra agora; outro (ou um caminho opcional) para a exceção, quando/se ela se generalizar.**

---

## Mapa de campos do `cardsjson`

Exemplo real (LigaMagic, grupo `group=480601` / Foundations, capturado em 2026-07-15):

```json
{
    "precoMenor": "3.25",
    "precoMaior": "19.99",
    "tag": null,
    "id": 76202,
    "nEN": "Arahbo, the First Fang",
    "nPT": "",
    "sC": "2W",
    "sT": "Legendary Creature - Cat Avatar",
    "sN": "2",
    "dN": "000000000000002",
    "pF": 0,
    "p1a": "3.25",
    "p1b": "8.14",
    "p1c": "19.99",
    "dt": "2024-10-25 20:55:20",
    "iCO": 4,
    "iR": 3,
    "idE": 480601,
    "iC": 8,
    "iCMC": 3,
    "iT": 1,
    "sA": "Simon Dominic",
    "sP": "\/arquivos\/in\/magic\/480601\/671c30ca...jpg",
    "iPP": 1,
    "iH": 0
}
```

### Confirmados

| Campo | Significado | Evidência |
|---|---|---|
| `nEN` / `nPT` | nome em inglês / português | batem com a tela; `nPT` vazio em carta sem tradução |
| `sC` | custo de mana | `"2WW"`, `"1BB"`; vazio em token, e a tela mostra "Custo de Mana" em branco |
| `iCMC` | custo de mana convertido | `2WW`→4, `1BB`→3, `1B`→2, `3GG`→5; conferido em 6 cartas de 2 edições |
| `sT` | tipo (texto) | `"Legendary Creature - Bison Ally"` |
| `iT` | tipo (código) | 1=criatura, 5=mág. instantânea, 6=feitiço; conferido em 2 edições |
| `iR` | raridade | 1=comum, 2=incomum, 3=rara, 4=mítica, 6=token; bate com "Raridade" da tela |
| `iC` | cor | 2=preto, 3=verde, 6=vermelho, 8=branco, 9=incolor (inferido do `sC`; azul não observado) |
| `idE` | id da edição | idêntico ao `edid=` da URL |
| `sN` | número da carta na edição | `"103"` |
| `dN` | chave de ordenação | `sN` zero-padded: `"000000000000103"` |
| `sA` | artista | `"Kev Walker"` |
| `sP` | caminho da imagem | `.jpg` em `/arquivos/in/<jogo>/<idE>/` |
| `dt` | **data do preview** | o dropdown de ordenação tem "Data do Preview"; os `dt` da TLA (`2025-08-14`, `2025-10-31`) antecedem o lançamento `21/11/2025` do `tb-info`. **Não é data de preço nem de lançamento.** |
| `p1a` / `p1b` / `p1c` | menor / médio / maior — **acabamento Normal apenas** | batem com o trio verde/amarelo/vermelho do modal "Preço Médio por Extras" |
| `precoMenor` / `precoMaior` | **duplicatas** de `p1a` / `p1c` | idênticos em toda a amostra. Só `p1b` traz informação nova. |

### Hipóteses (não confirmadas — não construa nada em cima)

| Campo | Hipótese | Evidência a favor | Como testar |
|---|---|---|---|
| `iPP` | é a primeira impressão da carta | reimpressão (Heartless Act) = 0; estreia = 1 | comparar mais reimpressões conhecidas |
| `iH` | a carta tem verso (dupla face) | 1 nos compostos de token, 0 no resto | conferir o `iH` de uma dupla face real (ex.: Aang, Master of Elements) |
| `id` | é da **carta**, não da impressão | Heartless Act tem id `56513` entre vizinhos `79xxx`, cadastrados na mesma janela | procurar `56513` na página de Ikoria — se for o mesmo id, confirmado |

### Desconhecidos
<!-- Exemplifique com um para eu fazer com os demais -->
| Campo | Situação |
|---|---|
| `iCO` | **Hipótese refutada.** Supus que contava impressões e previ 27 para Sire of Seven Deaths; a tela mostra só 3 edições. Valores observados: 27, 18, 14, 7, 4, 1, 0. Correlaciona com carta antiga/cobiçada, mas sem explicação. Hipótese alternativa não testada: variação percentual de preço (casaria com o menu "Cards em Alta/Queda"). |
| `pF` | `0` em toda a amostra das duas edições. Nome sugere foil, mas o Sire tem foil a R$ 158,75 e o campo continua 0. <!-- PREENCHER: resultado de `grep -o '"pF":[0-9]*' fdn.html \| sort -u` --> |
| `tag` | `null` em toda a amostra |

---

## Limitações conhecidas da fonte

**Só o acabamento Normal.** O modal de detalhes mostra que uma carta tem preços por acabamento — Normal, Foil, Promo, Pre-Release — cada um com seu trio menor/médio/maior. O `cardsjson` traz **apenas o Normal**. Confirmado no Sire of Seven Deaths: `p1a`/`p1c` = `104.99`/`179.99` = exatamente a linha "Normal" do modal; as outras três linhas não existem no payload.

Os preços de Foil/Promo/Pre-Release só existem na **página de detalhe da carta** — uma requisição por carta, milhares por edição. A 360s cada, é inviável. Ver [Decisões tomadas](#decisões-tomadas).

**Nenhum campo carrega o momento do preço.** Todos os campos temporais (`dt`) são estáticos. A fonte não diz quando o preço foi apurado. Isso torna o `scraped_at` da fase 4 **obrigatório**: sem ele não existe série temporal.

**`p1b` pode cair fora da faixa `[p1a, p1c]`.** Caso real — Goblin 1/1 (TKFDN): `p1a: 0.97`, `p1b: 1.14`, `p1c: 1.00`. A média está acima do máximo. Provavelmente `p1b` é média de uma janela passada de vendas, enquanto `p1a`/`p1c` são ofertas atuais. Raro (1 em ~12 na amostra), o que o torna mais perigoso: passa despercebido até virar KPI. Vira teste de qualidade no dbt (fase 7) — como **warning**, não erro, porque é defeito da fonte e não nosso.

**`p1b` diverge do valor exibido.** Payload: `139.90`. Modal: `140,18`. O menor e o maior batem no centavo; a média não. Cadência de recálculo diferente, ou momentos de captura distintos. Não investigado — mais um motivo para não tratar `p1b` como verdade absoluta.

**O `cardsjson` é uma lista de produtos vendáveis, não de cartas.** Em edições de token, o cartão físico traz dois tokens sem relação (ex.: Food de um lado, Treasure do outro), e a Liga cadastra **os três**: `Food (#22)`, `Treasure (#23)` e `Food (#22) // Treasure (#23)`. Os três têm ofertas e faixas de preço distintas — são anúncios reais, não duplicatas.

Consequências: `len(cardsjson)` **não** é "quantidade de cartas da coleção" (é quantidade de produtos listados), e somar preços conta o mesmo cartão físico mais de uma vez. Não é bug da fonte — é rótulo errado do spider antigo. Nomeie pelo que é e decida o KPI na fase 7.

Atenção: `//` no `nEN` **não** marca duplicata. Dupla face legítima existe em edições normais (ex.: Aang, Master of Elements) e é uma carta única.

---

## Decisões tomadas

| Decisão | Por quê |
|---|---|
| **Scrapy puro; Splash sai, nada entra no lugar** | dados server-side no HTML; renderização é desnecessária |
| **Raspar cada edição por `edid=` (uniforme nos 4 sites)** | `group=` só existe no Magic; a estratégia uniforme funciona em todos com um caminho de código só, sem lógica de split/dedup |
| **`group=` (Magic) fica como otimização diferida** | ganho real (~10×) mas com imposto de complexidade; a cadência mensal tem folga. Revisitar na fase 5 se o crawl do Magic doer. "Spider da regra agora, exceção depois." |
| **Capturar o parentesco pai→filha como dado, em todos os sites** | a hierarquia existe na árvore de edições mesmo sem `group=`. Marcando o vínculo desde já, uma futura chegada de `group=` nos outros sites vira só tratamento de valores, sem quebra retroativa |
| **Spider em dois estágios** (lista de edições → edições) | o nome/sigla/pai das edições só existe na lista; o estágio 2 raspa cada edição e casa pelo `idE` |
| **`DOWNLOAD_DELAY` explícito respeitando os 360s** | `ROBOTSTXT_OBEY` filtra URLs proibidas mas **não aplica `Crawl-delay`**; `AUTOTHROTTLE_MAX_DELAY` tem padrão 60s. As duas configs que parecem resolver, não resolvem. |
| **Crawl mensal** | **Revisável.** Não é imposição da fonte: 360s comporta semanal folgado (~30h/site × 4 sites = 120h de 720h no mês). Mensal é escolha de simplicidade e boa vizinhança. Custo: 12 pontos/ano — bom para tendência, cego para picos que sobem e voltam em 2 semanas. **A frequência real depende do KPI, que ainda não foi definido.** Lembre: dá para reamostrar semanal→mensal; nunca o contrário. Dado temporal não capturado está perdido. |
| **Sites em sequência, nunca em paralelo** | origem compartilhada. 4 sites em paralelo a 360s = 1 req/90s no servidor real: respeita a letra, fura o espírito. **Isso invalida "crawls paralelos" previsto na fase 6.** |
| **`JOBDIR` para retomada** | um crawl de ~30h será interrompido. Pegadinhas: só serializa em shutdown gracioso (1× Ctrl+C), e usar `-o` (append) e não `-O` (overwrite) — retomar sobrescrevendo apaga o já coletado. |
| **`scraped_at` gravado por item, no yield** | um crawl de 30h não é um snapshot: é um borrão de 30h. Carimbar a data da execução em todas as linhas seria mentira. |
| **Foil/Promo/Pre-Release ficam de fora** | custa 1 requisição por carta. **Escolha, não esquecimento** — e escolha com perda irreversível: a série de preço foil só começa quando decidirmos capturar. |
| **Raridade (`iR`) entra desde já** | está no payload, custa zero. Não capturar não economiza nada. |
| **O spider emite todos os campos do payload** | a requisição já foi paga e o JSON já foi parseado; emitir 22 campos em vez de 6 custa zero e preserva liberdade para quando os KPIs existirem. Quem escolhe o que vira coluna é a carga, não o spider. |
| **`average_price` grafado correto desde o início** | ver fase 2 |

---

## Em aberto

Nada aqui bloqueia a fase 1.

- [ ] A hierarquia pai→filha está codificada de forma parseável no HTML da lista de edições (aninhamento real, não só espaçamento)? Verificar ao construir o estágio 1 — a captura do parentesco depende disso.
- [ ] `pF`: resultado do `grep -o '"pF":[0-9]*' fdn.html | sort -u`
- [ ] `iCO`: sem hipótese viável
- [ ] `id` é da carta ou da impressão? (teste do Heartless Act em Ikoria)
- [ ] Quantos casos de `p1b` fora da faixa existem? (o Goblin não deve ser o único)
- [ ] **Para a fase 5 (capacidade), não bloqueante:** contar edições e grupos por site — `grep -o 'card=edid=[0-9]*' edicoes.html | sort -u | wc -l` e o mesmo com `group=`. Dá o tamanho real do crawl e quanto o `group=` do Magic economizaria.
- [ ] Lorcana entra no escopo? A tabela `game` só tem `ptcg`, `ygo`, `mtg`. Sugestão: usar Lorcana **depois** do spider base pronto, como teste da parametrização — se custar mais que uma subclasse de 5 linhas + 1 `INSERT`, a abstração está errada.

---

## Nota de método

Quatro hipóteses foram levantadas e **refutadas pelos dados** durante este diagnóstico:

1. `dt` seria data de atualização do preço → depois, data de lançamento da edição → é data do preview.
2. `iT` separaria carta individual de composto → é o tipo da carta. A correlação era espúria: na edição de tokens, todo token individual era criatura por acaso.
3. `iCO` contaria impressões, com previsão de 27 para o Sire of Seven Deaths → a tela mostrou 3 edições.
4. "Raspar grupos via `group=`" seria a estratégia geral → o `group=` só existe no Magic. A estratégia foi derivada de um site e generalizada para os quatro.

Todas soavam plausíveis. A #2 e a #4 caíram pelo mesmo motivo: **amostra homogênea gera conclusão falsa.** A #2 vinha de uma edição só, de um tipo só; a #4, de um site só. Nos dois casos foi preciso cruzar com um caso diferente (outra edição; outro site) para a generalização indevida cair.

**Daí as duas regras deste documento:** testar hipótese com amostra diversa antes de codificar filtro em cima dela, e marcar explicitamente o que é certeza e o que é palpite. Um documento que não separa os dois transforma chute em fato na cabeça de quem lê depois — inclusive na do autor.
