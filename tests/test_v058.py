import tempfile, unittest
from pathlib import Path
from kenshi_quick_translator.core import copy_mod_folder


class CopyFolder(unittest.TestCase):
    def test_copia_tudo_menos_mod(self):
        with tempfile.TemporaryDirectory() as t:
            src, dst = Path(t, "src"), Path(t, "dst")
            (src / "models" / "a").mkdir(parents=True)
            dst.mkdir()
            (src / "Foo.mod").write_bytes(b"x")
            (src / "Foo.info").write_text("i")
            (src / "Foo.png").write_bytes(b"p")
            (src / "models" / "a" / "m.mesh").write_bytes(b"m")
            n = copy_mod_folder(src, dst, "Foo", "Foo PT")
            self.assertEqual(n, 3)
            self.assertFalse((dst / "Foo.mod").exists())
            self.assertTrue((dst / "Foo PT.png").exists())
            self.assertTrue((dst / "Foo.info").exists())
            self.assertTrue((dst / "models" / "a" / "m.mesh").exists())


if __name__ == "__main__":
    unittest.main()
