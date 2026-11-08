"""Gera presets EXTRAS de glossário (armas, armaduras, raças, itens, construções, pesquisas, regiões, livros e
lista completa de personagens) a partir da tradução oficial do Kenshi pt-BR.
Só entra nome que existe de fato no arquivo .translation (o que o jogo usa), conferido byte a byte.
Uso: python build_presets_extra.py <pasta pt_BR> <pasta de saída>"""
import sys, re, json, struct, pathlib
Z = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)

def un(s):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'): s = s[1:-1]
    return s.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')

ents = []
for blk in re.split(r'\n\s*\n', (Z / 'gamedata.po').read_text(encoding='utf-8')):
    ctx = mid = ms = cur = None
    for line in blk.split('\n'):
        if line.startswith('msgctxt '): cur = 'c'; ctx = un(line[8:])
        elif line.startswith('msgid '): cur = 'i'; mid = un(line[6:])
        elif line.startswith('msgstr '): cur = 's'; ms = un(line[7:])
        elif line.startswith('"'):
            v = un(line)
            if cur == 'c': ctx += v
            elif cur == 'i': mid += v
            elif cur == 's': ms += v
    if mid and ctx is not None:
        p = ctx.split(',')
        if p[-1] == '':  # só o NOME (sem descrição)
            ents.append((p[0], mid.strip(), (ms or '').strip()))

blob = (Z / 'pt_BR.translation').read_bytes()
def no_jogo(s):  # a tradução existe, com esse texto exato, no arquivo que o jogo lê?
    e = s.encode('utf-8'); return struct.pack('<I', len(e)) + e in blob

BAD = re.compile(r"/|\|\||--|override|\bOLD\b|copy|template|delete|^test|^Test|\?\?|MARKER|^\s*$|\d{4,}", re.I)
def pick(types, keep_same=False, allow_paren=False, single_ok=False):
    out = {}
    for t, en, pt in ents:
        if t not in types or not pt or BAD.search(en) or BAD.search(pt): continue
        if not allow_paren and ('(' in en or ')' in en): continue
        if not (2 <= len(en) <= 60) or en[:1].islower() or en.isupper() and len(en) > 3: continue
        if pt == en and not keep_same: continue
        if ' ' not in en and not single_ok: continue      # palavra solta ('Arc', 'Ancient') viraria regra em qualquer frase
        if pt[:1].islower() and not en[:1].islower(): continue
        if pt != en and not no_jogo(pt): continue      # conferência com o .translation
        out[en] = pt
    return out

def dump(fname, nome, desc, terms):
    terms = {k: (None if v == k else v) for k, v in sorted(terms.items(), key=lambda kv: kv[0].casefold())}
    json.dump({"nome": nome, "descricao": desc, "idioma": "pt-BR",
               "fonte": "Tradução oficial do Kenshi (pt-BR), gamedata.po conferido com pt_BR.translation",
               "case_sensitive": True, "terms": terms},
              open(OUT / fname, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return len(terms)

jobs = [
 ('vanilla_pt-BR_racas.json', 'Raças e animais (Kenshi pt-BR)', 'Raças (Shek, Hive, Skeleton...) e criaturas como no Kenshi em português.', {'RACE', 'ANIMAL_CHARACTER'}, True),
 ('vanilla_pt-BR_armas.json', 'Armas (Kenshi pt-BR)', 'Armas, bestas, munição e fabricantes de armas.', {'WEAPON', 'CROSSBOW', 'WEAPON_MANUFACTURER', 'ITEM_AMMO'}, False),
 ('vanilla_pt-BR_armaduras.json', 'Armaduras e roupas (Kenshi pt-BR)', 'Armaduras, capacetes, botas e roupas.', {'ARMOUR'}, False),
 ('vanilla_pt-BR_itens.json', 'Itens e comida (Kenshi pt-BR)', 'Itens comuns, comida, recipientes, membros protéticos, medicamentos e mapas.', {'ITEM_NO_FUNCTION', 'ITEM_FOOD', 'CONTAINER', 'MAP_ITEM', 'LIMB_REPLACEMENT', 'ITEM_SEVERED_LIMB', 'ITEM_FIRSTAID', 'ITEM_NARCOTIC', 'ITEM_BLUEPRINT', 'ITEMS_CULTURE'}, False),
 ('vanilla_pt-BR_livros.json', 'Livros (Kenshi pt-BR)', 'Títulos dos livros do jogo.', {'ITEM_BOOK'}, False),
 ('vanilla_pt-BR_construcoes.json', 'Construções (Kenshi pt-BR)', 'Nomes de construções, portões, móveis e estações de trabalho.', {'BUILDING'}, False),
 ('vanilla_pt-BR_pesquisas.json', 'Pesquisas (Kenshi pt-BR)', 'Nomes das pesquisas e tecnologias.', {'RESEARCH'}, False),
 ('vanilla_pt-BR_regioes.json', 'Regiões e biomas (Kenshi pt-BR)', 'Nomes das regiões do mapa (Cinerlanda, Campos Ósseos...).', {'BIOME_GROUP'}, True),
 ('vanilla_pt-BR_personagens_todos.json', 'Personagens: lista completa (Kenshi pt-BR)', 'TODAS as entradas de personagem do jogo. Inclui cargos genéricos (Mercenário, Guarda...). Use só se precisar de tudo; o preset "Personagens com nome" é mais seguro.', {'CHARACTER'}, False),
]
for fn, nome, desc, types, same in jobs:
    t = pick(types, keep_same=same, single_ok=same)
    print(fn, dump(fn, nome, desc, t))
