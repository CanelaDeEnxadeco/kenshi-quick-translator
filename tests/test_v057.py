"""Testes da 0.5.7: gráfico de velocidade, imagem do mod, passo a passo e dicas (parte sem janela)."""
import tempfile
import unittest
from pathlib import Path

from kenshi_quick_translator import i18n
from kenshi_quick_translator.ui_extra import (TIPS_BY_TEXT, TOUR_STEPS, RateTracker, icon_factor, pick_icon_file,
                                      sparkline_coords)


class Velocidade(unittest.TestCase):
    def test_velocidade_constante(self):
        r, t, done = RateTracker(), 1000.0, 0
        novos = 0
        for _ in range(40):
            t += 0.5
            done += 10  # 20 textos por segundo = 1200 por minuto
            novos += r.add(t, done)
        self.assertGreaterEqual(novos, 5)
        self.assertTrue(all(abs(p - 1200) < 5 for p in r.points), r.points)
        self.assertAlmostEqual(r.peak, r.current, delta=5)

    def test_proximo_mod_da_fila_nao_gera_ponto_falso(self):
        r, t = RateTracker(), 0.0
        done = 0
        for _ in range(20):
            t += 0.5
            done += 10
            r.add(t, done)
        antes = list(r.points)
        t += 0.5
        r.add(t, 0)  # outro mod: o contador voltou a zero
        for _ in range(20):
            t += 0.5
            done += 0
        self.assertTrue(all(p >= 0 for p in r.points))
        self.assertEqual(r.points[: len(antes)], antes)

    def test_sem_progresso_da_zero_e_reset_limpa(self):
        r, t = RateTracker(), 0.0
        for _ in range(12):
            t += 1.0
            r.add(t, 5)  # parado
        self.assertTrue(all(p == 0 for p in r.points))
        r.reset()
        self.assertEqual(r.points, [])

    def test_coordenadas(self):
        self.assertEqual(sparkline_coords([5], 100, 30), [])
        c = sparkline_coords([0, 10], 100, 30)
        self.assertEqual(len(c), 4)
        self.assertGreater(c[1], c[3])  # maior velocidade = mais alto (y menor)


class Imagem(unittest.TestCase):
    def test_escolhe_imagem_do_mod(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "Hydro.mod").write_bytes(b"m")
            (d / "zzz.png").write_bytes(b"x")
            (d / "preview.jpg").write_bytes(b"x")
            (d / "Hydro.png").write_bytes(b"x")
            self.assertEqual(pick_icon_file(d / "Hydro.mod").name, "Hydro.png")
            (d / "Hydro.png").unlink()
            self.assertEqual(pick_icon_file(d / "Hydro.mod").name, "preview.jpg")
            self.assertIsNone(pick_icon_file(d / "Hydro.mod", strict=True))

    def test_pasta_sem_imagem_e_imagem_enorme(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "a.mod").write_bytes(b"m")
            self.assertIsNone(pick_icon_file(d / "a.mod"))
            (d / "a.png").write_bytes(b"x" * (5 * 1024 * 1024))
            self.assertIsNone(pick_icon_file(d / "a.mod"))  # grande demais: não vira ícone

    def test_fator(self):
        self.assertEqual(icon_factor(1024, 512, 20), 52)
        self.assertEqual(icon_factor(10, 10, 20), 1)


class Textos(unittest.TestCase):
    def test_tour_e_dicas_traduzidos_nos_quatro_idiomas(self):
        try:
            textos = [t for s in TOUR_STEPS for t in s[1:]] + [t for _, t in TIPS_BY_TEXT]
            textos += ["Primeiros passos", "Pular", "Voltar", "Próximo", "Concluir", "▶  Passo a passo",
                       "Não mostrar de novo", "Agora: ", " · Pico: "]
            for lang in ("en", "es", "ru", "zh"):
                i18n.set_language(lang)
                for t in textos:
                    if lang == "es" and t in (" · Pico: ", "Concluir"):
                        continue  # em espanhol é igual ou muito parecido
                    self.assertNotEqual(i18n.tr(t), t, (lang, t[:50]))
            i18n.set_language("zh")
            self.assertEqual(i18n.tr("Passo 2 de 4"), "第 2 步,共 4 步")
        finally:
            i18n.set_language("pt")

    def test_alvos_do_tour_conhecidos(self):
        self.assertEqual({s[0] for s in TOUR_STEPS}, {"mods", "how", "review", "help"})


if __name__ == "__main__":
    unittest.main()
