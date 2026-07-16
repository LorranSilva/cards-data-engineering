# Metodologia — explorar e validar a fonte no Scrapy shell antes de escrever o spider

**Objetivo deste documento:** registrar um método **repetível** para, diante de uma fonte web nova, validar o modelo de dados **na mão** — offline, no Scrapy shell, contra uma página salva — antes de escrever uma linha de spider.

Aplicado aqui à lista de edições (`jsonEditions`) da Liga, mas os passos servem para **qualquer fonte que embuta dados em JS/JSON no HTML**. Onde aparecer algo específico da Liga (nome da variável, números esperados), troque pelo equivalente do seu caso.

> Levantado em 2026-07-16, durante a fase 1. Companheiro do [`diagnostico-fonte.md`](./diagnostico-fonte.md): o diagnóstico diz *o que* a fonte é; este documento diz *como validá-la* antes de automatizar.

---

## Por que fazer assim

1. **O crawl é caro.** Com `Crawl-delay: 360`, cada tentativa contra o site vivo custa 6 minutos. Contra uma página salva, é instantâneo.
2. **Validar antes de codar mata suposição errada cedo.** Se você descobre a estrutura no shell e confere contra contagens conhecidas, o spider nasce sobre fato, não palpite.
3. **A fixture é reproduzível.** Mesma entrada → mesmo resultado, sempre. Isso permite escrever **critério de aceite com número exato**.

**Princípio central:** primeiro o modelo de dados na mão; o spider é só a automação do que já foi provado.

---

## Pré-requisitos

- Uma página da fonte **salva localmente** (a *fixture*). Ex.: `docs/mtg.html`.
- Saber (do diagnóstico) que os dados estão **embutidos no HTML** numa variável JS — aqui, `let jsonEditions = {...}`.
- Ambiente com Scrapy (`uv run scrapy ...`).

---

## Regra de ouro do shell

O Scrapy shell é um **REPL Python** (IPython) com objetos do Scrapy já carregados (`response`, `fetch`, `view`…). **Tudo que você digita é Python.** URL e HTML só entram **dentro de aspas**, como argumento de uma função.

| Você digita | O que acontece | Certo |
|---|---|---|
| `?view=cards/edicoes` | erro — o `?` é o "help" do IPython, e URL não é Python | `fetch("https://…?view=cards/edicoes")` |
| `<script>` | `SyntaxError` — isso é HTML, não Python | `response.xpath("//script…")` |

Guarde isto: **o shell não é barra de endereços nem editor de HTML. É Python.**

---

## Os passos

Cada passo tem **objetivo**, **comando** e **resultado esperado**. Os valores esperados abaixo são do `mtg.html`; a tabela de aceite ao final traz os quatro jogos.

### 0. Abrir o shell já com a página carregada

- **Objetivo:** ter a variável `response` preenchida com a fixture, sem tocar no servidor.
- **Comando (no terminal, não dentro do shell):**
  ```
  uv run scrapy shell "file:///D:/Projetos/cards-data-engineering/docs/mtg.html"
  ```
- **Esperado:** o prompt do shell (`In [1]:`). O `response` já existe — você **não** redigita a URL lá dentro.
- *Para trocar de página já dentro do shell: `fetch("file:///D:/…")` — com parênteses e aspas.*

### 1. Confirmar que a página carregou

- **Objetivo:** garantir que `response` aponta para a fixture certa antes de qualquer parse.
- **Comando:**
  ```python
  response
  ```
- **Esperado:** `<200 file:///D:/…/mtg.html>`.

### 2. Extrair o texto do `<script>` que contém os dados

- **Objetivo:** isolar o bloco de JavaScript onde a variável está, saindo do HTML para uma string.
- **Comando:**
  ```python
  script = response.xpath("//script[contains(., 'jsonEditions')]/text()").get()
  len(script)
  ```
- **Esperado:** um número grande (dezenas/centenas de milhares). Se `script` for `None`, o `xpath` não achou — reveja o nome da variável.

### 3. Decodificar o objeto JS para um objeto Python

- **Objetivo:** transformar a string `{...}` num `dict` navegável, **sem adivinhar onde o objeto termina**.
- **Comando:**
  ```python
  import json
  i = script.index("{", script.index("jsonEditions"))
  data, _ = json.JSONDecoder().raw_decode(script[i:])
  list(data.keys())
  ```
