# STATUS — Kenshi Quick Translator (continuar em outro chat: leia só este arquivo)

Versão atual: **0.6.0** (Python 3.10+/Tkinter). Pedido original do usuário: 3 etapas, nesta ordem, respostas econômicas, interface em português do Brasil, não inventar resultados ("não testei" quando não der).

## ETAPA 1 — PRONTA (testada só com serviços falsos)
- `kenshi_quick_translator/freeproviders.py` (novo): Google, Google2, Bing, Microsoft, Yandex (portados da GTranslate, MIT) + `Aggregate`.
  - Falha (429/403/5xx/timeout/resposta ruim) → resto do lote vai ao próximo serviço; falha parcial aproveita o que já veio.
  - Serviço que falha sai da rotação: 60 s, dobra a cada falha seguida, máx. 600 s (respeita Retry-After). Sucesso zera.
  - Todos fora → espera (3–60 s) e tenta de novo, até 4 rodadas; só então `ProviderError` ("Todos os serviços falharam").
  - `RateLimiter` por serviço (rpm prudente: Google 120, Google2 90, Bing 60, Microsoft 90, Yandex 90 — valores meus, NÃO oficiais).
  - Textos acima do limite de um serviço (Bing/Microsoft 1000 caracteres) passam ao próximo sem punir o serviço.
  - Avisos em português via `on_event` (ex.: "Google bloqueou (muitos pedidos). Fica de fora por 1 min. Passei para o Bing."), copiados para `Report.messages` em `core.translate_project`.
  - `Aggregate.status()` devolve (chave, nome, segundos de quarentena) — usar na tela de serviços (etapa 3).
- `providers.py`: `ProviderError` ganhou `status`, `retry_after`, `partial`; `GoogleFree` antigo removido; `make_provider(..., free_order)`; SPECS ganhou agregado (primeiro), google2, bing, microsoft, yandex. Chave `google-free` continua existindo (agora = só Google).
- `config.py`: `provider` padrão = `agregado`; novo `free_order` (ordem do agregado, editável no config.json; GUI de ordem fica p/ etapa 3).
- `core.py`: `copy_mod_to_game()` (copia pasta do Workshop → Kenshi/mods/<nome>, só lê o Workshop); `translate_project` liga cancelamento/avisos ao agregado.
- `session.py`/`gui.py`: botão "Copiar mod para a pasta do jogo" (lista de mods, à esquerda); dica de velocidade para serviços gratuitos.
- `tests/test_aggregate.py`: 9 testes (rodízio, quarentena, falha parcial, todos falham, texto grande, assinatura Microsoft, cópia). Todos passam; test_core/test_session/test_keypool continuam passando.

## v0.3.1 — pedidos do usuário após testar a Etapa 1 (PRONTO, GUI não testada)
- Botão "⚙ Configurações" (cabeçalho) → janela com: idioma do programa (Português/English/Español), "Avisar quando trocar de serviço" (`cfg.notify_switch`; desligado = `Options.notify_switch=False`, o agregado troca em silêncio), "Copiar imagem/ícone do mod original ao instalar" (`cfg.copy_images`).
- `i18n.py`: tabela pt→en/es (`ROWS`); `apply(raiz)` troca textos de widgets, `install_hooks()` faz messagebox/filedialog/StringVar.set passarem por `tr()`. Textos com números são traduzidos por pedaços. Limites: valores de tabela/combobox (estados "Pendente", filtros "Todos", coluna "Onde") e textos de variável já exibidos ficam em português até a próxima atualização; tudo certo após reiniciar. Para traduzir algo novo, acrescente uma linha em `ROWS`.
- Instalar no jogo agora copia também a imagem/ícone do mod original (`core.copy_mod_images`, extensões em `IMAGE_EXTS`; renomeia se o nome da imagem leva o nome do mod). NÃO copia outros arquivos do original. Origem achada por nome em `scan_mods` (Workshop ou pasta do jogo). Não sei qual o nome exato que o Kenshi usa para o ícone: copio qualquer imagem da pasta.
- `tests/test_v031.py` (9 testes). Sem Tkinter no ambiente: janela de configurações e `i18n.apply` só foram checados por `py_compile`.

