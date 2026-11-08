"""Gera os presets de glossário a partir da tradução oficial do Kenshi (pasta pt_BR com gamedata.po e pt_BR.translation).
Uso: python build_presets_final.py <pasta pt_BR> <pasta de saída>"""
import sys, re, json, collections, pathlib
Z=pathlib.Path(sys.argv[1]);OUT=pathlib.Path(sys.argv[2]);OUT.mkdir(parents=True,exist_ok=True)

def un(s):
    s=s.strip()
    if s.startswith('"') and s.endswith('"'): s=s[1:-1]
    return s.replace('\\"','"').replace('\\n','\n').replace('\\\\','\\')
def parse(path):
    out=[]
    for blk in re.split(r'\n\s*\n',open(path,encoding='utf-8').read()):
        ctx=mid=ms=cur=None
        for line in blk.split('\n'):
            if line.startswith('msgctxt '): cur='c';ctx=un(line[8:])
            elif line.startswith('msgid '): cur='i';mid=un(line[6:])
            elif line.startswith('msgstr '): cur='s';ms=un(line[7:])
            elif line.startswith('"'):
                v=un(line)
                if cur=='c':ctx+=v
                elif cur=='i':mid+=v
                elif cur=='s':ms+=v
        if mid and ctx is not None: out.append((ctx,mid.strip(),(ms or '').strip()))
    return out

entries=parse(Z/'gamedata.po')
names=[(c.split(',')[0],en,pt) for c,en,pt in entries if c.split(',')[-1]=='']
txt=(Z/'pt_BR.translation').read_bytes().decode('utf-8','ignore')
low=collections.Counter(re.findall(r"[a-z]{3,}",txt))         # palavras em minúscula no jogo = palavras comuns
low.update(re.findall(r"[a-z]{3,}",' '.join(re.findall(r'msgid "(.*)"',(Z/'main.po').read_text(encoding='utf-8')))))

BAD=re.compile(r"/|\|\||--|override|\bOLD\b|copy|template|TEMPLATE|delete|^CHARACTER|\d{3,}|\bdead\b|^test|^Test|\?\?|MARKER|\bnest\b|nest-|nestruin|housecamp|^\s*$|initialisation|random character|Expedition \d|\bgeneric\b",re.I)
def clean(t):
    out={}
    for tt,en,pt in names:
        if tt!=t or not pt or BAD.search(en) or BAD.search(pt): continue
        if '(' in en or ')' in en or not (2<=len(en)<=48): continue
        if en[:1].islower(): continue
        # palavra comum sozinha ("Nowhere", "Wolves") não entra: viraria regra em qualquer frase
        if ' ' not in en and (low[en.lower()]>=2 or low[en.lower().rstrip('s')]>=3): continue
        out[en]=pt
    return out
towns,facs,chars=clean('TOWN'),clean('FACTION'),clean('CHARACTER')
for k in ('Shark','Spring','Your Outpost','Raided Caravan','Camp- Cannibal Hunters','Tiny Settlement'): towns.pop(k,None)
for k in ('Fisher','Herbivore'): facs.pop(k,None)

# --- facções: também sem o artigo ("The Holy Nation" -> "Holy Nation" / "Nação Sagrada")
extra={}
for en,pt in list(facs.items()):
    if en.startswith('The ') and re.match(r'(A|O|As|Os) ',pt):
        extra.setdefault(en[4:],pt.split(' ',1)[1])
for k,v in extra.items(): facs.setdefault(k,v)

# --- personagens: só quem tem nome próprio
TITLES={'Lord','Lady','Sir','Boss','Doctor','General','Emperor','Mr','Slave Master','Slave Mistress','High Inquisitor','Lord Commander','Little','Big','Mad','Cannibal Hunter','Stubs'}
tok=collections.Counter(w for n in chars for w in re.split(r"[ ,]",n))
def namey(w): return w[:1].isupper() and len(w)>=3 and low[w.lower()]<=2 and tok[w]<=2 and not re.search(r'bot$|ling$',w)
MANUAL={'Big Al','Mr Floppy','Little Jon','Stubs Momuso','Mad Cat-Lon','Cannibal Hunter Robun','The Preacher','Esata the Stone Golem','Mukai The Mountain','Rane The Giant','Tora The Fearless','Screamer the False','Emperor Tengu','Boss Simion','Doctor Chung','Big Darkbrow'}
DENY={'Sir Testalot','Bo','Slave Master Grande','Hex','Jewel','Picky','Razor','Shade','Silvershade','Screamy','Headshot','Griffin','Horse','Harbinger','Grayflayer','Gutterhead','Crumblejon','Blackshifter','Flayed Woman','Spring Agent','Straw Lieutenant','Stormthrall','Undertaker','Twinblade','Militia','Machinist','Manhunter','Karate Drifter','Alpha Gurgler','Anti-Slaver','Ex-Servant','Fark Guard','Head of Agriculture','High Overseer','Holy Pacifier','Hydraulic Knight','Infinite Wingwang','Paladin Guardian','Skeleton Grayflayer','Skeleton Civilian','Soldierbot Guard','Spider Foreman','Sniperbot','Rhinobot','Upgraded Watchbot','Watchbot','No-Face','Shek Dueler','Shek Retainer','TG Diplomat','The Five Invincibles','Mongrel Bar Patron','Mongrel crazy','Big Fang','Big Gray','Flotsam Jonin','Flotsam Ninja','Black Dragon Genin','Sand Ninja Jounin','Sand Ninja Oni','Swamp Ninja Chunin','Swamp Ninja Genin','Screamer Unit','Manhunter Boss','Grass Pirate','Armour King\'s Thrall','Armoury Droneguard','Lord Mirage'}
people={}
for en,pt in chars.items():
    if en in DENY: continue
    ws=en.split()
    single = len(ws)==1 and pt==en and low[en.lower()]==0 and tok[en]<=2
    titled = len(ws)>=2 and any(namey(w) for w in ws[1:]) and any(en.startswith(t+' ') for t in TITLES)
    thex   = re.match(r"^[A-Z]\w+ [Tt]he [A-Z]\w+",en) and namey(ws[0])
    if single or titled or thex or en in MANUAL: people[en]=pt
# Lord Mirage é "Lorde Mirage" e é nome: volta
if 'Lord Mirage' in chars: people['Lord Mirage']=chars['Lord Mirage']

def dump(fname,nome,desc,terms):
    terms={k:(None if v==k else v) for k,v in sorted(terms.items(),key=lambda kv:kv[0].casefold())}
    json.dump({"nome":nome,"descricao":desc,"idioma":"pt-BR","fonte":"Tradução oficial do Kenshi (pt-BR), gamedata.po","case_sensitive":True,"terms":terms},
              open(OUT/fname,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    return len(terms)
n1=dump('vanilla_pt-BR_cidades.json','Cidades e locais (Kenshi pt-BR)','Nomes de cidades, vilas, acampamentos, ruínas e outros locais como no Kenshi em português.',towns)
n2=dump('vanilla_pt-BR_faccoes.json','Facções (Kenshi pt-BR)','Nomes de facções como no Kenshi em português (Nação Sagrada, Reino Shek...).',facs)
n3=dump('vanilla_pt-BR_personagens.json','Personagens com nome (Kenshi pt-BR)','Personagens únicos e importantes com nome fixo (Lorde Inaba, Hamut, Cat-Lon...).',people)
print(n1,n2,n3)
