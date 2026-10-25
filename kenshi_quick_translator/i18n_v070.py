"""Textos novos da 0.7.0 (modo seguro e janela de configurações em seções)."""
from __future__ import annotations

MORE_V070: list[tuple[str, str, str, str, str]] = [
    ('Aparência', 'Appearance', 'Apariencia', 'Внешний вид', '外观'),
    ('Avisos', 'Notices', 'Avisos', 'Уведомления', '提醒'),
    ('Tradução', 'Translation', 'Traducción', 'Перевод', '翻译'),
    ('Instalação no jogo', 'Installing in the game', 'Instalación en el juego', 'Установка в игру', '安装到游戏'),
    ('Dados e créditos', 'Data and credits', 'Datos y créditos', 'Данные и авторы', '数据与致谢'),
    ('Modo seguro (recomendado)', 'Safe mode (recommended)', 'Modo seguro (recomendado)', 'Безопасный режим (рекомендуется)', '安全模式（推荐）'),
    ('Traduz só registros que têm texto de jogo (diálogos, itens, facções, personagens...). Animações, arquivos e efeitos ficam intactos, porque traduzir ali pode corromper o mod. Vale na próxima vez que o mod for aberto.', 'Translates only records that have in-game text (dialogue, items, factions, characters...). Animations, files and effects are left untouched, because translating them can corrupt the mod. Applies the next time the mod is opened.', 'Traduce solo registros con texto del juego (diálogos, objetos, facciones, personajes...). Animaciones, archivos y efectos quedan intactos, porque traducirlos puede corromper el mod. Se aplica la próxima vez que se abra el mod.', 'Переводит только записи с игровым текстом (диалоги, предметы, фракции, персонажи...). Анимации, файлы и эффекты не трогаются, так как перевод там может испортить мод. Действует при следующем открытии мода.', '只翻译含游戏文本的记录（对话、物品、阵营、角色…）。动画、文件和特效保持不变，因为翻译它们可能损坏模组。下次打开模组时生效。'),
    ('Mods com pasta locale: montar o idioma completo', 'Mods with a locale folder: build the full language', 'Mods con carpeta locale: montar el idioma completo', 'Моды с папкой locale: собрать полный язык', '带 locale 文件夹的模组：组装完整语言包'),
    ('Corrige menu, falas e tela de início que ficam em inglês em mods como o Project Kathun, e traduz as frases do próprio mod. O original da pasta locale fica guardado como locale_off.', "Fixes the menu, dialogue and start screen that stay in English in mods like Project Kathun, and translates the mod's own phrases. The original locale folder is kept as locale_off.", 'Corrige el menú, los diálogos y la pantalla de inicio que quedan en inglés en mods como Project Kathun, y traduce las frases del propio mod. La carpeta locale original se guarda como locale_off.', 'Исправляет меню, диалоги и стартовый экран, остающиеся на английском в модах вроде Project Kathun, и переводит фразы самого мода. Оригинальная папка locale сохраняется как locale_off.', '修复 Project Kathun 等模组中仍为英文的菜单、对话和开局界面，并翻译模组自身的短语。原 locale 文件夹会保留为 locale_off。'),
    ('Apaga projetos, memória de tradução e cópias do programa (você escolhe o quê). Os mods não são alterados.', "Deletes projects, translation memory and the program's copies (you choose what). Your mods are not changed.", 'Borra proyectos, memoria de traducción y copias del programa (tú eliges qué). Los mods no se modifican.', 'Удаляет проекты, память переводов и копии программы (вы выбираете что). Сами моды не меняются.', '删除项目、翻译记忆和程序的副本（由你选择）。模组本身不会被修改。'),
    ('Azul galáxia', 'Galaxy blue', 'Azul galaxia', 'Синяя галактика', '银河蓝'),
    ('Verde', 'Green', 'Verde', 'Зелёная', '绿色'),
    ('Vermelho', 'Red', 'Rojo', 'Красная', '红色'),
    ('Amarelo', 'Yellow', 'Amarillo', 'Жёлтая', '黄色'),
    ('Laranja', 'Orange', 'Naranja', 'Оранжевая', '橙色'),
    ('Roxo', 'Purple', 'Morado', 'Фиолетовая', '紫色'),
    ('Rosa', 'Pink', 'Rosa', 'Розовая', '粉色'),
]
PATTERNS_V070: list = []