## v0.3.2 — modo escuro (PRONTO, janela não testada: sem Tkinter no ambiente)
- `gui.py`: `PALETTES` (light/dark), `set_palette()`, `system_theme()` (Windows via winreg), `App._style()` agora usa só a paleta, `App.apply_theme()` troca na hora (mapa cor antiga→nova + `_recolor`), `_style_tags()` para as linhas das tabelas. Config: `theme` = light | dark | auto. Escolha em ⚙ Configurações → Tema.
- Risco conhecido: o ttk "clam" pode deixar algum detalhe claro no escuro (caixas de seleção, barra de título do Windows). Ajustar `_style()` se o usuário mandar print. Contraste das cores conferido por cálculo.

## NÃO TESTADO (importante)
- Nenhum serviço gratuito foi chamado de verdade (sem internet no ambiente). Formatos conferidos só lendo o código da GTranslate.
- Ponto de risco: Bing (credenciais extraídas do HTML de /translator), Microsoft (assinatura `X-MT-Signature` com chave do app Android; formato de data `ddd, dd MMM yyyy HH:mm:ssGMT`) e Google2 (batchexecute).
- GUI sem tkinter no ambiente: só `py_compile`. Testar no Windows.
- Google: GET→POST com `dj=1`, sem o parâmetro `tk` (a GTranslate envia `tk`; o GET sem `tk` já funcionava no teste do usuário).
- Mapa de idiomas: pt-BR→"pt" (Google/Bing/Microsoft), "pt-BR" (Yandex). Conferido só pela GTranslate/memória.
- Falta o ambiente ter `kenshi-translator-toolkit` para rodar testes (usei `PYTHONPATH=/home/claude/ktk` com clone do GitHub AlexPrestes).

## ETAPA 2 — PRONTA na v0.4.0 (testada só com servidores FALSOS locais; janela NÃO testada, sem Tkinter aqui)
- `services.py` (novo): `OpenAICompat` (POST {URL base}/chat/completions, Bearer, modelo/URL/chave editáveis; prompt manda manter ZQ0ZQ, <x0/>, /CODIGOS/, {}, [], <>; resposta = array JSON; fora do formato → divide o lote; ficha/marcador mudou → pede de novo 1 vez com aviso; a conferência final é do core via `markers.py`), `GoogleCloudV3` (lotes ≤50 itens e ≤25000 caracteres; login por JSON de conta de serviço — exige `cryptography` — ou `gcloud auth print-access-token`), `PRESETS`, `build_service`, `build_aggregate`.
- `freeproviders.Aggregate` agora aceita QUALQUER `Provider` (DeepL, Google Cloud v2/v3, LibreTranslate, IAs, gratuitos). `spread=True` (config `spread`, padrão ligado): cada lote começa por um serviço livre diferente → divide os lotes entre serviços em paralelo; `parallel_hint` eleva os "workers" do core até nº de serviços (máx. 12). `max_batch` = menor entre os membros. Dentro do agregado, serviços com chave fazem 1 tentativa de rede (`http_retries`).
- `providers._http` agora preenche `status`/`retry_after`. `make_provider("agregado", services=…, use_free, spread)`.
- Config novos: `services` (lista de dicts: id, kind, name, enabled, base_url, api_key, model, rpm, project, credentials), `use_free`, `spread`. Várias chaves do mesmo serviço: separar com `;` (KeyPool).
- GUI: botão "Serviços do agregado…" (aparece com o agregado) → `ServicesDialog` (lista, formulário por tipo, modelos prontos, Salvar/Testar/Remover/▲▼, flags use_free/spread). Textos novos não estão em `i18n.ROWS` (ficam em português).
- `core.py`: aceita `None` vindo do serviço (vira vazio).
- Testes: `tests/test_services.py` (servidor HTTP falso local). Rodar: `PYTHONPATH=<clone do toolkit> python -m unittest discover -s tests`. 104 passam.
- NÃO testado: nenhuma IA/Cloud/DeepL real; `ServicesDialog`; login v3 (JWT) e `gcloud`; mapa de idiomas do v3 (pt-BR→"pt", zh→"zh-CN", não confirmado); resposta de IA com `finish_reason`/pensamento em modelos reais; Qwen: a doc tem URL com {WorkspaceId} e região (e se contradiz no host de Pequim) — o usuário tem de copiar o endereço da própria conta.
- Documentação lida em 17/10/2026: Gemini (base `https://generativelanguage.googleapis.com/v1beta/openai/`), DeepSeek (`https://api.deepseek.com`), OpenRouter (`https://openrouter.ai/api/v1`, cabeçalho opcional X-OpenRouter-Title), Groq (`https://api.groq.com/openai/v1`), DeepL (JSON ou form; host api-free/api; 128 KiB por pedido), Cloud v3 (translateText; v3 NÃO aceita chave de API). Limites gratuitos: NÃO confirmados, não afirmar.

