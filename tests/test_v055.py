"""v0.5.5: tamanho da letra, posição da janela, configuração nova (sem Tkinter)."""
import json
import tempfile
import unittest
from pathlib import Path

from kenshi_quick_translator.config import Config
from kenshi_quick_translator.ui_state import FONT_STEPS, clamp_geometry, clamp_scale, parse_geometry, step_font


class FonteTests(unittest.TestCase):
    def test_passos(self):
        self.assertEqual(step_font(100, +1), 115)
        self.assertEqual(step_font(100, -1), 85)
        self.assertEqual(step_font(85, -1), 85)  # não passa do menor
        self.assertEqual(step_font(150, +1), 150)  # nem do maior
        self.assertEqual(step_font(130, 0), 100)
        self.assertEqual(step_font(107, +1), 115)  # valor fora dos passos vai ao vizinho
        self.assertEqual(step_font(107, -1), 100)

    def test_valor_invalido(self):
        self.assertEqual(clamp_scale("abc"), 100)
        self.assertEqual(clamp_scale(5), 70)
        self.assertEqual(clamp_scale(900), 200)
        self.assertIn(100, FONT_STEPS)


class JanelaTests(unittest.TestCase):
    V = (0, 0, 1920, 1080)

    def test_le_geometria(self):
        self.assertEqual(parse_geometry("1200x800+10+20"), (1200, 800, 10, 20))
        self.assertEqual(parse_geometry("1200x800+-8+0"), (1200, 800, -8, 0))
        self.assertIsNone(parse_geometry("lixo"))
        self.assertIsNone(parse_geometry(""))

    def test_dentro_da_tela_fica_igual(self):
        self.assertEqual(clamp_geometry("1200x800+100+50", self.V, (900, 560)), "1200x800+100+50")

    def test_monitor_desligado_traz_para_a_tela(self):
        # estava num segundo monitor à direita (x=2500) que não existe mais
        self.assertEqual(clamp_geometry("1200x800+2500+50", self.V, (900, 560)), "1200x800+720+50")

    def test_nao_deixa_menor_que_o_minimo_nem_maior_que_a_tela(self):
        self.assertEqual(clamp_geometry("300x200+0+0", self.V, (900, 560)), "900x560+0+0")
        w = clamp_geometry("5000x5000+0+0", self.V, (900, 560))
        self.assertEqual(w, "1900x1020+0+0")

    def test_monitor_a_esquerda_com_x_negativo(self):
        v = (-1920, 0, 3840, 1080)
        self.assertEqual(clamp_geometry("1200x800+-1500+10", v, (900, 560)), "1200x800+-1500+10")


class ConfigTests(unittest.TestCase):
    def test_config_antiga_sem_campos_novos_carrega(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            p.write_text(json.dumps({"target_lang": "pt-BR", "ptbr_fix": True}), encoding="utf-8")
            c = Config.load(p)
            self.assertEqual((c.font_scale, c.win_geometry, c.last_selection, c.mod_filter, c.mod_sort),
                             (100, "", [], "todos", "padrao"))

    def test_salva_e_le_estado_da_janela(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            c = Config()
            c.font_scale, c.win_geometry, c.win_zoomed = 130, "1300x900+40+20", True
            c.last_selection = ["C:/mods/A.mod"]
            c.save(p)
            c2 = Config.load(p)
            self.assertEqual((c2.font_scale, c2.win_geometry, c2.win_zoomed, c2.last_selection),
                             (130, "1300x900+40+20", True, ["C:/mods/A.mod"]))


if __name__ == "__main__":
    unittest.main()
