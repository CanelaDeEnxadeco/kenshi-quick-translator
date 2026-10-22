<div align="center">

[🇺🇸 English](README.md) · **🇧🇷 Português**

</div>

<div align="center">

# 🗡️ Kenshi Quick Translator

**Traduza mods de Kenshi rapidamente, sem estragar os códigos do jogo.**

![Versão](https://img.shields.io/badge/vers%C3%A3o-0.6.5-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-yellow)
![Plataforma](https://img.shields.io/badge/plataforma-Windows-lightgrey)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)
![Idiomas do programa](https://img.shields.io/badge/interface-PT%20%C2%B7%20EN%20%C2%B7%20ES%20%C2%B7%20RU%20%C2%B7%20ZH-orange)

Programa de janela para Windows que **lê o `.mod`**, **traduz todos os textos** (diálogos, nomes, descrições…), deixa você **revisar lado a lado** e **instala a tradução direto no Kenshi**, sem nunca alterar o arquivo original.

<!-- 📸 COLOQUE AQUI um print da tela principal: docs/img/tela-principal.png -->
<!-- ![Tela principal](docs/img/tela-principal.png) -->

</div>

---

## 📑 Índice

- [✨ Destaques](#-destaques)
- [🖼️ Capturas de tela](#️-capturas-de-tela)
- [🚀 Como usar](#-como-usar)
- [🧭 Conhecendo a tela](#-conhecendo-a-tela)
- [🌐 Serviços de tradução](#-serviços-de-tradução)
- [🛡️ Como ele protege o seu mod](#️-como-ele-protege-o-seu-mod)
- [📝 Revisão das traduções](#-revisão-das-traduções)
- [📦 Instalar, restaurar e limpar](#-instalar-restaurar-e-limpar)
- [🎨 Aparência e conforto](#-aparência-e-conforto)
- [⌨️ Atalhos do teclado](#️-atalhos-do-teclado)
- [💻 Linha de comando](#-linha-de-comando)
- [🧱 Dependências](#-dependências)
- [🔨 Gerando o `.exe`](#-gerando-o-exe)
- [🧪 Testes](#-testes)
- [🗂️ Estrutura do projeto](#️-estrutura-do-projeto)
- [🛠️ Como foi feito](#️-como-foi-feito)
- [🙏 Créditos](#-créditos)
- [⚠️ Limites conhecidos](#️-limites-conhecidos)
- [📜 Licença](#-licença)

---

## ✨ Destaques

| | |
|---|---|
| 🔎 **Lê o idioma pelo conteúdo** | Detecta o idioma de cada mod (e até de cada texto) em vez de confiar no nome do arquivo. |
| 🌍 **Mods com mais de um idioma** | Um mod com inglês **e** chinês? Cada texto vai ao serviço com o idioma certo. |
| 🔁 **Vários serviços em um só** | Modo *agregado*: Google, Bing, Microsoft e Yandex gratuitos, mais DeepL, Google Cloud, LibreTranslate e IAs. Se um bloqueia, o programa troca sozinho. |
| 🛡️ **Códigos do jogo protegidos** | Marcadores como `/TEAMUP/` são guardados antes da tradução e conferidos depois. |
| ⚡ **Rápido** | Lotes em paralelo, memória de tradução e texto repetido enviado só uma vez. |
| 💾 **Nunca perde o trabalho** | O progresso é gravado aos poucos. Pode fechar e continuar depois. |
| 🧐 **Revisão lado a lado** | Tabela com original e tradução, contador de textos duvidosos, desfazer, segunda passada. |
| 📦 **Instala em um clique** | Coloca o mod traduzido na pasta do jogo, ativa no `mods.cfg` e guarda o original. |
| ♻️ **Reversível** | Botão **Restaurar o original** devolve o mod como estava. |
| 🗣️ **Interface em 5 idiomas** | Português, English, Español, Русский e 中文. |

---

## 🖼️ Capturas de tela

> 📸 *Adicione aqui os seus prints na pasta `docs/img/` e descomente as linhas abaixo.*

<!--
| Lista de mods | Como traduzir |
|---|---|
| ![Lista](docs/img/lista-de-mods.png) | ![Traduzir](docs/img/como-traduzir.png) |

| Revisão | Configurações |
|---|---|
| ![Revisão](docs/img/revisao.png) | ![Configurações](docs/img/configuracoes.png) |

| Serviços do agregado | Modo escuro |
|---|---|
| ![Serviços](docs/img/servicos.png) | ![Escuro](docs/img/modo-escuro.png) |
-->

---

## 🚀 Como usar

### ▶️ Opção 1: com o `.exe` (sem instalar nada)

1. Gere o `.exe` seguindo [Gerando o `.exe`](#-gerando-o-exe) (ou baixe um já pronto, se existir em *Releases*).
2. Abra `KenshiQuickTranslator.exe`.
3. Escolha o mod na lista → escolha o idioma → **Traduzir este mod**.
4. Revise o que quiser → **Instalar no jogo**.

### 🐍 Opção 2: pelo código-fonte

1. Instale o **Python 3.10 ou mais novo** em [python.org](https://www.python.org/). Na instalação, marque **"Add python.exe to PATH"**.
2. Dê dois cliques em `instalar.bat` (uma vez só).
3. Dê dois cliques em `abrir.bat`.

> 💡 Se o Kenshi não for achado sozinho, use **Pasta do Kenshi…**. Para mods que estão fora da instalação, use **Abrir arquivo…**.

### 📋 Passo a passo para um mod do Workshop

1. Na lista, selecione o mod que aparece como **Workshop**.
2. Clique em **Copiar mod para a pasta do jogo** (copia a pasta inteira do mod, com modelos e texturas; o Workshop não é alterado).
3. Selecione o mesmo mod, agora na linha **Pasta mods**.
4. Escolha o idioma e clique em **Traduzir este mod**.
5. Ao terminar, clique em **Instalar no jogo**.
6. Abra o Kenshi (ou o FCS) e confira.

---

## 🧭 Conhecendo a tela

À esquerda fica a **lista dos seus mods**; à direita, **três passos**.

### 📚 Lista de mods

- 🖼️ **Ícone** de cada mod (PNG, JPG, GIF, BMP), quando o mod traz imagem.
- 🌐 **Idioma** detectado pelo conteúdo, com a sigla: `Inglês (en)`, `Chinês (zh)`…
- 📊 **Feito**: quanto já foi traduzido, por mod e idioma de destino.
- 📍 **Onde**: *Pasta mods* ou *Workshop*.
- 🔎 Busca, filtros (todos / Workshop / pasta mods…) e ordenação.
- ✅ Seleção múltipla com **Ctrl+clique** para traduzir em **fila**.
- 🧩 Dois mods com o **mesmo nome** (Steam e pasta local) são tratados separados, cada um com o seu projeto.

### 1️⃣ Mod escolhido

Mostra o nome, **quantos textos há para traduzir** e **quantos textos de cada idioma** o programa encontrou (ex.: `31225 textos para traduzir. Idioma: Chinês (zh) 20375 · Inglês (en) 15 · Japonês (ja) 11…`).

### 2️⃣ Como traduzir

- 🌐 **Idioma do mod** (ou *Detectar automaticamente*) e **Traduzir para**.
- ☑️ **Este mod tem mais de um idioma** (ex.: inglês e chinês). O programa já sugere sozinho quando detecta.
- ☑️ **Não traduzir nomes de personagens**.
- 🔧 **Serviço** e botão **Testar serviço**.
- ⚙️ **Serviços do agregado…** (IAs, DeepL, Google Cloud…).
- 🏎️ **Velocidade**: de 1 a 12 partes ao mesmo tempo.
- ▶️ **Traduzir este mod** · ▶▶ **Traduzir selecionados** · ⏹ **Parar**.
- 🔁 **Refazer automáticas** e **Segunda passada nos "Conferir"**.
- ☑️ **Instalar no jogo ao terminar (fila)**.
- 📈 **Gráfico de velocidade** (textos por minuto, com o pico) ao lado da barra de progresso.

### 3️⃣ Revise e gere o mod

- 🗃️ Tabela com **Estado**, **Original** e **Tradução**.
- ✏️ Caixa de edição: corrija e aperte **Ctrl+Enter** para aplicar e ir para a próxima.
- 🔎 Busca e filtros por estado e por idioma de origem.
- 🧮 Contadores: `31225 textos | 0 pendentes | 31021 automáticos | 1 p/ conferir`.
- 🛠️ **Gerar mod de tradução…** · **Instalar no jogo** · **Restaurar o original** · **Glossário…** · **Exportar PO…** · **Importar PO…**

---

## 🌐 Serviços de tradução

### 🆓 Gratuitos (sem chave), usados juntos no modo **Agregado**

| Serviço | Observação |
|---|---|
| Google | rápido, o mais usado |
| Google 2 | outro caminho do Google, com limite próprio |
| Bing | |
| Microsoft | |
| Yandex | |

> ⚠️ São endereços **não oficiais**: podem limitar ou mudar a qualquer momento. O agregado reduz os bloqueios, mas não os impede.

### 🔑 Com chave própria

| Serviço | Observação |
|---|---|
| DeepL | boa qualidade (a chave gratuita termina em `:fx`) |
| Google Cloud Translation | v2 (chave de API) e v3 (conta de serviço ou `gcloud`) |
| LibreTranslate | seu próprio servidor, chave opcional |
| IAs no formato OpenAI | Gemini, DeepSeek, OpenRouter, Groq, Qwen e qualquer um compatível: você informa URL, modelo e chave |
| Simulado | não traduz de verdade; serve para testar o programa |

### 🧠 Como o agregado funciona

- 🔄 **Rodízio**: cada lote começa por um serviço diferente, dividindo o trabalho.
- ⏸️ **Quarentena**: um serviço que falha (429, 403, 5xx, tempo esgotado, resposta ruim) sai de circulação por 1 minuto, dobrando a cada falha seguida (máx. 10 min).
- 🧩 **Falha parcial**: o que já veio é aproveitado e o resto do lote vai para o próximo serviço.
- 🚦 **Limitador por serviço**: espaça os pedidos para não ser bloqueado (valores prudentes, não oficiais).
- 📣 **Avisos em português** quando troca de serviço (dá para desligar em Configurações).
- 🗝️ **Várias chaves** do mesmo serviço, separadas por `;`, para dividir a carga.
- 🔍 **Janela "Serviços do agregado"**: marque/desmarque, reordene com ▲▼, cadastre serviços com chave, escolha modelos prontos e use **Testar todos**.
- ⏳ Se todos caem, o programa espera e tenta de novo; só depois para, guardando o que já foi traduzido.

---

## 🛡️ Como ele protege o seu mod

| Proteção | O que faz |
|---|---|
| 🏷️ **Marcadores do jogo** | `/TEAMUP/`, `/BROTHER/`, `/BASTARD/s`… são protegidos antes de ir ao serviço e conferidos depois. Se um se perder, o programa tenta de outras formas; se não der, mantém o original e marca **Conferir**. Nenhuma tradução com marcador perdido é gravada. |
| 📖 **Glossário** | Termos que devem sair sempre iguais ou não ser traduzidos. Os de fábrica são sugestões, edite à vontade. |
| 🧑 **Nomes de personagens** | Ficam como estão (dá para desmarcar). |
| 🧬 **Campos de texto** | Como o programa original, traduz todos os campos de texto, menos os da lista `translator_blacklist.txt` (11 campos técnicos, como `bone name` e `anim name`). |
| 🧯 **Filtro de código** | Campos que parecem código (nome de arquivo, caminho, identificador colado, palavra solta em minúsculas) ficam em inglês, e o programa avisa quais. Para forçar a tradução de um campo, use `translator_liberados.txt`. |
| 💾 **Projetos salvos** | Atualizar o mod não apaga o seu trabalho. Se o texto original mudou, a linha volta como **Conferir**. |
| 🔬 **Conferência final** | O arquivo gerado é lido de volta e comparado com o projeto. Se algo estiver errado, **não instala**. |
| 🔒 **Original intacto** | O `.mod` original nunca é alterado ao gerar. Ao instalar, ele é guardado como `<nome>.mod.original`. |

---

## 📝 Revisão das traduções

- ⚠️ **Contador de duvidosos** (`⚠ N duvidosos`) e filtro **Duvidosos**: junta os textos em *Conferir*, os de marcadores que não batem e os "traduzidos" iguais ao original.
- 🎨 **Marcadores coloridos** nos dois campos: verde = bate; vermelho = falta ou sobra.
- ↶ **Desfazer edição** (Ctrl+Shift+Z), até 200 níveis por mod aberto.
- 🔁 **Segunda passada nos "Conferir"**: refaz só esses textos com outro serviço e só troca quando o resultado melhora; o que você revisou não é alterado.
- 🌐 **Filtro por idioma de origem** (aparece quando o mod tem 2+ idiomas).
- 📤📥 **Exportar/Importar `.po`**: edite no Poedit e traga de volta.
- 🧰 **Refazer automáticas**: traduz de novo as traduções automáticas (o que você revisou à mão é preservado) e faz uma cópia de segurança do projeto antes.

---

## 📦 Instalar, restaurar e limpar

### 📥 Instalar no jogo

- Põe o mod traduzido em `Kenshi/mods/<nome>/` com o **mesmo nome** do original (ele ocupa o lugar do original no jogo).
- Guarda o original como `<nome>.mod.original`, uma vez só.
- Garante que o mod está ativo em `data/mods.cfg`, **com backup** do `mods.cfg`.
- Se o mod é do Workshop, use antes **Copiar mod para a pasta do jogo**: a pasta inteira é copiada (modelos, texturas, `.info`, imagem).
- Traduzir depois para **outro idioma** simplesmente troca a tradução instalada; o programa lê sempre o original.

### 🧬 Dois tipos de mod traduzido (⚙ Configurações)

| Tipo | O que é |
|---|---|
| **Completo** (padrão) | Cópia do original com os textos traduzidos, mesmo nome, substitui o original no jogo. Não depende do original. |
| **Dependente** | Só o que mudou, num arquivo `Nome IDIOMA.mod` em pasta própria, ativado logo depois do original no `mods.cfg`. O original precisa continuar instalado. |

### ↩️ Restaurar o original

Botão ao lado de **Instalar no jogo**: devolve o `.mod` original e deixa a tradução ao lado como `<nome>.mod.traduzido`. A cópia `.original` é mantida.

### 🧹 Limpar dados

Em **Configurações → Limpar dados…** você escolhe o que apagar, vendo a quantidade e o tamanho de cada item:

- 💾 Traduções salvas (o progresso de cada mod)
- 🗄️ Cópias de segurança dos projetos
- 🧠 Memória de tradução
- 🌐 Idiomas detectados nos mods
- 📖 Glossário
- ⚙️ Configurações e chaves dos serviços

> 🔒 Só apaga **dados do próprio programa**. Os mods, o `mods.cfg` e as cópias `.original` na pasta do Kenshi **não são mexidos**.

### 🗑️ Zerar a tradução de um mod

Botão **Zerar tradução deste mod**: apaga o progresso salvo daquele mod (com cópia de segurança). Para abrir a pasta dos projetos: **Abrir pasta dos projetos**.

### 📁 Onde ficam os dados

`%APPDATA%\KenshiQuickTranslator\` — projetos (`projetos\<Mod>.<idioma>.ktproj.json`), memória de tradução (`memoria.sqlite`), configuração (`config.json`), glossário e as listas de campos.

---

## 🎨 Aparência e conforto

- 🗣️ **Idioma do programa**: Português, English, Español, Русский, 中文 (é o idioma dos menus, não o da tradução do mod).
- 🌗 **Tema**: claro, escuro ou automático (segue o Windows).
- 🔠 **Tamanho da letra**: de 85% a 150%.
- 🧭 **Passo a passo guiado** na primeira abertura (botão **Passo a passo** no topo reabre quando quiser).
- 💬 **Dicas** ao passar o mouse nos campos.
- 📉 **Gráfico de velocidade** durante a tradução.
- 🔔 Som e janela piscando quando a tradução ou a fila termina (opcional).
- 🪟 A janela lembra tamanho, posição e a última seleção; em janela estreita, a lista vira um painel que abre e fecha (F9).
- 🚨 **Erros com botões**: se o serviço quebra no meio, a janela oferece **Tentar de novo** (continua de onde parou) e **Trocar de serviço…**.

---

## ⌨️ Atalhos do teclado

| Atalho | Ação |
|---|---|
| `Ctrl+T` | traduzir este mod |
| `Ctrl+Shift+T` | traduzir os mods selecionados |
| `Esc` | parar |
| `F5` | atualizar a lista de mods |
| `F6` | gerar o mod de tradução |
| `F7` | instalar no jogo |
| `Ctrl+Enter` | aplicar a edição e ir ao próximo |
| `Ctrl+Shift+Z` | desfazer a última edição |
| `Ctrl+F` / `Ctrl+Shift+F` | buscar nos textos / na lista de mods |
| `F9` | abrir/fechar a lista (janela estreita) |
| `Ctrl +` / `Ctrl −` / `Ctrl+0` | aumentar / diminuir / normalizar a letra |

---

## 💻 Linha de comando

```bash
kenshi-quick-translator scan                                  # lista os mods instalados
kenshi-quick-translator info "Kaizo.mod"                      # textos e idiomas detectados
kenshi-quick-translator translate "Kaizo.mod" --provider deepl --key SUA_CHAVE --workers 6 --out saida
kenshi-quick-translator translate "Misto.mod" --sources en,zh --provider deepl --key SUA_CHAVE
kenshi-quick-translator translate "Kaizo.mod" --provider simulado --install
kenshi-quick-translator po-export "Kaizo.mod" --out Kaizo.po  # edite no Poedit
kenshi-quick-translator po-import "Kaizo.mod" --po Kaizo.po
```

---

## 🧱 Dependências

| O que | Para quê | Obrigatório? |
|---|---|---|
| 🐍 **Python 3.10+** | rodar o programa | sim (não precisa se usar o `.exe`) |
| 🖼️ **Tkinter** | a janela | sim (já vem com o Python do Windows) |
| 🧩 [`kenshi-translator-toolkit`](https://github.com/AlexPrestes/kenshi-translator-toolkit) `>= 1.1.1` | **ler e escrever o formato `.mod`** do Kenshi | sim (instalado pelo `instalar.bat`) |
| 🎨 **Pillow** | ícones de mods em JPG e imagens grandes | não (opcional; `pip install pillow`) |
| 🔐 **cryptography** | login por conta de serviço do Google Cloud v3 | não (só se usar essa opção) |
| ☁️ **gcloud** | alternativa de login do Google Cloud v3 | não |
| 📦 **PyInstaller** | gerar o `.exe` | só para quem quer gerar o `.exe` |

Instalação manual:

```bash
python -m pip install .            # instala o programa e o toolkit
python -m pip install pillow       # opcional
```

> 🌐 O programa precisa de internet para traduzir (os serviços ficam na nuvem). Ler, revisar e instalar funcionam sem internet.

---

## 🔨 Gerando o `.exe`

1. Instale o Python (veja acima).
2. Dê dois cliques em **`gerar-exe.bat`**.
3. O resultado fica em `lancamento\KenshiQuickTranslator\`: o `.exe` (sem UPX, para reduzir alertas falsos de antivírus), mais `LEIA-ME`, `LICENSE` e `LICENCAS-TERCEIROS`.

> 🛡️ **Antivírus:** `.exe` feito em Python com PyInstaller às vezes é marcado por engano. Se preferir, rode pelo código-fonte.
> 🔓 O PyInstaller **não criptografa**: o `.exe` guarda o código compilado, que é mais difícil de ler que o `.py`, mas pode ser recuperado.

---

## 🧪 Testes

```bash
python -m unittest discover -s tests -v                        # suíte completa (203 testes)
KENSHI_SAMPLE_MOD="caminho/mod.mod" python -m unittest discover -s tests   # com um mod real
xvfb-run -a python tests/gui_smoke61.py                        # janela de verdade (Linux, tela virtual)
python tests/bench_large.py --texts 50000 --delay 0 --workers 6  # mod grande
```

Os testes cobrem leitura e escrita do `.mod`, marcadores, serviços (com servidores HTTP **falsos**), rodízio e quarentena, memória de tradução, projetos, idiomas da interface e a janela em tela virtual.

**Velocidade do próprio programa** (serviço simulado, 0,05 s por pedido, mod sintético de 20 000 textos):

| Partes em paralelo | 1 | 3 | 6 | 12 |
|---|---|---|---|---|
| Tempo | 38,5 s | 13,2 s | 6,8 s | 3,6 s |

> Isso mede o programa, **não** os serviços. Na prática, quem decide o tempo é o limite de cada serviço.

---

## 🗂️ Estrutura do projeto

```
kenshi-quick-translator/
├── iniciar.py · abrir.bat · instalar.bat · gerar-exe.bat
├── KenshiQuickTranslator.spec        # receita do PyInstaller
├── pyproject.toml
├── kenshi_quick_translator/
│   ├── gui.py                 # a janela (Tkinter)
│   ├── session.py             # liga janela, serviços, projeto e jogo
│   ├── core.py                # traduz, gera, confere e instala o mod
│   ├── project.py             # projeto salvo de cada mod/idioma
│   ├── fields.py              # quais campos de texto entram (lista + filtro de código)
│   ├── markers.py             # proteção dos códigos do jogo (/TEAMUP/…)
│   ├── freeproviders.py       # serviços gratuitos e o modo agregado
│   ├── providers.py           # DeepL, Google Cloud v2, LibreTranslate, simulado
│   ├── services.py            # IAs (formato OpenAI) e Google Cloud v3
│   ├── langdetect.py          # idioma de cada texto, sem modelo externo
│   ├── memory.py              # memória de tradução (SQLite)
│   ├── glossary.py            # glossário
│   ├── review.py              # duvidosos, marcadores coloridos, desfazer
│   ├── restore.py             # restaurar o original
│   ├── cleanup.py             # limpar dados do programa
│   ├── locate.py              # acha o Kenshi, o Workshop e os mods
│   ├── i18n*.py               # interface em 5 idiomas
│   ├── ui_*.py                # peças da interface (ações, estado, passo a passo, ícones)
│   └── cli.py                 # linha de comando
└── tests/                     # 203 testes + testes de janela
```

---

## 🛠️ Como foi feito

Este projeto nasceu de uma vontade simples: **traduzir mods do Kenshi sem sofrimento**.

1. 🌱 **Ponto de partida.** O programa original é o [KenshiTranslator](https://github.com/Kakrain/KenshiTranslator), de **Kakrain** (código aberto, MIT, escrito em C#). Foi ele que mostrou como era possível traduzir um mod inteiro com um clique, usando serviços gratuitos de tradução em modo agregado.
2. 🧬 **Reescrito em Python.** O Kenshi Quick Translator é uma **reescrita em Python** a partir do código aberto do Kakrain, e não uma cópia: o formato das chamadas dos serviços gratuitos, a ideia do modo agregado, a lista de campos que não se traduzem e o botão "Copiar para a pasta do jogo" seguem o original. O restante é código novo.
3. 🧩 **Formato `.mod`.** Para ler e escrever o arquivo `.mod` do Kenshi, o programa usa o [`kenshi-translator-toolkit`](https://github.com/AlexPrestes/kenshi-translator-toolkit), de AlexPrestes (MIT), que por sua vez usa o algoritmo do MOD Translation Helper, de kongyo11.
4. 🤖 **Feito com a ajuda do Claude.** Todo o código foi escrito em conversa com o **Claude** (IA da Anthropic, via Claude Code). Eu descrevia o que queria e o que dava errado, mandava capturas de tela do Windows, e o Claude escrevia, testava e corrigia, versão após versão.
5. 🔁 **Evoluiu pelo uso real.** Vários recursos nasceram de problemas que apareceram testando mods de verdade, por exemplo:
   - mods com dois idiomas misturados → tradução texto a texto, com detecção de idioma por texto;
   - marcadores quebrados pelo tradutor → proteção e conferência dos códigos;
   - serviços gratuitos bloqueando → rodízio, quarentena e limitador;
   - progresso "fantasma" entre mods de mesmo nome → projetos separados por mod;
   - erro **"Corrupt mod file"** no FCS em mods de cabeçalho estendido → correção do tamanho do cabeçalho e conferência obrigatória antes de instalar.
6. ✅ **Testes.** Cada recurso ganhou testes automáticos (203 hoje) e, para a janela, testes em tela virtual.

---

## 🙏 Créditos

- 👤 **Criador:** **Canela de Enxadeco**.
- 🤖 **Desenvolvido com a ajuda do [Claude](https://www.anthropic.com/claude)** (Anthropic).
- 🌱 **Base e inspiração:** [KenshiTranslator](https://github.com/Kakrain/KenshiTranslator), de **Kakrain** (MIT) — código aberto que serviu de base para a ideia, os serviços gratuitos e o modo agregado.
- 🧩 **Leitura e escrita do `.mod`:** [kenshi-translator-toolkit](https://github.com/AlexPrestes/kenshi-translator-toolkit), de **AlexPrestes** (MIT), que usa o algoritmo do MOD Translation Helper, de **kongyo11**.
- 🌐 **Formato das chamadas dos serviços gratuitos:** [GTranslate](https://github.com/d4n3436/GTranslate), de **d4n3436** (MIT), reescrito em Python.
- Python, Tkinter, PyInstaller e Pillow seguem as licenças próprias de cada um. Veja [`LICENCAS-TERCEIROS.txt`](LICENCAS-TERCEIROS.txt).

> Este é um projeto de fã e **não tem ligação com os criadores do Kenshi** (Lo-Fi Games). Respeite os termos de uso dos serviços de tradução e a licença dos mods que você traduz: peça permissão ao autor antes de publicar uma tradução.

---

## ⚠️ Limites conhecidos

- 🧪 O programa foi testado pelo autor no Windows com mods reais (inclusive abrindo o mod traduzido no FCS), mas **não há garantia para todos os mods**. Se achar um erro, abra uma *issue* com uma captura de tela.
- 🔑 **Serviços com chave** (DeepL, Google Cloud, IAs, LibreTranslate) foram escritos lendo a documentação oficial e testados com servidores **falsos**. Use **Testar serviço** primeiro. Nomes de modelo e endereços predefinidos são sugestões que mudam com o tempo.
- 🆓 **Serviços gratuitos** são não oficiais: podem bloquear ou mudar a qualquer hora.
- 🤖 **IA pode errar ou "inventar" texto.** O programa confere os códigos do jogo, mas **não a qualidade**: revise os diálogos importantes.
- 🌐 O detector de idioma não separa português do Brasil do de Portugal; textos curtos em alfabeto latino ("Maybe.") não têm como ser decididos com certeza (vão com o idioma automático do serviço).
- 🎯 O programa só traduz o que **o próprio mod** contém. Linhas do jogo original que o mod apenas *referencia* (aparecem em azul no FCS) não podem ser traduzidas por ele.
- 🚫 Não traduz para dois idiomas de destino ao mesmo tempo: traduza duas vezes, trocando o idioma. Cada idioma guarda o seu projeto.
- 🈯 As traduções da interface em **russo e chinês** foram feitas por IA, sem revisão de falante nativo. Correções são bem-vindas.
- ⏱️ O tempo de um mod grande depende do serviço escolhido e do limite da conta; não dá para prometer um número.

---

## 📜 Licença

Distribuído sob a licença **MIT**. Veja o arquivo [`LICENSE`](LICENSE).

<div align="center">

Feito com ☕ por **Canela de Enxadeco** · com a ajuda do **Claude** 🤖

</div>