## ETAPA 3 — PRONTA na v0.5.0 (GUI NÃO testada aqui: sem Tkinter; só py_compile + testes de lógica)
- (i) `ServicesDialog`: lista dos gratuitos (duplo clique marca/desmarca, ▲▼ reordena → `cfg.free_order` só com os marcados; nenhum marcado desliga `use_free`), serviços com chave (já da etapa 2), botão "Testar todos" (usa `Aggregate.test()`, mostra ✓/✗ por serviço), janela maior. `make_provider("agregado")` com `use_free=False` e sem serviços dá erro claro.
- (j) Avisos ao vivo: `Options.on_message` (core chama em cada troca/bloqueio) → `Session.on_message` → fila da janela → linha em negrito sob a barra de progresso. Linha "Serviços: ✓ nome · ⏸ nome (volta em X)" atualizada 1x/s via `Aggregate.status()` (só com o agregado). O resumo em "Avisos do serviço" no fim continua.
- Ainda NÃO feito: chave por serviço gratuito (eles não usam chave); i18n dos textos novos; caixas de marcar ficam com visual padrão no modo escuro.

## Decisões
- Agregado é `Provider` que contém `FreeService`s; serviços com chave (etapa 2) devem virar membros do mesmo mecanismo (generalizar `FreeService`/`Aggregate` para qualquer `Provider`).
- Tradução texto a texto nos gratuitos (como a GTranslate), espaçada por RateLimiter.


## 0.5.1
- Subtítulo do cabeçalho: "traduza mods rapidamente".
- Ícone do usuário (icone.ico/png): janela (`_definir_icone`) e .exe (`--icon`, .spec e gerar-exe.bat).
- gerar-exe.bat novo. Destino pt-BR garantido (config antiga com 'pt' vira pt-BR uma vez; `ptbr_fix`).
- Botões "Zerar tradução deste mod" (com cópia em projetos\backup, guarda 5) e "Abrir pasta dos projetos"; cópia automática antes de "Refazer automáticas".
- `providers.friendly_error`: 429/HTML viram frase curta em português. Resumo ao fim de cada tradução. Caixas de marcar no modo escuro (indicator*) — só conferido sem erro no xvfb, não visualmente no Windows.
- tests/test_v051.py. 109 testes OK (serviços falsos). NÃO testado: serviços reais, ícone no Windows/.exe.
- Pendente/ideias: filtro/ordenar lista de mods; mods com o MESMO nome de arquivo (Workshop e pasta local) compartilham o mesmo projeto salvo.

## 0.5.2
- Idioma do PROGRAMA: acrescentados Русский e 中文 (⚙ Configurações → Idioma do programa). Textos em `i18n_extra.py` (mesma ordem de `i18n.ROWS`; ao acrescentar linha em ROWS, acrescentar também em RU_ZH). Ajuda em ru/zh. Teste: tests/test_v051.py (alinhamento). NÃO visto na janela real do Windows; traduções feitas por mim (sem revisão de nativo). Telas sem entrada em ROWS (ex.: "Serviços do agregado") continuam em português, como já ocorria em en/es.

