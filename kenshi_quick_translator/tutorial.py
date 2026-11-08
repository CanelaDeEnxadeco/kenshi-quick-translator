"""Tutoriais do programa (0.7.5): básico e avançado. Sem Tkinter, para poder ser testado.

Cada passo: (alvo, título, texto), cada um com 5 idiomas (pt, en, es, ru, zh).
 - O alvo é o nome de uma parte da janela (veja `App._tut_target` em gui.py); se a parte não está visível
   (janela estreita, por exemplo), o passo é pulado.
 - O português é a "chave" de tradução: i18n.tr(texto_pt) devolve o texto no idioma do programa.
`MORE_TUTORIAL` (frases para i18n.py) sai da mesma tabela, então cada texto é escrito uma vez só.
"""
from __future__ import annotations

T5 = tuple[str, str, str, str, str]

# --------------------------------------------------------------------------- tela de boas-vindas
WELCOME: tuple[T5, ...] = (
    ("Bem-vindo ao Kenshi Quick Translator!", "Welcome to Kenshi Quick Translator!", "¡Bienvenido a Kenshi Quick Translator!",
     "Добро пожаловать в Kenshi Quick Translator!", "欢迎使用 Kenshi Quick Translator!"),
    ("Tutoriais", "Tutorials", "Tutoriales", "Обучение", "教程"),
    ("Traduza mods do Kenshi sem estragar os marcadores do jogo. Como você quer começar?",
     "Translate Kenshi mods without breaking the game's markers. How would you like to start?",
     "Traduce mods de Kenshi sin romper los marcadores del juego. ¿Cómo quieres empezar?",
     "Переводите моды Kenshi, не ломая игровые маркеры. С чего хотите начать?",
     "翻译 Kenshi 模组而不破坏游戏标记。你想怎么开始?"),
    ("Tutorial básico", "Basic tutorial", "Tutorial básico", "Базовое обучение", "基础教程"),
    ("Só o essencial: escolher o mod, traduzir, conferir e instalar. Leva cerca de 2 minutos.",
     "Just the essentials: choose the mod, translate, review and install. Takes about 2 minutes.",
     "Solo lo esencial: elegir el mod, traducir, revisar e instalar. Dura unos 2 minutos.",
     "Только главное: выбрать мод, перевести, проверить и установить. Около 2 минут.",
     "只讲要点:选择模组、翻译、检查并安装。大约 2 分钟。"),
    ("Tutorial avançado", "Advanced tutorial", "Tutorial avanzado", "Расширенное обучение", "进阶教程"),
    ("Explica cada parte da tela e cada botão, um por um, na ordem em que aparecem.",
     "Explains every part of the window and every button, one by one, in the order they appear.",
     "Explica cada parte de la ventana y cada botón, uno por uno, en el orden en que aparecen.",
     "Объясняет каждую часть окна и каждую кнопку по порядку.",
     "按出现顺序逐一讲解窗口的每个部分和每个按钮。"),
    ("Agora não, vou explorar sozinho", "Not now, I will explore on my own", "Ahora no, voy a explorar por mi cuenta",
     "Не сейчас, разберусь сам", "暂不,我自己摸索"),
    ("Não mostrar isto ao abrir o programa", "Do not show this when the program opens",
     "No mostrar esto al abrir el programa", "Не показывать при запуске программы", "启动程序时不再显示"),
    ("Você pode abrir os tutoriais quando quiser, no botão “Tutorial” no topo da janela.",
     "You can open the tutorials whenever you like, with the “Tutorial” button at the top of the window.",
     "Puedes abrir los tutoriales cuando quieras, con el botón «Tutorial» en la parte superior de la ventana.",
     "Обучение можно открыть в любой момент кнопкой «Обучение» в верхней части окна.",
     "你可以随时通过窗口顶部的“教程”按钮打开教程。"),
    ("Tutorial básico", "Basic tutorial", "Tutorial básico", "Базовое обучение", "基础教程"),
    ("Ver o tutorial avançado", "See the advanced tutorial", "Ver el tutorial avanzado", "Смотреть расширенное обучение", "查看进阶教程"),
)

