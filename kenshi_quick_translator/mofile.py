"""
Arquivos de idioma .mo (gettext) da interface.

Alguns mods (ex.: Project Kathun) trazem uma pasta `locale` com um .mo próprio para trocar
poucos textos da interface ("Katanas" -> "Lightsabers"). Se o jogo usa esse arquivo NO LUGAR
do pacote do idioma escolhido, o resto do menu cai para o inglês. Este módulo lê e grava .mo
e junta os dois: pacote do idioma do jogo + textos do mod já traduzidos.

Só formato; nada aqui acessa a rede ou a pasta do Kenshi.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field

MAGIC_LE = 0x950412DE
MAGIC_BE = 0xDE120495
_CHARSET = re.compile(r"charset\s*=\s*([\w.\-]+)", re.I)
_LANG = re.compile(r"^Language:\s*(\S+)", re.I | re.M)


class MoError(ValueError):
    """Arquivo .mo ilegível ou fora do formato."""


@dataclass
class Catalog:
    """Entradas {msgid: msgstr}. msgid pode ter contexto ("ctx\\x04id") e plural ("a\\x00b")."""

    entries: dict[str, str] = field(default_factory=dict)
    header: str = ""  # texto do cabeçalho (msgid vazio): Content-Type, Language...
    encoding: str = "utf-8"

    @property
    def language(self) -> str:
        m = _LANG.search(self.header)
        return m.group(1) if m else ""

    def __len__(self) -> int:
        return len(self.entries)


def _charset(header: str) -> str:
    m = _CHARSET.search(header)
    name = (m.group(1) if m else "utf-8").lower()
    return "utf-8" if name in ("utf8", "utf-8", "") else name


def read_mo(data: bytes) -> Catalog:
    if len(data) < 28:
        raise MoError("arquivo pequeno demais para ser um .mo")
    magic = struct.unpack("<I", data[:4])[0]
    if magic == MAGIC_LE:
        end = "<"
    elif magic == MAGIC_BE:
        end = ">"
    else:
        raise MoError("não é um arquivo .mo (marca inicial desconhecida)")
    _rev, n, off_o, off_t = struct.unpack(end + "4I", data[4:20])
    if n < 0 or off_o + 8 * n > len(data) or off_t + 8 * n > len(data):
        raise MoError("tabelas do .mo fora do arquivo")

    def piece(table: int, i: int) -> bytes:
        length, offset = struct.unpack(end + "2I", data[table + 8 * i : table + 8 * i + 8])
        if offset + length > len(data):
            raise MoError("texto do .mo fora do arquivo")
        return data[offset : offset + length]

    pairs = [(piece(off_o, i), piece(off_t, i)) for i in range(n)]
    header_raw = next((t for o, t in pairs if o == b""), b"")
    header = header_raw.decode("utf-8", errors="replace")
    enc = _charset(header)
    cat = Catalog(header=header, encoding=enc)
    for o, t in pairs:
        if o == b"":
            continue
        try:
            cat.entries[o.decode(enc)] = t.decode(enc)
        except (UnicodeDecodeError, LookupError) as e:
            raise MoError(f"texto do .mo não está em {enc}") from e
    return cat


def write_mo(cat: Catalog) -> bytes:
    """Grava um .mo (ordem dos msgids crescente, sem tabela hash: o gettext aceita)."""
    enc = cat.encoding or "utf-8"
    items = [(b"", cat.header.encode(enc))] if cat.header else []
    items += sorted((k.encode(enc), v.encode(enc)) for k, v in cat.entries.items())
    n = len(items)
    off_o = 28
    off_t = off_o + 8 * n
    data_start = off_t + 8 * n
    o_blob, t_blob, o_tab, t_tab = b"", b"", [], []
    pos = data_start
    for o, _t in items:
        o_tab.append((len(o), pos + len(o_blob)))
        o_blob += o + b"\x00"
    pos += len(o_blob)
    for _o, t in items:
        t_tab.append((len(t), pos + len(t_blob)))
        t_blob += t + b"\x00"
    out = struct.pack("<7I", MAGIC_LE, 0, n, off_o, off_t, 0, 0)
    for ln, off in o_tab:
        out += struct.pack("<2I", ln, off)
    for ln, off in t_tab:
        out += struct.pack("<2I", ln, off)
    return out + o_blob + t_blob


def merge(game: Catalog, mod: Catalog, mod_texts: dict[str, str] | None = None) -> Catalog:
    """
    Pacote do jogo + textos do mod. `mod_texts` {msgid: texto já traduzido} vale no lugar do que
    está no .mo do mod (ex.: o "Lightsabers" traduzido). Textos do mod sem msgstr são ignorados.
    O cabeçalho (idioma, plural) é o do jogo.
    """
    header = game.header or mod.header
    # a saída é sempre UTF-8 (qualquer idioma cabe); o cabeçalho passa a dizer isso
    header = _CHARSET.sub("charset=UTF-8", header) if _CHARSET.search(header) else header
    out = Catalog(entries=dict(game.entries), header=header, encoding="utf-8")
    for k, v in mod.entries.items():
        text = (mod_texts or {}).get(k, v)
        if text and text.strip():
            out.entries[k] = text
    return out