## 0.5.3
- Tradução completa da interface (en/es/ru/zh): tabelas de estados/filtros/origem, nomes de idiomas (`i18n.names`), janela "Serviços do agregado", avisos/erros dos serviços, mensagens de conferência. Textos em `i18n_more.py` (MORE: pt,en,es,ru,zh; PATTERNS: números). Janela de glossário/configurações já passavam por `i18n.apply`.
- De propósito NÃO traduzidos (o programa os usa como chave de seleção; traduzir quebraria): nomes de serviços ("DeepL (chave)", "Google (gratuito, não oficial)"…), tipos em KINDS, nomes de idiomas do seletor ("Português (Brasil) (pt-BR)"). Teste em tests/test_v051.py garante isso.
- Conferido só por script (xvfb): nenhum texto em português sobra nas janelas principal e de serviços em ru/zh/en. Traduções feitas por mim, sem revisão de nativo. Não visto no Windows.

## 0.5.4
- **Mods de mesmo nome** (Workshop e pasta do jogo): `project.resolve_project_path()` — o projeto agora guarda `mod_path` (dono). Primeiro dono usa `Nome.pt-BR.ktproj.json`; outro mod de mesmo nome usa `Nome.pt-BR~<8 hex>.ktproj.json`. Projeto antigo sem dono passa a ser do primeiro mod que o abrir. `Session.saved_progress/backup_project/reset_progress` agora recebem o CAMINHO do mod (antes, o nome). Na lista, nomes repetidos mostram `[Workshop]`/`[Pasta mods]`; o caminho completo aparece sob a lista ao passar o mouse/selecionar.
- **Lista de mods**: filtro (Todos / Sem tradução / Incompletos / Completos / Só Workshop / Só pasta do jogo) e ordem (Padrão / Nome / Menos traduzidos / Mais traduzidos / Maiores). Filtro e ordem por progresso esperam a leitura em segundo plano (mods ainda não lidos ficam de fora do filtro e vão ao fim da ordem) e a lista se refaz sozinha.
- **Luzes dos serviços** (substituem a linha de texto): verde = ativo; amarelo = fora até 2 min; vermelho = fora por mais de 2 min ou 3+ falhas seguidas. Dica ao passar o mouse mostra motivo e tempo. `Aggregate.status_detail()` (novo; `status()` continua igual). Classe `Tip` (dica de mouse) em gui.py.
- **Aviso ao terminar**: som (winsound) + piscar o botão na barra de tarefas (FlashWindowEx, só se a janela não está em foco) ao fim da tradução, da fila e quando o serviço quebra. Config `notify_done` (padrão ligado), caixa em ⚙ Configurações.
- Textos novos em i18n_more.py (en/es/ru/zh, feitos por mim).
- Testes: tests/test_v054.py (projetos de mesmo nome, status_detail). Rodados aqui SEM o toolkit e SEM Tkinter: só com módulo falso do toolkit; test_v054 + test_aggregate passam (12). Lógica de filtro/ordem da lista exercitada com Tk falso. NÃO rodei a suíte inteira (falta o toolkit) nem abri a janela (sem Tkinter): luzes, dicas, som e piscar da barra NÃO foram vistos funcionando.
- Pendente/ideias: restante da lista de ideias de interface (ver chat): barra por mod na fila, ícone do mod, diff de marcadores, desfazer, tamanho da letra, lembrar posição da janela, etc.