# --------------------------------------------------------------------------- tutorial básico
BASIC: tuple[tuple[str, T5, T5], ...] = (
    ("mods",
     ("1. Escolha o mod", "1. Choose the mod", "1. Elige el mod", "1. Выберите мод", "1. 选择模组"),
     ("À esquerda ficam os mods que o programa achou no Kenshi e no Workshop. Clique em um para abrir. "
      "Se o seu não aparecer, use “Abrir arquivo…”.",
      "On the left are the mods the program found in Kenshi and in the Workshop. Click one to open it. "
      "If yours is not listed, use “Open file…”.",
      "A la izquierda están los mods que el programa encontró en Kenshi y en el Workshop. Haz clic en uno para abrirlo. "
      "Si el tuyo no aparece, usa «Abrir archivo…».",
      "Слева — моды, найденные программой в Kenshi и в Workshop. Нажмите на мод, чтобы открыть его. "
      "Если вашего мода нет в списке, используйте «Открыть файл…».",
      "左侧是程序在 Kenshi 和 Workshop 中找到的模组。点击一个即可打开。如果没有你的模组,请使用“打开文件…”。")),
    ("langs",
     ("2. Diga para qual idioma", "2. Say which language", "2. Indica a qué idioma", "2. Укажите язык перевода", "2. 选择目标语言"),
     ("Em “Traduzir para”, escolha o idioma que você quer. O idioma do mod costuma ser detectado sozinho, "
      "então normalmente não precisa mexer em “Idioma do mod”.",
      "Under “Translate to”, choose the language you want. The mod's language is usually detected by itself, "
      "so you normally do not need to touch “Mod language”.",
      "En «Traducir a», elige el idioma que quieras. El idioma del mod suele detectarse solo, "
      "así que normalmente no hace falta tocar «Idioma del mod».",
      "В поле «Перевести на» выберите нужный язык. Язык мода обычно определяется сам, "
      "поэтому «Язык мода» обычно трогать не нужно.",
      "在“翻译为”中选择你想要的语言。模组语言通常会自动识别,一般不需要改“模组语言”。")),
    ("go",
     ("3. Clique em Traduzir", "3. Click Translate", "3. Haz clic en Traducir", "3. Нажмите «Перевести»", "3. 点击翻译"),
     ("O serviço já vem escolhido (o agregado, que é grátis e não pede chave). Clique em “Traduzir este mod”. "
      "Dá para fechar o programa no meio: o progresso fica salvo e você continua depois.",
      "The service is already chosen (the aggregate, which is free and needs no key). Click “Translate this mod”. "
      "You can close the program halfway: progress is saved and you continue later.",
      "El servicio ya viene elegido (el agregado, que es gratuito y no pide clave). Haz clic en «Traducir este mod». "
      "Puedes cerrar el programa a la mitad: el progreso queda guardado y continúas después.",
      "Сервис уже выбран (агрегат: он бесплатный и не требует ключа). Нажмите «Перевести этот мод». "
      "Программу можно закрыть посреди работы: прогресс сохраняется, и вы продолжите позже.",
      "服务已选好(聚合服务,免费且无需密钥)。点击“翻译此模组”。中途可以关闭程序:进度会保存,之后可继续。")),
    ("table",
     ("4. Confira o resultado", "4. Check the result", "4. Revisa el resultado", "4. Проверьте результат", "4. 检查结果"),
     ("A tabela mostra o original e a tradução. As linhas amarelas (“Conferir”) merecem um olhar: clique numa, "
      "corrija na caixa de baixo e aperte Ctrl+Enter para ir ao próximo.",
      "The table shows the original and the translation. The yellow lines (“Review”) deserve a look: click one, "
      "fix it in the box below and press Ctrl+Enter to go to the next.",
      "La tabla muestra el original y la traducción. Las líneas amarillas («Revisar») merecen una mirada: haz clic en una, "
      "corrígela en el cuadro de abajo y pulsa Ctrl+Enter para ir a la siguiente.",
      "В таблице — оригинал и перевод. Жёлтые строки («Проверить») стоит просмотреть: нажмите на строку, "
      "исправьте текст в поле ниже и нажмите Ctrl+Enter, чтобы перейти к следующей.",
      "表格显示原文和译文。黄色行(“待检查”)值得看一眼:点击一行,在下方框中修改,然后按 Ctrl+Enter 跳到下一行。")),
    ("build",
     ("5. Gere ou instale o mod", "5. Build or install the mod", "5. Genera o instala el mod", "5. Создайте или установите мод",
      "5. 生成或安装模组"),
     ("“Gerar mod de tradução” cria o mod novo sem mexer no original. “Instalar no jogo” coloca o mod traduzido no Kenshi "
      "e guarda o original como backup (dá para voltar com “Restaurar o original”).",
      "“Build translation mod” creates the new mod without touching the original. “Install in game” puts the translated mod "
      "in Kenshi and keeps the original as a backup (you can go back with “Restore the original”).",
      "«Generar mod de traducción» crea el mod nuevo sin tocar el original. «Instalar en el juego» pone el mod traducido en Kenshi "
      "y guarda el original como copia de seguridad (puedes volver con «Restaurar el original»).",
      "«Создать мод перевода» делает новый мод, не трогая оригинал. «Установить в игру» помещает переведённый мод в Kenshi "
      "и сохраняет оригинал как резервную копию (вернуться можно кнопкой «Восстановить оригинал»).",
      "“生成翻译模组”会创建新模组,不改动原模组。“安装到游戏”会把翻译后的模组放进 Kenshi,并把原模组备份"
      "(可用“还原原版”恢复)。")),
    ("tutorial",
     ("Quer saber mais?", "Want to know more?", "¿Quieres saber más?", "Хотите узнать больше?", "想了解更多?"),
     ("Passe o mouse sobre qualquer botão para ver o que ele faz. Para uma explicação de cada parte da tela, "
      "abra o “Tutorial avançado” neste botão “Tutorial”.",
      "Hover over any button to see what it does. For an explanation of every part of the window, "
      "open the “Advanced tutorial” with this “Tutorial” button.",
      "Pasa el ratón sobre cualquier botón para ver qué hace. Para una explicación de cada parte de la ventana, "
      "abre el «Tutorial avanzado» con este botón «Tutorial».",
      "Наведите мышь на любую кнопку, чтобы увидеть, что она делает. Подробное объяснение каждой части окна — "
      "в «Расширенном обучении», которое открывается этой кнопкой «Обучение».",
      "把鼠标移到任意按钮上即可查看其作用。若想了解窗口每个部分,请用这个“教程”按钮打开“进阶教程”。")),
)

