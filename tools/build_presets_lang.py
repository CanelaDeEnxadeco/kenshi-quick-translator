"""Gera TODOS os presets de glossário de um idioma a partir da tradução oficial do Kenshi daquele idioma.
Uso: python build_presets_lang.py <pasta do idioma (com gamedata.po e <x>.translation)> <codigo do programa: es, fr, de, ru, ja, ko, zh, pt-BR> <pasta de saída>
Só entra nome que existe de fato no arquivo .translation (o que o jogo lê), conferido byte a byte."""
import sys, re, json, struct, collections, pathlib

Z = pathlib.Path(sys.argv[1]); CODE = sys.argv[2]; OUT = pathlib.Path(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
NOMES = {"pt-BR": "Português (Brasil)", "es": "Español", "fr": "Français", "de": "Deutsch", "ru": "Русский", "ja": "日本語", "ko": "한국어", "zh": "中文"}
LANG = NOMES.get(CODE, CODE)

def un(s):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'): s = s[1:-1]
    return s.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')

def parse(path):
    """Aceita os dois formatos: com msgctxt ("TIPO,Nome,campo") e o antigo, só com '#. Type:' e '#. Name:'."""
    out = []
    for blk in re.split(r'\n\s*\n', path.read_text(encoding='utf-8-sig')):
        ctx = mid = ms = cur = typ = name = ref = None
        for line in blk.split('\n'):
            if line.startswith('#. Type:'): typ = line[8:].strip()
            elif line.startswith('#. Name:'): name = line[8:].strip()
            elif line.startswith('#: ') and ref is None: ref = line[3:].strip()
            elif line.startswith('msgctxt '): cur = 'c'; ctx = un(line[8:])
            elif line.startswith('msgid '): cur = 'i'; mid = un(line[6:])
            elif line.startswith('msgstr '): cur = 's'; ms = un(line[7:])
            elif line.startswith('"'):
                v = un(line)
                if cur == 'c': ctx += v
                elif cur == 'i': mid += v
                elif cur == 's': ms += v
        if not mid: continue
        if ctx is not None:
            p = ctx.split(','); out.append((p[0], mid.strip(), (ms or '').strip(), p[-1], ref))
        elif typ:
            out.append((typ, mid.strip(), (ms or '').strip(), '' if name is not None and mid.strip() == name.strip() else 'x', ref))
    return out

ents = parse(next(Z.rglob('gamedata.po')))
trfile = next(Z.rglob('*.translation'))
blob = trfile.read_bytes()
def no_jogo(s):
    e = s.encode('utf-8'); return struct.pack('<I', len(e)) + e in blob

# O .translation guarda, para cada registro, [nome traduzido][id-arquivo]. Serve de fonte principal:
# o .po de alguns idiomas está vazio ou desatualizado (ex.: francês).
by_id = {}
for m in re.finditer(rb'\d+-[^\x00-\x1f]{1,90}?\.(?:mod|base)', blob):
    a = m.start()
    if a < 8 or struct.unpack('<I', blob[a - 4:a])[0] != len(m.group(0)): continue
    for L in range(1, 160):
        if a - 4 - L - 4 < 0: break
        if struct.unpack('<I', blob[a - 8 - L:a - 4 - L])[0] == L:
            try: by_id.setdefault(m.group(0).decode(), blob[a - 4 - L:a - 4].decode('utf-8'))
            except UnicodeDecodeError: pass
            break
names = []
for t, en, tr, f, ref in ents:
    if f != '': continue
    ref = (ref or '').split(' ')[0]
    got = by_id.get(ref, '')
    if not tr and got and got != en: tr = got        # po vazio: usa o que o jogo realmente tem
    if not tr and t in ('TOWN', 'FACTION', 'CHARACTER', 'RACE', 'BIOME_GROUP'): tr = en   # sem tradução: o jogo mostra o nome original
    names.append((t, en, tr))

txt = blob.decode('utf-8', 'ignore')
low = collections.Counter(re.findall(r"[a-z]{3,}", txt))
mainpo = next(Z.rglob('main.po'), None)
if mainpo: low.update(re.findall(r"[a-z]{3,}", ' '.join(re.findall(r'msgid "(.*)"', mainpo.read_text(encoding='utf-8', errors='ignore')))))

BAD = re.compile(r"/|\|\||--|override|\bOLD\b|copy|template|TEMPLATE|delete|^CHARACTER|\d{3,}|\bdead\b|^test|^Test|\?\?|MARKER|\bnest\b|nest-|nestruin|housecamp|^\s*$|initialisation|random character|Expedition \d|\bgeneric\b", re.I)
def clean(t):
    out = {}
    for tt, en, tr in names:
        if tt != t or not tr or BAD.search(en) or BAD.search(tr): continue
        if '(' in en or ')' in en or not (2 <= len(en) <= 48) or en[:1].islower(): continue
        if ' ' not in en and (low[en.lower()] >= 2 or low[en.lower().rstrip('s')] >= 3): continue
        if tr != en and not no_jogo(tr): continue
        out[en] = tr
    return out
towns, facs, chars = clean('TOWN'), clean('FACTION'), clean('CHARACTER')
for k in ('Shark', 'Spring', 'Your Outpost', 'Raided Caravan', 'Camp- Cannibal Hunters', 'Tiny Settlement'): towns.pop(k, None)
for k in ('Fisher', 'Herbivore'): facs.pop(k, None)
extra = {}
for en, tr in list(facs.items()):
    if en.startswith('The ') and tr != en:
        extra.setdefault(en[4:], None)          # sem o "The": o valor é resolvido abaixo
for k in list(extra):
    full = 'The ' + k
    # tira o artigo da tradução só quando ele existe como palavra separada (pt/es/fr/de...)
    m = re.match(r'^(A|O|As|Os|El|La|Los|Las|Le|Les|L\'|Der|Die|Das|Den|Dem)\s+(.+)$', facs[full])
    if m: facs.setdefault(k, m.group(2))
    elif CODE in ('ru', 'ja', 'ko', 'zh') and facs[full] != full: facs.setdefault(k, facs[full])   # idiomas sem artigo

TITLES = {'Lord', 'Lady', 'Sir', 'Boss', 'Doctor', 'General', 'Emperor', 'Mr', 'Slave Master', 'Slave Mistress', 'High Inquisitor', 'Lord Commander', 'Little', 'Big', 'Mad', 'Cannibal Hunter', 'Stubs'}
tok = collections.Counter(w for n in chars for w in re.split(r"[ ,]", n))
def namey(w): return w[:1].isupper() and len(w) >= 3 and low[w.lower()] <= 2 and tok[w] <= 2 and not re.search(r'bot$|ling$', w)
MANUAL = {'Big Al', 'Mr Floppy', 'Little Jon', 'Stubs Momuso', 'Mad Cat-Lon', 'Cannibal Hunter Robun', 'The Preacher', 'Esata the Stone Golem', 'Mukai The Mountain', 'Rane The Giant', 'Tora The Fearless', 'Screamer the False', 'Emperor Tengu', 'Boss Simion', 'Doctor Chung', 'Big Darkbrow', 'Lord Mirage'}
DENY = {'Sir Testalot', 'Bo', 'Slave Master Grande', 'Hex', 'Jewel', 'Picky', 'Razor', 'Shade', 'Silvershade', 'Screamy', 'Headshot', 'Griffin', 'Horse', 'Harbinger', 'Grayflayer', 'Gutterhead', 'Crumblejon', 'Blackshifter', 'Flayed Woman', 'Spring Agent', 'Straw Lieutenant', 'Stormthrall', 'Undertaker', 'Twinblade', 'Militia', 'Machinist', 'Manhunter', 'Karate Drifter', 'Alpha Gurgler', 'Anti-Slaver', 'Ex-Servant', 'Fark Guard', 'Head of Agriculture', 'High Overseer', 'Holy Pacifier', 'Hydraulic Knight', 'Infinite Wingwang', 'Paladin Guardian', 'Skeleton Grayflayer', 'Skeleton Civilian', 'Soldierbot Guard', 'Spider Foreman', 'Sniperbot', 'Rhinobot', 'Upgraded Watchbot', 'Watchbot', 'No-Face', 'Shek Dueler', 'Shek Retainer', 'TG Diplomat', 'The Five Invincibles', 'Mongrel Bar Patron', 'Mongrel crazy', 'Big Fang', 'Big Gray', 'Flotsam Jonin', 'Flotsam Ninja', 'Black Dragon Genin', 'Sand Ninja Jounin', 'Sand Ninja Oni', 'Swamp Ninja Chunin', 'Swamp Ninja Genin', 'Screamer Unit', 'Manhunter Boss', 'Grass Pirate', "Armour King's Thrall", 'Armoury Droneguard'}
people = {}
for en, tr in chars.items():
    if en in DENY: continue
    ws = en.split()
    single = len(ws) == 1 and tr == en and low[en.lower()] == 0 and tok[en] <= 2
    titled = len(ws) >= 2 and any(namey(w) for w in ws[1:]) and any(en.startswith(t + ' ') for t in TITLES)
    thex = re.match(r"^[A-Z]\w+ [Tt]he [A-Z]\w+", en) and namey(ws[0])
    if single or titled or thex or en in MANUAL: people[en] = tr

def pick(types, keep_same=False, single_ok=False):
    out = {}
    for t, en, tr in names:
        if t not in types or not tr or BAD.search(en) or BAD.search(tr): continue
        if '(' in en or ')' in en or not (2 <= len(en) <= 60) or en[:1].islower() or (en.isupper() and len(en) > 3): continue
        if tr == en and not keep_same: continue
        if ' ' not in en and not single_ok: continue
        if tr != en and not no_jogo(tr): continue
        out[en] = tr
    return out

def dump(slug, nome, desc, terms):
    terms = {k: (None if v == k else v) for k, v in sorted(terms.items(), key=lambda kv: kv[0].casefold())}
    if not terms: return 0
    json.dump({"nome": f"{nome} [{LANG}]", "descricao": desc, "idioma": CODE,
               "fonte": f"Tradução oficial do Kenshi ({LANG}), gamedata.po conferido com {trfile.name}",
               "case_sensitive": True, "terms": terms},
              open(OUT / f"vanilla_{CODE}_{slug}.json", 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return len(terms)

res = {}
res['cidades'] = dump('cidades', 'Cidades e locais', 'Nomes de cidades, vilas, acampamentos e ruínas como no Kenshi oficial.', towns)
res['faccoes'] = dump('faccoes', 'Facções', 'Nomes de facções como no Kenshi oficial.', facs)
res['personagens'] = dump('personagens', 'Personagens com nome', 'Personagens únicos e importantes com nome fixo (lista por regras, aproximada).', people)
jobs = [('racas', 'Raças e animais', 'Raças e criaturas.', {'RACE', 'ANIMAL_CHARACTER'}, True),
        ('armas', 'Armas', 'Armas, bestas, munição e fabricantes.', {'WEAPON', 'CROSSBOW', 'WEAPON_MANUFACTURER', 'ITEM_AMMO'}, False),
        ('armaduras', 'Armaduras e roupas', 'Armaduras, capacetes, botas e roupas.', {'ARMOUR'}, False),
        ('itens', 'Itens e comida', 'Itens comuns, comida, recipientes, membros protéticos, medicamentos e mapas.', {'ITEM', 'ITEM_NO_FUNCTION', 'ITEM_FOOD', 'CONTAINER', 'MAP_ITEM', 'LIMB_REPLACEMENT', 'ITEM_SEVERED_LIMB', 'ITEM_FIRSTAID', 'ITEM_NARCOTIC', 'ITEM_BLUEPRINT', 'ITEMS_CULTURE'}, False),
        ('livros', 'Livros', 'Títulos dos livros do jogo.', {'ITEM_BOOK'}, False),
        ('construcoes', 'Construções', 'Construções, portões, móveis e estações de trabalho.', {'BUILDING'}, False),
        ('pesquisas', 'Pesquisas', 'Pesquisas e tecnologias.', {'RESEARCH'}, False),
        ('regioes', 'Regiões e biomas', 'Regiões do mapa.', {'BIOME_GROUP'}, True),
        ('comida', 'Comida e bebida', 'Comida, bebidas e drogas do jogo, inclusive nomes de uma palavra só (Pão, Grog...). Não vem marcado por padrão.', {'ITEM_FOOD', 'ITEM_FOOD_RESTRICTED', 'ITEM_NARCOTIC'}, False),
        ('cenarios', 'Cenários de início de jogo', 'Nomes dos cenários da tela de novo jogo (Fundo do Poço, Cidadão do Império...).', {'NEW_GAME_STARTOFF'}, False)]
for slug, nome, desc, types, same in jobs:
    res[slug] = dump(slug, nome, desc, pick(types, keep_same=same, single_ok=same or slug in ('comida', 'cenarios')))
res['personagens_todos'] = dump('personagens_todos', 'Personagens: lista completa', 'TODAS as entradas de personagem, inclusive cargos genéricos. O preset "Personagens com nome" é mais seguro.', pick({'CHARACTER'}))
print(CODE, res)