## 0.5.5 — aparência e conforto
- **Tamanho da letra** (⚙ Configurações → Tamanho da letra; Ctrl +/−/0): `cfg.font_scale` (85/100/115/130/150 %). `_fonts()` só cria as fontes na 1ª vez e depois muda o tamanho das MESMAS fontes nomeadas (as telas abertas acompanham); altura das linhas das tabelas = 26 × escala em `_style()`. Lógica em `ui_state.py` (sem Tkinter).
- **Janela adaptável**: abaixo de `ui_state.NARROW_WIDTH` (1240 px) a lista de mods sai do painel e vira gaveta (botão "☰ Mods" no cabeçalho ou F9; fecha ao escolher 1 mod, com Esc ou no botão). Largura mínima da janela caiu de 1100 para 900. Textos corridos de largura fixa (≥600) acompanham a largura (`_rewrap`). Barra de ações do passo 2 ficou em duas linhas ("Refazer automáticas" e "Instalar ao terminar" na 2ª).
- **Lembrar**: `win_geometry`, `win_zoomed`, `last_selection` (inclui mod aberto por "Abrir arquivo…"), `mod_filter`, `mod_sort`; salvos em `on_close` (`_save_ui_state`), restaurados na abertura (`_restore_window`, e na 1ª leitura da lista). Posição fora da tela (monitor desligado) é trazida de volta por `clamp_geometry`.
- **Atalhos** (aparecem nos botões; lista completa em "⌨ Atalhos"): Ctrl+T traduzir, Ctrl+Shift+T selecionados, Esc parar/fechar gaveta, F5 atualizar lista, F6 gerar, F7 instalar, Ctrl+Enter aplicar, Ctrl+F buscar nos textos, Ctrl+Shift+F buscar nos mods, F9 gaveta. Em Text/Entry/Combobox o Tk usa Ctrl+T/F para outras coisas; `bind_class` troca por estes.
- i18n: frases novas em `i18n_more.py` (en/es/ru/zh, minhas). Fragmentos só valem com 9+ caracteres: textos curtos com atalho precisam de linha exata (ex.: "■  Parar  (Esc)").
- Testes: tests/test_v055.py (9: passos da letra, geometria, config). Com toolkit e Tkinter FALSOS: lógica da gaveta/Esc/salvar estado e traduções dos botões conferidas por script. A suíte completa dá os mesmos 35 erros da 0.5.3 neste ambiente (o toolkit falso não tem `TypeCode`), nenhum novo.
- NÃO visto numa janela real: gaveta (place sobre o PanedWindow), reflow em 900–1240 px, troca de letra ao vivo, restauração da posição/seleção, atalhos em Text/Entry. Testar no Windows.


## 0.5.6 — todos os campos de texto (como o original) + filtro de segurança
- `fields.py` (novo): `collect_units()` = unidades do toolkit + TODOS os outros campos de texto dos registros (exceto os só-referência e chaves que começam com `_`), menos: (1) `translator_blacklist.txt` (11 campos padrão do original, criado na pasta de dados = pai de `projetos`; editável); (2) filtro automático (`technical_reason`: caminho, arquivo, `_`, camelCase, letra+número, `:=;{}[]<>|`, palavra solta minúscula; nome de campo com pedaço técnico; campo cuja maioria dos valores parece código); (3) tipos de registro sem texto conhecido só aceitam valores com 2+ palavras. `translator_liberados.txt` libera campos suspeitos (a blacklist vence).
- `Project.from_mod_file(..., rules=None)` usa `collect_units`; `project.field_report` (só memória) → `Report.field_notes` → resumo na janela (`gui.FIELD_NOTES_TITLE`, traduzido em `i18n_more.MORE`) e no CLI. Linhas do relatório (nome do campo, contagem) ficam em português em todos os idiomas.
- `core.verify_output` agora lê direto os registros do mod gerado (não depende de `collect`).
- Nomes de registros de tipos fora da lista do toolkit NÃO são traduzidos (o original traduziria); descrição do mod (header) também não.
- Testes: tests/test_v056.py (11). Suíte completa: 136 OK com o toolkit real (clone de AlexPrestes/kenshi-translator-toolkit). NÃO testado: mod real, GUI, Kenshi carregando o resultado.