# --------------------------------------------------------------------------- tutorial avançado
ADVANCED: tuple[tuple[str, T5, T5], ...] = (
    ("mods",
     ("A. Lista de mods", "A. Mod list", "A. Lista de mods", "A. Список модов", "A. 模组列表"),
     ("• Buscar: filtra pelo nome.\n• Mostrar: só os sem tradução, incompletos, completos, do Workshop ou da pasta do jogo.\n"
      "• Ordem: por nome, tamanho ou quanto já foi traduzido.\n• Colunas: idioma detectado, “Feito” (% traduzido) e onde o mod está. "
      "Verde = pronto, amarelo = parcial.\n• Ctrl+clique escolhe vários mods; passar o mouse mostra o caminho do arquivo.",
      "• Search: filters by name.\n• Show: only untranslated, incomplete, complete, Workshop or game-folder mods.\n"
      "• Order: by name, size or how much is already translated.\n• Columns: detected language, “Done” (% translated) and where the mod is. "
      "Green = finished, yellow = partial.\n• Ctrl+click selects several mods; hovering shows the file path.",
      "• Buscar: filtra por nombre.\n• Mostrar: solo los sin traducir, incompletos, completos, del Workshop o de la carpeta del juego.\n"
      "• Orden: por nombre, tamaño o cuánto ya está traducido.\n• Columnas: idioma detectado, «Hecho» (% traducido) y dónde está el mod. "
      "Verde = terminado, amarillo = parcial.\n• Ctrl+clic elige varios mods; al pasar el ratón se ve la ruta del archivo.",
      "• Поиск: фильтр по названию.\n• Показать: только без перевода, неполные, готовые, из Workshop или из папки игры.\n"
      "• Порядок: по имени, размеру или степени готовности перевода.\n• Столбцы: определённый язык, «Готово» (% переведено) и расположение мода. "
      "Зелёный — готово, жёлтый — частично.\n• Ctrl+клик выбирает несколько модов; при наведении показывается путь к файлу.",
      "• 搜索:按名称筛选。\n• 显示:仅未翻译、未完成、已完成、Workshop 或游戏文件夹中的模组。\n"
      "• 排序:按名称、大小或已翻译程度。\n• 列:识别出的语言、“完成”(已翻译百分比)和模组所在位置。"
      "绿色 = 已完成,黄色 = 部分完成。\n• Ctrl+点击可选多个模组;鼠标悬停显示文件路径。")),
    ("mod_buttons",
     ("B. Botões da lista", "B. List buttons", "B. Botones de la lista", "B. Кнопки списка", "B. 列表按钮"),
     ("• Atualizar (F5): lê as pastas de novo.\n• Abrir arquivo…: abre um .mod que não está na lista.\n"
      "• Pasta do Kenshi…: indique onde o jogo está, se o programa não achou.\n• Copiar mod para a pasta do jogo: leva um mod do Workshop para a pasta mods.\n"
      "• Mais ações: Abrir pasta do mod, Abrir pasta dos projetos e Zerar tradução deste mod (apaga o progresso; fica uma cópia de segurança).",
      "• Refresh (F5): reads the folders again.\n• Open file…: opens a .mod that is not in the list.\n"
      "• Kenshi folder…: tell the program where the game is, if it did not find it.\n• Copy mod to the game folder: moves a Workshop mod to the mods folder.\n"
      "• More actions: Open mod folder, Open projects folder and Reset this mod's translation (erases the progress; a safety copy is kept).",
      "• Actualizar (F5): lee las carpetas de nuevo.\n• Abrir archivo…: abre un .mod que no está en la lista.\n"
      "• Carpeta de Kenshi…: indica dónde está el juego, si el programa no lo encontró.\n• Copiar mod a la carpeta del juego: lleva un mod del Workshop a la carpeta mods.\n"
      "• Más acciones: Abrir carpeta del mod, Abrir carpeta de proyectos y Reiniciar traducción de este mod (borra el progreso; queda una copia de seguridad).",
      "• Обновить (F5): заново читает папки.\n• Открыть файл…: открывает .mod, которого нет в списке.\n"
      "• Папка Kenshi…: укажите, где находится игра, если программа её не нашла.\n• Скопировать мод в папку игры: переносит мод из Workshop в папку mods.\n"
      "• Другие действия: Открыть папку мода, Открыть папку проектов и Сбросить перевод этого мода (стирает прогресс; остаётся резервная копия).",
      "• 刷新(F5):重新读取文件夹。\n• 打开文件…:打开不在列表中的 .mod。\n"
      "• Kenshi 文件夹…:程序没找到游戏时,在这里指定位置。\n• 复制模组到游戏文件夹:把 Workshop 的模组复制到 mods 文件夹。\n"
      "• 更多操作:打开模组文件夹、打开项目文件夹、重置此模组的翻译(清除进度,会保留一份备份)。")),
    ("one",
     ("C. Mod escolhido", "C. Selected mod", "C. Mod elegido", "C. Выбранный мод", "C. 已选模组"),
     ("Mostra o nome do mod aberto, quantos textos há para traduzir e o idioma detectado (avisa se o mod mistura idiomas). "
      "Cada mod tem o seu próprio projeto salvo, por idioma de destino.",
      "Shows the name of the open mod, how many texts there are to translate and the detected language (it warns if the mod mixes languages). "
      "Each mod has its own saved project, per target language.",
      "Muestra el nombre del mod abierto, cuántos textos hay por traducir y el idioma detectado (avisa si el mod mezcla idiomas). "
      "Cada mod tiene su propio proyecto guardado, por idioma de destino.",
      "Показывает название открытого мода, сколько текстов нужно перевести и определённый язык (предупредит, если в моде смешаны языки). "
      "У каждого мода свой сохранённый проект для каждого языка перевода.",
      "显示当前模组的名称、待翻译的文本数量和识别出的语言(若模组混用多种语言会提醒)。每个模组按目标语言各有一个独立保存的项目。")),
    ("langs",
     ("D. Idiomas e glossário", "D. Languages and glossary", "D. Idiomas y glosario", "D. Языки и глоссарий", "D. 语言与术语表"),
     ("• Idioma do mod: “Detectar automaticamente” costuma acertar.\n• Traduzir para: cada idioma de destino tem o seu projeto e o seu glossário.\n"
      "• Glossário: mostra qual está ativo e quantos termos tem. Ao trocar o idioma de destino, o programa pergunta se cria um com os nomes "
      "oficiais do Kenshi, se você escolhe presets ou se traduz sem glossário.",
      "• Mod language: “Detect automatically” is usually right.\n• Translate to: each target language has its own project and its own glossary.\n"
      "• Glossary: shows which one is active and how many terms it has. When you change the target language, the program asks whether to create one "
      "with Kenshi's official names, choose presets or translate without a glossary.",
      "• Idioma del mod: «Detectar automáticamente» suele acertar.\n• Traducir a: cada idioma de destino tiene su proyecto y su glosario.\n"
      "• Glosario: muestra cuál está activo y cuántos términos tiene. Al cambiar el idioma de destino, el programa pregunta si crea uno con los nombres "
      "oficiales de Kenshi, si eliges presets o si traduces sin glosario.",
      "• Язык мода: «Определять автоматически» обычно угадывает верно.\n• Перевести на: у каждого языка свой проект и свой глоссарий.\n"
      "• Глоссарий: показывает, какой активен и сколько в нём терминов. При смене языка программа спрашивает: создать глоссарий с официальными "
      "названиями Kenshi, выбрать наборы или переводить без глоссария.",
      "• 模组语言:“自动检测”通常是准确的。\n• 翻译为:每种目标语言有各自的项目和术语表。\n"
      "• 术语表:显示当前启用的术语表及其词条数。更改目标语言时,程序会询问:用 Kenshi 官方名称创建、选择预设,还是不使用术语表翻译。")),
    ("service",
     ("E. Serviço de tradução", "E. Translation service", "E. Servicio de traducción", "E. Сервис перевода", "E. 翻译服务"),
     ("• Serviço: o agregado já vem escolhido; junta vários serviços grátis e troca sozinho quando um bloqueia.\n"
      "• Chave: só para serviços que pedem (DeepL, Google Cloud, IAs). Mais de uma? Separe com ; e o trabalho é dividido.\n"
      "• Testar serviço: manda uma frase de teste.\n• Serviços do agregado…: escolhe e ordena os serviços (IAs, DeepL, Google Cloud) que trabalham juntos.",
      "• Service: the aggregate is already chosen; it combines several free services and switches by itself when one blocks.\n"
      "• Key: only for services that ask for one (DeepL, Google Cloud, AIs). More than one? Separate with ; and the work is split.\n"
      "• Test service: sends a test sentence.\n• Aggregate services…: choose and order the services (AIs, DeepL, Google Cloud) that work together.",
      "• Servicio: el agregado ya viene elegido; junta varios servicios gratuitos y cambia solo cuando uno se bloquea.\n"
      "• Clave: solo para servicios que la piden (DeepL, Google Cloud, IAs). ¿Más de una? Sepáralas con ; y el trabajo se reparte.\n"
      "• Probar servicio: envía una frase de prueba.\n• Servicios del agregado…: elige y ordena los servicios (IAs, DeepL, Google Cloud) que trabajan juntos.",
      "• Сервис: агрегат уже выбран; он объединяет несколько бесплатных сервисов и сам переключается, когда один блокирует.\n"
      "• Ключ: только для сервисов, которые его требуют (DeepL, Google Cloud, ИИ). Несколько? Разделите знаком ;, и работа распределится.\n"
      "• Проверить сервис: отправляет тестовую фразу.\n• Сервисы агрегата…: выбор и порядок сервисов (ИИ, DeepL, Google Cloud), работающих вместе.",
      "• 服务:默认已选“聚合”;它整合多个免费服务,某个被封锁时自动切换。\n"
      "• 密钥:仅需要密钥的服务才用(DeepL、Google Cloud、AI)。有多个?用 ; 分隔,工作会平均分配。\n"
      "• 测试服务:发送一句测试文本。\n• 聚合服务…:选择并排序一起工作的服务(AI、DeepL、Google Cloud)。")),
    ("speed",
     ("F. Velocidade", "F. Speed", "F. Velocidad", "F. Скорость", "F. 速度"),
     ("Quantas partes vão ao serviço ao mesmo tempo. Mais partes = mais rápido, até o limite do serviço. "
      "Se o serviço reclamar, o programa diminui sozinho; não precisa se preocupar em acertar o número.",
      "How many parts go to the service at the same time. More parts = faster, up to the service's limit. "
      "If the service complains, the program lowers it by itself, so you do not need to get the number exactly right.",
      "Cuántas partes van al servicio al mismo tiempo. Más partes = más rápido, hasta el límite del servicio. "
      "Si el servicio se queja, el programa la baja solo; no hace falta acertar el número.",
      "Сколько частей отправляется сервису одновременно. Больше частей — быстрее, до предела сервиса. "
      "Если сервис жалуется, программа сама снижает значение, так что подбирать число точно не нужно.",
      "同时发送给服务的部分数量。数量越多越快,但受服务限制。若服务报错,程序会自动调低,所以无需精确设置。")),
    ("actions",
     ("G. Traduzir e parar", "G. Translate and stop", "G. Traducir y detener", "G. Перевод и остановка", "G. 翻译与停止"),
     ("• Traduzir este mod (Ctrl+T): traduz o que falta no mod aberto.\n• Traduzir selecionados (Ctrl+Shift+T): traduz em fila todos os mods "
      "escolhidos na lista.\n• Parar (Esc): interrompe; o que já foi traduzido fica salvo.",
      "• Translate this mod (Ctrl+T): translates what is missing in the open mod.\n• Translate selected (Ctrl+Shift+T): translates all the mods "
      "chosen in the list, in a queue.\n• Stop (Esc): interrupts; what is already translated stays saved.",
      "• Traducir este mod (Ctrl+T): traduce lo que falta en el mod abierto.\n• Traducir seleccionados (Ctrl+Shift+T): traduce en cola todos los mods "
      "elegidos en la lista.\n• Detener (Esc): interrumpe; lo ya traducido queda guardado.",
      "• Перевести этот мод (Ctrl+T): переводит недостающее в открытом моде.\n• Перевести выбранные (Ctrl+Shift+T): по очереди переводит все "
      "выбранные в списке моды.\n• Стоп (Esc): прерывает; уже переведённое сохраняется.",
      "• 翻译此模组(Ctrl+T):翻译当前模组中尚未翻译的部分。\n• 翻译所选模组(Ctrl+Shift+T):按队列翻译列表中选中的所有模组。\n"
      "• 停止(Esc):中断;已翻译的内容会保留。")),
    ("actions2",
     ("H. Refazer e segunda passada", "H. Redo and second pass", "H. Rehacer y segunda pasada", "H. Переделать и второй проход",
      "H. 重做与二次翻译"),
     ("• Refazer automáticas: traduz de novo só o que o programa fez sozinho; o que você revisou não muda.\n"
      "• Segunda passada nos “Conferir”: traduz de novo só as linhas marcadas, com o serviço que você escolher.\n"
      "• Instalar no jogo ao terminar (fila): na tradução em fila, instala cada mod assim que ficar pronto.",
      "• Redo automatic ones: translates again only what the program did by itself; what you reviewed does not change.\n"
      "• Second pass on “Review” lines: translates again only the marked lines, with the service you choose.\n"
      "• Install in the game when done (queue): in a queued translation, installs each mod as soon as it is ready.",
      "• Rehacer automáticas: vuelve a traducir solo lo que el programa hizo solo; lo que revisaste no cambia.\n"
      "• Segunda pasada en los «Revisar»: vuelve a traducir solo las líneas marcadas, con el servicio que elijas.\n"
      "• Instalar en el juego al terminar (cola): en la traducción en cola, instala cada mod en cuanto esté listo.",
      "• Переделать автоматические: заново переводит только то, что программа сделала сама; проверенное вами не меняется.\n"
      "• Второй проход по строкам «Проверить»: заново переводит только помеченные строки выбранным сервисом.\n"
      "• Установить в игру по окончании (очередь): при переводе в очереди ставит каждый мод сразу, как он готов.",
      "• 重做自动翻译:只重新翻译程序自动完成的部分,你已检查的内容不变。\n"
      "• 对“待检查”再翻译一遍:只用你选择的服务重新翻译被标记的行。\n"
      "• 完成后安装到游戏(队列):按队列翻译时,每个模组一完成就立即安装。")),
    ("progress",
     ("I. Progresso", "I. Progress", "I. Progreso", "I. Ход работы", "I. 进度"),
     ("A barra mostra o andamento, e ao lado ficam o tempo que falta e um pequeno gráfico da velocidade (textos por minuto). "
      "As luzinhas mostram cada serviço do agregado: verde funcionando, amarelo esperando, vermelho com problema.",
      "The bar shows the progress, and next to it are the time left and a small speed chart (texts per minute). "
      "The little lights show each aggregate service: green working, yellow waiting, red with a problem.",
      "La barra muestra el avance, y al lado están el tiempo restante y un pequeño gráfico de velocidad (textos por minuto). "
      "Las lucecitas muestran cada servicio del agregado: verde funcionando, amarillo esperando, rojo con problema.",
      "Полоса показывает ход работы, рядом — оставшееся время и небольшой график скорости (текстов в минуту). "
      "Огоньки показывают каждый сервис агрегата: зелёный — работает, жёлтый — ждёт, красный — проблема.",
      "进度条显示进度,旁边是剩余时间和一个小型速度图(每分钟文本数)。小灯显示聚合中的每个服务:绿色 = 正常,黄色 = 等待,红色 = 有问题。")),
    ("filters",
     ("J. Filtrar a tabela", "J. Filter the table", "J. Filtrar la tabla", "J. Фильтр таблицы", "J. 筛选表格"),
     ("• Mostrar: todos, pendentes, para conferir, duvidosos, automáticas, revisadas ou ignoradas.\n"
      "• Idioma (aparece em mods com mais de um idioma): mostra só os textos de um idioma.\n• Buscar (Ctrl+F): procura no texto original ou na tradução.",
      "• Show: all, pending, to review, doubtful, automatic, reviewed or ignored.\n"
      "• Language (appears in mods with more than one language): shows only the texts of one language.\n• Search (Ctrl+F): looks in the original text or the translation.",
      "• Mostrar: todos, pendientes, para revisar, dudosos, automáticas, revisadas o ignoradas.\n"
      "• Idioma (aparece en mods con más de un idioma): muestra solo los textos de un idioma.\n• Buscar (Ctrl+F): busca en el texto original o en la traducción.",
      "• Показать: все, ожидающие, на проверку, сомнительные, автоматические, проверенные или пропущенные.\n"
      "• Язык (появляется в модах с несколькими языками): показывает тексты только одного языка.\n• Поиск (Ctrl+F): ищет в оригинале или в переводе.",
      "• 显示:全部、待处理、待检查、存疑、自动、已检查或已忽略。\n"
      "• 语言(含多种语言的模组才会出现):只显示某一种语言的文本。\n• 搜索(Ctrl+F):在原文或译文中查找。")),
    ("table",
     ("K. A tabela de textos", "K. The text table", "K. La tabla de textos", "K. Таблица текстов", "K. 文本表格"),
     ("Cada linha é um texto do mod. Estados: Pendente (ainda não traduzido), Automática (traduzido pelo programa), Conferir "
      "(o programa desconfiou: marcador do jogo suspeito, texto igual ao original etc.), Revisada (você aprovou) e Ignorada. "
      "Clique numa linha para editar embaixo.",
      "Each row is one text in the mod. States: Pending (not translated yet), Automatic (translated by the program), Review "
      "(the program is unsure: suspicious game marker, text equal to the original, etc.), Reviewed (you approved it) and Ignored. "
      "Click a row to edit it below.",
      "Cada fila es un texto del mod. Estados: Pendiente (aún sin traducir), Automática (traducido por el programa), Revisar "
      "(el programa duda: marcador del juego sospechoso, texto igual al original, etc.), Revisada (la aprobaste) e Ignorada. "
      "Haz clic en una fila para editarla abajo.",
      "Каждая строка — один текст мода. Состояния: Ожидает (ещё не переведён), Авто (переведён программой), Проверить "
      "(программа сомневается: подозрительный игровой маркер, текст совпадает с оригиналом и т. п.), Проверено (вы подтвердили) и Пропущено. "
      "Нажмите на строку, чтобы править её внизу.",
      "每一行是模组中的一个文本。状态:待处理(尚未翻译)、自动(由程序翻译)、待检查(程序存疑:游戏标记可疑、译文与原文相同等)、"
      "已检查(你已确认)和已忽略。点击一行即可在下方编辑。")),
    ("editor",
     ("L. Editar uma tradução", "L. Edit a translation", "L. Editar una traducción", "L. Правка перевода", "L. 编辑译文"),
     ("À esquerda fica o original; à direita, a tradução, que você pode corrigir. O programa confere os marcadores do jogo (partes como "
      "<nome> ou $var que não podem mudar) e avisa logo embaixo se algo ficou errado; ele não deixa gravar um marcador quebrado.",
      "On the left is the original; on the right, the translation, which you can fix. The program checks the game's markers (parts like "
      "<name> or $var that must not change) and warns right below if something is wrong; it does not let you save a broken marker.",
      "A la izquierda está el original; a la derecha, la traducción, que puedes corregir. El programa comprueba los marcadores del juego (partes como "
      "<nombre> o $var que no pueden cambiar) y avisa justo debajo si algo quedó mal; no deja guardar un marcador roto.",
      "Слева — оригинал, справа — перевод, который можно исправить. Программа проверяет игровые маркеры (части вроде "
      "<имя> или $var, которые нельзя менять) и сразу ниже предупреждает, если что-то не так; повреждённый маркер сохранить нельзя.",
      "左边是原文,右边是译文,可以修改。程序会检查游戏标记(如 <名称> 或 $var 这类不能改动的部分),有问题时会在下方提示;损坏的标记无法保存。")),
    ("editbtns",
     ("M. Aplicar, copiar e desfazer", "M. Apply, copy and undo", "M. Aplicar, copiar y deshacer", "M. Применить, копировать, отменить",
      "M. 应用、复制与撤销"),
     ("• Aplicar e próximo (Ctrl+Enter): grava a sua edição como “Revisada” e vai ao próximo texto.\n"
      "• Copiar original: copia o original para a caixa (bom para nomes que não devem mudar).\n• Desfazer edição: volta a última edição aplicada.",
      "• Apply and next (Ctrl+Enter): saves your edit as “Reviewed” and goes to the next text.\n"
      "• Copy original: copies the original into the box (good for names that must not change).\n• Undo edit: goes back on the last applied edit.",
      "• Aplicar y siguiente (Ctrl+Enter): guarda tu edición como «Revisada» y pasa al siguiente texto.\n"
      "• Copiar original: copia el original al cuadro (bueno para nombres que no deben cambiar).\n• Deshacer edición: revierte la última edición aplicada.",
      "• Применить и далее (Ctrl+Enter): сохраняет правку как «Проверено» и переходит к следующему тексту.\n"
      "• Копировать оригинал: копирует оригинал в поле (удобно для имён, которые менять нельзя).\n• Отменить правку: откатывает последнюю применённую правку.",
      "• 应用并转到下一个(Ctrl+Enter):将你的修改保存为“已检查”并跳到下一个文本。\n"
      "• 复制原文:把原文复制到框中(适合不应改动的名称)。\n• 撤销编辑:撤销最近一次应用的修改。")),
    ("build",
     ("N. Gerar, instalar e restaurar", "N. Build, install and restore", "N. Generar, instalar y restaurar", "N. Создать, установить, восстановить",
      "N. 生成、安装与还原"),
     ("• Gerar mod de tradução (F6): cria o mod traduzido, uma cópia completa com o mesmo nome. Não altera o original.\n"
      "• Instalar no jogo (F7): põe o traduzido no lugar do original no Kenshi, guarda o original como backup e confere o mods.cfg.\n"
      "• Restaurar o original: desfaz a instalação com a cópia guardada.",
      "• Build translation mod (F6): creates the translated mod, a full copy with the same name. It does not change the original.\n"
      "• Install in game (F7): puts the translated one in the original's place in Kenshi, keeps the original as a backup and checks mods.cfg.\n"
      "• Restore the original: undoes the installation with the saved copy.",
      "• Generar mod de traducción (F6): crea el mod traducido, una copia completa con el mismo nombre. No modifica el original.\n"
      "• Instalar en el juego (F7): pone el traducido en lugar del original en Kenshi, guarda el original como copia de seguridad y revisa mods.cfg.\n"
      "• Restaurar el original: deshace la instalación con la copia guardada.",
      "• Создать мод перевода (F6): создаёт переведённый мод — полную копию с тем же именем. Оригинал не меняется.\n"
      "• Установить в игру (F7): ставит переведённый мод на место оригинала в Kenshi, сохраняет оригинал как резервную копию и проверяет mods.cfg.\n"
      "• Восстановить оригинал: отменяет установку по сохранённой копии.",
      "• 生成翻译模组(F6):创建翻译后的模组(同名完整副本),不改动原模组。\n"
      "• 安装到游戏(F7):在 Kenshi 中用翻译版替换原模组,备份原模组并检查 mods.cfg。\n"
      "• 还原原版:用保存的副本撤销安装。")),
    ("tools",
     ("O. Glossário, Ferramentas e arquivos PO", "O. Glossary, Tools and PO files", "O. Glosario, Herramientas y archivos PO",
      "O. Глоссарий, инструменты и файлы PO", "O. 术语表、工具与 PO 文件"),
     ("• Glossário…: termos que devem sair sempre iguais ou nunca ser traduzidos; tem presets com os nomes oficiais.\n"
      "• Ferramentas…: sugerir presets, nomes novos, conferir caracteres, o que mudou, consistência, memória de tradução e relatório de erro.\n"
      "• Modo simples: janela só com o essencial.\n• Exportar/Importar PO: edita os textos em outro programa (ex.: Poedit).",
      "• Glossary…: terms that must always come out the same or never be translated; it has presets with the official names.\n"
      "• Tools…: suggest presets, new names, check characters, what changed, consistency, translation memory and error report.\n"
      "• Simple mode: a window with only the essentials.\n• Export/Import PO: edit the texts in another program (e.g. Poedit).",
      "• Glosario…: términos que deben salir siempre igual o no traducirse nunca; tiene presets con los nombres oficiales.\n"
      "• Herramientas…: sugerir presets, nombres nuevos, revisar caracteres, qué cambió, coherencia, memoria de traducción e informe de error.\n"
      "• Modo simple: ventana solo con lo esencial.\n• Exportar/Importar PO: edita los textos en otro programa (ej.: Poedit).",
      "• Глоссарий…: термины, которые должны всегда переводиться одинаково или не переводиться; есть наборы с официальными названиями.\n"
      "• Инструменты…: предложить наборы, новые имена, проверка символов, что изменилось, согласованность, память переводов и отчёт об ошибке.\n"
      "• Простой режим: окно только с самым нужным.\n• Экспорт/Импорт PO: правка текстов в другой программе (напр. Poedit).",
      "• 术语表…:必须始终一致或从不翻译的词条;带有官方名称预设。\n"
      "• 工具…:推荐预设、新名称、检查字符、有何变化、一致性、翻译记忆库和错误报告。\n"
      "• 简易模式:只含基本功能的窗口。\n• 导出/导入 PO:在其他程序中编辑文本(如 Poedit)。")),
    ("settings",
     ("P. Configurações e atalhos", "P. Settings and shortcuts", "P. Configuración y atajos", "P. Настройки и горячие клавиши", "P. 设置与快捷键"),
     ("• Configurações: idioma do programa, tema, tamanho da letra e opções de instalação.\n"
      "• Atalhos: lista das teclas rápidas (F5 atualizar, F6 gerar, F7 instalar, Ctrl+T traduzir, Ctrl+ e Ctrl− mudam a letra).\n"
      "• Se algo der errado, o programa guarda um erros.log; em Ferramentas há “Copiar relatório de erro”.",
      "• Settings: program language, theme, text size and installation options.\n"
      "• Shortcuts: list of quick keys (F5 refresh, F6 build, F7 install, Ctrl+T translate, Ctrl+ and Ctrl− change the text size).\n"
      "• If something goes wrong, the program keeps an erros.log; in Tools there is “Copy error report”.",
      "• Configuración: idioma del programa, tema, tamaño de letra y opciones de instalación.\n"
      "• Atajos: lista de teclas rápidas (F5 actualizar, F6 generar, F7 instalar, Ctrl+T traducir, Ctrl+ y Ctrl− cambian la letra).\n"
      "• Si algo sale mal, el programa guarda un erros.log; en Herramientas está «Copiar informe de error».",
      "• Настройки: язык программы, тема, размер шрифта и параметры установки.\n"
      "• Горячие клавиши: список (F5 обновить, F6 создать, F7 установить, Ctrl+T перевести, Ctrl+ и Ctrl− меняют размер шрифта).\n"
      "• Если что-то пойдёт не так, программа ведёт файл erros.log; в «Инструментах» есть «Копировать отчёт об ошибке».",
      "• 设置:程序语言、主题、字体大小和安装选项。\n"
      "• 快捷键:快捷键列表(F5 刷新、F6 生成、F7 安装、Ctrl+T 翻译、Ctrl+ 与 Ctrl− 调整字体)。\n"
      "• 若出现问题,程序会保存 erros.log;在“工具”中有“复制错误报告”。")),
    ("tutorial",
     ("Pronto!", "Done!", "¡Listo!", "Готово!", "完成!"),
     ("Agora você conhece a tela inteira. Este tutorial (básico ou avançado) pode ser aberto de novo quando quiser, no botão “Tutorial”.",
      "Now you know the whole window. This tutorial (basic or advanced) can be opened again whenever you like, with the “Tutorial” button.",
      "Ahora conoces toda la ventana. Este tutorial (básico o avanzado) se puede abrir de nuevo cuando quieras, con el botón «Tutorial».",
      "Теперь вы знаете всё окно. Это обучение (базовое или расширенное) можно открыть снова в любой момент кнопкой «Обучение».",
      "现在你已了解整个窗口。随时可以通过“教程”按钮再次打开本教程(基础或进阶)。")),
)

