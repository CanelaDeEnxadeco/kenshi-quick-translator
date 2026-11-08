"""
Memória de tradução: guarda cada frase já traduzida para nunca pagar (nem
esperar) duas vezes pela mesma frase, em nenhum mod. Usa SQLite, que já vem
com o Python.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Iterable


class TranslationMemory:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute(
                """CREATE TABLE IF NOT EXISTS tm (
                       src TEXT NOT NULL,
                       tl  TEXT NOT NULL,
                       dst TEXT NOT NULL,
                       origin TEXT NOT NULL,
                       ts REAL NOT NULL,
                       PRIMARY KEY (src, tl)
                   )"""
            )
            self._db.commit()

    def get(self, src: str, target_lang: str) -> str | None:
        with self._lock:
            row = self._db.execute(
                "SELECT dst FROM tm WHERE src = ? AND tl = ?", (src, target_lang)
            ).fetchone()
        return row[0] if row else None

    def get_many(self, sources: Iterable[str], target_lang: str) -> dict[str, str]:
        """Consulta vários textos de uma vez (bem mais rápido que um por um)."""
        found: dict[str, str] = {}
        batch: list[str] = []

        def flush() -> None:
            if not batch:
                return
            marks = ",".join("?" * len(batch))
            with self._lock:
                rows = self._db.execute(
                    f"SELECT src, dst FROM tm WHERE tl = ? AND src IN ({marks})", [target_lang, *batch]
                ).fetchall()
            found.update(rows)
            batch.clear()

        for s in sources:
            batch.append(s)
            if len(batch) >= 500:  # o SQLite limita a quantidade de parâmetros por consulta
                flush()
        flush()
        return found

    def put(self, src: str, target_lang: str, dst: str, origin: str = "auto") -> None:
        """origin: nome do serviço, ou 'revisao' para o que o usuário corrigiu."""
        self.put_many([(src, dst)], target_lang, origin)

    def put_many(self, items: Iterable[tuple[str, str]], target_lang: str, origin: str = "auto") -> None:
        """Grava vários de uma vez, com uma única gravação em disco."""
        now = time.time()
        rows = [(s, target_lang, d, origin, now) for s, d in items]
        if not rows:
            return
        with self._lock:
            self._db.executemany(
                "INSERT INTO tm (src, tl, dst, origin, ts) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(src, tl) DO UPDATE SET dst = excluded.dst, "
                "origin = excluded.origin, ts = excluded.ts",
                rows,
            )
            self._db.commit()

    def export_json(self, path: str | Path) -> int:
        """Salva a memória num arquivo .json (para levar a outro computador ou compartilhar)."""
        import json
        with self._lock:
            rows = self._db.execute("SELECT src, tl, dst, origin FROM tm").fetchall()
        data = [{"src": a, "tl": b, "dst": c, "origin": d} for a, b, c, d in rows]
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
        return len(data)

    def import_json(self, path: str | Path, overwrite: bool = False) -> int:
        """Junta um arquivo exportado à memória. Por padrão não troca o que já existe. Devolve quantas entradas entraram."""
        import json
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        n = 0
        by_tl: dict[str, list[tuple[str, str, str]]] = {}
        for r in data:
            if isinstance(r, dict) and r.get("src") and r.get("dst") and r.get("tl"):
                by_tl.setdefault(r["tl"], []).append((r["src"], r["dst"], str(r.get("origin") or "importada")))
        for tl, items in by_tl.items():
            if not overwrite:
                have = self.get_many([a for a, _b, _c in items], tl)
                items = [x for x in items if x[0] not in have]
            for origin in {x[2] for x in items}:
                self.put_many([(a, b) for a, b, c in items if c == origin], tl, origin)
            n += len(items)
        return n

    def count(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM tm").fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._db.close()