## 0.5.7 — passo a passo, dicas, ícones e gráfico (itens 11, 12, 6 e 2)
- **Passo a passo** (`gui.Tour`, textos em `ui_extra.TOUR_STEPS`): abre sozinho na 1ª vez (`cfg.tour_done`; caixa "Não mostrar de novo"); botão "▶ Passo a passo" no cabeçalho reabre. 4 passos (lista de mods, Como traduzir, Revise e gere, Dicas/ajuda): realça a borda do cartão (`App.cards`), rola até ele e põe a janelinha no lado da tela que não o cobre. Em janela estreita o passo 1 aponta para "☰ Mods".
- **Dicas ao passar o mouse**: `App._attach_tips` liga `Tip` a ~30 botões/campos pelo texto original (`ui_extra.TIPS_BY_TEXT`; roda ANTES de `i18n.apply`). Para dica nova: acrescentar em TIPS_BY_TEXT e a tradução em `i18n_tour.MORE_TOUR` (teste confere os 4 idiomas).
- **Ícone do mod** na lista: `ui_extra.pick_icon_file` (imagem com o nome do mod; senão icon/preview/…; arquivo avulso só com o nome igual; ignora >4 MB), carregado 3 por vez a cada 30 ms (`_icon_tick`), tamanho acompanha a letra. Sem Pillow só PNG/GIF; com Pillow (instalar.bat/gerar-exe.bat agora instalam) também JPG. Mod sem imagem fica sem ícone. NÃO sei o nome real da imagem que o Workshop do Kenshi usa: pego qualquer imagem da pasta do mod.
- **Gráfico de velocidade** ao lado do "textos/min · faltam": `RateTracker` (ponto a cada 2 s, janela de 10 s; zera ao começar; ao trocar de mod na fila não gera ponto falso). Dica no gráfico mostra agora e pico.
- Testes: tests/test_v057.py (9) + tests/gui_smoke57.py (janela real em xvfb: tour completo, realces, ícones PNG e JPG, gráfico, tour em chinês). Suíte inteira 145 OK (repetida 12×; uma única vez deu 1 erro que não reapareceu e não pude capturar).
- NÃO visto no Windows. Ainda faltam da lista de 18: 7, 8, 9, 10 (revisão), 3 (fila com barra por mod), 13 (erros com botões).

## 0.5.8
- Ao instalar, copia TODA a pasta do mod original (.info, subpastas de modelos/texturas, imagem) para a pasta do mod de tradução; só o .mod original fica de fora, no lugar entra o traduzido. Não testado no jogo.

## 0.5.9 — nomes de idioma e mod traduzido com o MESMO nome
- **Nomes de idioma** (`langdetect.lang_name(code, ui)`, tabela `_LN` nos 5 idiomas): "Português (pt-BR)", "Portuguese (pt-BR)", "Inglês (en)"; "und" sem sigla. `pt` detectado aparece como pt-BR (o detector não separa pt-BR de pt-PT). Usado na coluna Idioma da lista de mods e da tabela, na linha de informação e nas caixas "idiomas que o mod tem". CAUSA do bug antigo: a lista guardava o texto já traduzido; agora guarda a contagem por idioma (`App.mod_counts`) e `App.relabel_languages()` refaz tudo ao trocar o idioma do programa. `session.language_label(counts, ui)`.
- **Mesmo nome**: `core.translation_filename` devolve o nome do original (o idioma não entra). `build_translation` agora faz CÓPIA COMPLETA do original (`toolkit.apply`) com a marca `[Kenshi Quick Translator: <idioma>]` na descrição; sem dependência do original (seria dependência de si mesmo; `verify_output` acusa se acontecer). Recusa gerar na mesma pasta do original.
- **Instalar**: `Kenshi/mods/<nome>/<nome>.mod`. Se já há um .mod ali que NÃO tem a marca (é o original), guarda uma vez como `<nome>.mod.original`; se tem a marca (tradução anterior, outro idioma) só substitui. Garante a linha no mods.cfg (backup antes).
- **Fonte para traduzir de novo**: `locate.scan_mods` lista o `.mod.original` no lugar do .mod traduzido; `locate.real_mod_name` tira o `.original` (nome do projeto e do arquivo de progresso ficam os mesmos).
- Textos da tela (dicas, passo a passo, confirmação de instalar, mensagens de conferência) atualizados em pt/en/es/ru/zh.
- Testes: tests/test_v059.py (12) + ajustes em test_core, test_v031, test_v056 e gui_smoke. Suíte: 158 OK (1 pulado).
- NÃO testado: janela (sem Tkinter aqui; só py_compile e checagem de nomes), Windows/.exe, o Kenshi carregando um mod traduzido com o mesmo nome do original, nem o comportamento do jogo quando o mesmo nome existe no Workshop e em Kenshi/mods (qual dos dois o jogo carrega). Traduções ru/zh dos textos novos são minhas.