- **Esperado:** `['main', 'aux']`.
- **Por que `raw_decode` e não regex:** `raw_decode` parseia **um** valor JSON e ignora o que vier depois. Você não precisa de um regex frágil tentando casar a chave `}` certa — aponta para o `{` inicial e ele acha o fim sozinho.

### 4. Entender a estrutura

- **Objetivo:** ver como a fonte organiza os dados (aqui: raízes em `main`, filhas agrupadas em `aux`).
- **Comando:**
  ```python
  len(data["main"])
  len(data["aux"])
  ```
- **Esperado:** `926` (pais/avulsas) e `130` (grupos).

### 5. Achatar numa coleção única

- **Objetivo:** juntar todos os registros num só iterável, para contar e transformar.
- **Comando:**
  ```python
  todas = data["main"] + [f for filhas in data["aux"].values() for f in filhas]
  len(todas)
  ```
- **Esperado:** `1489` (total = pais + filhas).

### 6. Inspecionar um registro

- **Objetivo:** ver os campos disponíveis, para decidir o que o item vai carregar.
- **Comando:**
  ```python
  todas[0]
  ```
- **Esperado:** um `dict` com `id`, `acronym`, `name`, `nameen`, `namept`, `nameptsa`, `dtrelease`, `idgrouped`, `icon`.

### 7. Validar a regra derivada (o parentesco)

- **Objetivo:** confirmar que a lógica que você vai codar (`idgrouped != "0"` → tem pai) bate com um número conhecido.
- **Comando:**
  ```python
  sum(1 for e in todas if e["idgrouped"] != "0")
  ```
- **Esperado:** `563` (as filhas).

### 8. Spot-checks pontuais

- **Objetivo:** conferir casos concretos que você conhece, não só agregados (agregado certo pode esconder erro sistemático).
- **Comando:**
  ```python
  [e for e in todas if e["id"] == "480601"]   # Foundations base
  [e for e in todas if e["id"] == "480602"]   # Foundations Tokens
  ```
- **Esperado:** o primeiro com `acronym="fdn"` e `idgrouped="0"` (raiz); o segundo com `acronym="tkfdn"` e `idgrouped="480601"` (pai = Foundations).

---

## Critério de aceite

O parse está correto quando os números batem **sem mudar o código** entre um jogo e outro (prova de que a parametrização é sólida):

| Fixture | total | raízes (`idgrouped="0"`) | filhas (`idgrouped≠"0"`) |
|---|---|---|---|
| `mtg.html` | 1489 | 926 | 563 |
| `poke.html` | 779 | 754 | 25 |
| `ygo.html` | 1233 | 1191 | 42 |
| `lor.html` | 19 | 19 | 0 |

Mais os dois spot-checks do Foundations. Se um jogo não bater, o erro está no **seu parse**, não na fonte — o número esperado é fato medido.

---

## Armadilhas aprendidas

- **Tudo no shell é Python.** URL/HTML digitados crus dão erro. (Ver "Regra de ouro".)
- **`raw_decode` > regex** para extrair JSON embutido: robusto, sem casar chaves à mão.
- **Os valores vêm como string:** `id` e `idgrouped` são `"480601"`, `"0"` — não `480601`, `0`. Compare com `"0"` (string) ou padronize o cast na entrada. Escolha uma e seja consistente.
- **Não trate o dado bruto como final:** o `acronym` aqui já vem limpo (`"fdn"`), mas o mesmo campo no cabeçalho `.tb-ed` vem `(FDN)` com parênteses. O nome do campo não garante o formato — confira.
- **Agregado certo não basta:** sempre feche com spot-check de caso conhecido.

---

## Do shell para o spider

O que você validou no shell **é** o miolo do estágio 1. A tradução é direta:

1. O passo 0 (abrir com a fixture) vira o `start_url` apontando para a página real.
2. Os passos 2–3 (extrair `<script>` + `raw_decode`) viram as primeiras linhas do método `parse`.
3. Os passos 5–7 (achatar + derivar o pai) viram o laço que emite um `yield` por edição.
4. A tabela de aceite vira o **teste** (fase 3, CI): rodar o parse contra as fixtures salvas e conferir as contagens — nunca crawl real no CI.

> Regra geral que fica: **desenvolva o parser contra fixtures no shell, prove com números conhecidos, e só então automatize.** O spider é a última etapa, não a primeira.