# Nome do botão do topo (um só texto, em 5 idiomas)
BUTTON: T5 = ("▶  Tutorial", "▶  Tutorial", "▶  Tutorial", "▶  Обучение", "▶  教程")
BUTTON_TIP: T5 = (
    "Abre o tutorial básico (o essencial) ou o avançado (explica cada parte da tela).",
    "Opens the basic tutorial (the essentials) or the advanced one (explains every part of the window).",
    "Abre el tutorial básico (lo esencial) o el avanzado (explica cada parte de la ventana).",
    "Открывает базовое обучение (самое главное) или расширенное (объясняет каждую часть окна).",
    "打开基础教程(要点)或进阶教程(讲解窗口每个部分)。",
)


def basic_steps() -> list[tuple[str, str, str]]:
    return [(k, t[0], x[0]) for k, t, x in BASIC]


def advanced_steps() -> list[tuple[str, str, str]]:
    return [(k, t[0], x[0]) for k, t, x in ADVANCED]


def steps_for(kind: str) -> list[tuple[str, str, str]]:
    return advanced_steps() if kind == "advanced" else basic_steps()


def all_rows() -> list[T5]:
    """Todas as frases (pt, en, es, ru, zh) para o i18n."""
    rows: list[T5] = list(WELCOME)
    for _k, title, text in (*BASIC, *ADVANCED):
        rows.append(title)
        rows.append(text)
    rows.append(BUTTON)
    rows.append(BUTTON_TIP)
    out, seen = [], set()
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            out.append(r)
    return out


MORE_TUTORIAL: list[T5] = all_rows()