## 0.5.10 — escolha: completo ou dependente do original
- `Config.translation_mode` = "completo" (padrão) | "dependente"; ⚙ Configurações → "Tipo do mod traduzido" (`gui.MODE_LABELS`/`MODE_NOTE`, textos em `i18n_more.MORE_MODE`, 5 idiomas). CLI: `translate --dependent`.
- `core.build_translation(..., mode=)`: dependente = `build_translation_mod` do toolkit (só o que mudou, declara o original como dependência), arquivo "Nome IDIOMA.mod" (`translation_filename(..., dependent=True)`). `install_translation` detecta o modo pelo nome: dependente → pasta própria, ativa depois do original no mods.cfg, sem backup nem troca do original. `verify_output` confere conforme o modo (completo: não pode depender de si; dependente: tem que depender do original).
- Testes: +6 em tests/test_v059.py. Suíte: 164 OK (1 pulado). NÃO testado: janela de configurações (sem Tkinter), Windows, jogo.

## 0.5.11 — créditos
- ⚙ Configurações, no rodapé, em letra pequena e cinza: "Inspirado no Kenshi Translator, de Kakrain. Feito por Canela de Enxadeco, com a ajuda de uma IA (Claude, da Anthropic)." (`gui.CREDITS_TEXT`, traduzido em `i18n_more.MORE_CREDITS`). Clicar no texto abre github.com/Kakrain (`CREDITS_URL`). Janela NÃO vista (sem Tkinter). Suíte: 164 OK.


## 0.6.0 — itens da lista aprovada ("faca") + empacotamento fechado
- **Restaurar o original** (`restore.py`, `Session.restore_original/has_original_backup`, botão "Restaurar o original"): copia `<nome>.mod.original` de volta sobre o `.mod` (troca atômica via `os.replace`); a tradução instalada vira `<nome>.mod.traduzido` (não é apagada); o backup é mantido. Sem backup → mensagem, nada muda.
- **Aviso do backup ao instalar**: `core.install_translation_info()` devolve `InstallInfo` (backup, `backup_created`, `replaced_translation`); `install_translation()` continua devolvendo a tupla antiga. `Session.last_install`; a janela "Instalado" mostra onde o original ficou (`ui_actions.install_notice`).
- **Revisão** (`review.py`, lógica pura): contador de duvidosos (estado Conferir + marcadores que não batem + "traduzida" igual ao original), filtro "Duvidosos", `⚠ N duvidosos` na linha de estatísticas; marcadores coloridos nos dois campos de texto (verde = bate, vermelho = falta no original/sobra na tradução); **desfazer** edição (`UndoHistory`, botão "↶ Desfazer edição" e Ctrl+Shift+Z; vale por mod aberto, 200 níveis; a memória de tradução NÃO é desfeita); **filtro por idioma de origem** (caixa aparece só com 2+ idiomas detectados).
- **Segunda passada** (`Options.only_attention`, `Session.second_pass(service)`, botão no passo 2): refaz só os "Conferir" com o serviço escolhido, sem memória de tradução; se o novo resultado também falha, mantém o texto anterior; faz backup do projeto antes.
- **Erro com botões** (`ui_actions.error_dialog/broken_dialog`): "Tentar de novo" (continua de onde parou), "Trocar de serviço…", "Fechar" — usado quando o serviço quebra durante a tradução. Outras mensagens de erro continuam caixas simples.
- **Fila**: o andamento do mod da vez aparece em % na própria lista de mods (coluna de progresso), os já feitos em 100%. NÃO é uma barra desenhada por mod.
- **Empacotamento**: `.spec` com `upx=False`; `gerar-exe.bat` usa `--noupx` e monta `lancamento\KenshiQuickTranslator\` (só .exe + LEIA-ME + LICENSE + LICENCAS-TERCEIROS). PyInstaller não criptografa: o .exe guarda bytecode, mais difícil de ler que o .py mas recuperável (igual ao original do Kakrain).
- Textos novos: `i18n_v06.py` (5 idiomas; ru/zh feitos por IA, sem nativo).
- Testes: `tests/test_v060.py` (27). Rodados SÓ com um stub do toolkit (`/tmp/stubtk`, não vai no zip) e sem Tkinter. A suíte antiga (que precisa do toolkit real) NÃO foi rodada nesta sessão: no ambiente não havia o toolkit nem internet. Rodar no PC: `python -m pip install .` e `python -m unittest discover -s tests`.
- NÃO testado: janela (nenhum botão novo foi aberto), Windows/.exe, Kenshi carregando mod traduzido, serviços reais.

## 0.6.1 — Limpar dados
- Configurações gerais > **Limpar dados…** (`cleanup.py`, `Session.clean_data`, `App.open_cleanup`): marca o que apagar, com quantidade e tamanho de cada item. Categorias: traduções salvas (projetos), backups dos projetos, memória de tradução, idiomas detectados (marcadas por padrão se houver algo), glossário e configurações/chaves (desmarcadas por padrão). Pede confirmação.
- Só apaga arquivos conhecidos da pasta de dados do programa. NÃO mexe na pasta do Kenshi (mods, mods.cfg, ".original") nem nas listas translator_blacklist/liberados. Bloqueado enquanto há tradução rodando.
- "Configurações" volta ao padrão na hora, mas alguns itens só valem ao reabrir o programa.
- Testes: tests/test_v061.py (lógica + 5 idiomas) e tests/gui_smoke61.py (janela real em tela virtual, 4 idiomas). Suíte: 196 OK. NÃO testado no Windows/.exe.

## 0.6.2 — correção: "Corrupt mod file" em mods de cabeçalho estendido
- Defeito da 0.6.0/0.6.1: em mods de cabeçalho estendido (tipo 17, ex.: Another World of RO) o modo completo acrescentava a marca "[Kenshi Quick Translator: …]" na descrição sem atualizar o `header_length`; o arquivo gerado ficava deslocado e o FCS/jogo diziam "Corrupt mod file". Corrigido em `core.set_description` (ajusta `header_length` pela diferença de bytes). Conferido com o arquivo real enviado (31225 textos): gera, lê de volta e passa na conferência.
- A conferência já via o problema ("não pôde ser lido de volta"), mas "Instalar no jogo" instalava mesmo assim. Agora, se a conferência achar qualquer problema, NÃO instala (mostra a lista).
- Mods instalados com a 0.6.0/0.6.1 nesse tipo de cabeçalho estão corrompidos: usar "Restaurar o original" e instalar de novo (o progresso da tradução é mantido).
- Testes: tests/test_v062.py (cabeçalho estendido sintético, antes falhava). Suíte: 199 OK. Não testado no jogo.

## 0.6.3
- App renamed to **Kenshi Quick Translator** (package `kenshi_quick_translator`, exe `KenshiQuickTranslator.exe`, CLI `kenshi-quick-translator`).
- Data folder `%APPDATA%\KenshiTradutor` is copied automatically to `%APPDATA%\KenshiQuickTranslator` (old folder kept, never overwritten).
- Mods translated with the old mark "[Kenshi Tradutor: ...]" are still recognized.
- READMEs in English and pt-BR, `.gitignore` added. 203 tests.
