"""Pruebas de scripts/actualizar_publicas.py.  Correr: python -m unittest discover tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from actualizar_publicas import actualizar  # noqa: E402

YAML = """# comentario que no se toca
capturado: 2026-11-09
instagram:
  DWeVfAqBprj: {fecha: 2026-03-29, cuenta: natyfarah, coautor: canola.life, views: 143368, fb_views: 0, likes: 6755, comments: 105, shares: 2142, dur_s: 130}
  2026-07-09: {views: 1708776, likes: 113461, comments: 391, shares: 56481}
tiktok:
  "7629112348766194951": {fecha: 2026-04-15, cuenta: chefanagalvis, views: 77000, likes: 3955, comments: 61, shares: 876, saves: 2433, dur_s: 83}
facebook:
  2026-07-09: {url: "https://www.facebook.com/reel/1", views: 902589, likes: 27300, likes_aprox: true, comments: 81, shares: 2497}
"""


class Reglas(unittest.TestCase):
    def test_solo_sube_y_resto_igual(self):
        t, c, a = actualizar(YAML, [("instagram", "DWeVfAqBprj", {"views": 143462, "likes": 6700, "comments": 106})], "2026-11-14")
        self.assertIn("views: 143462, fb_views: 0, likes: 6755, comments: 106, shares: 2142, dur_s: 130", t)
        self.assertIn("cuenta: natyfarah, coautor: canola.life", t)
        self.assertTrue(any("se conserva 6755" in x for x in c))
        self.assertEqual(a, [])

    def test_clave_por_fecha_y_tiktok_con_comillas(self):
        t, _, _ = actualizar(YAML, [("instagram", "2026-07-09", {"views": 1710000}),
                                    ("tiktok", "7629112348766194951", {"saves": 2500})], "2026-11-14")
        self.assertIn("2026-07-09: {views: 1710000, likes: 113461", t)
        self.assertIn("saves: 2500, dur_s: 83", t)

    def test_facebook_no_se_toca_y_corte(self):
        t, _, _ = actualizar(YAML, [("instagram", "2026-07-09", {"views": 1})], "2026-11-14")
        self.assertIn("2026-07-09: {url: \"https://www.facebook.com/reel/1\", views: 902589", t)
        self.assertIn("capturado: 2026-11-14", t)
        self.assertIn("# comentario que no se toca", t)

    def test_abreviadas_no_se_usan(self):
        t, _, _ = actualizar(YAML, [("tiktok", "7629112348766194951", {"views": "80K"})], "2026-11-14")
        self.assertIn("views: 77000", t)

    def test_desconocida_avisa(self):
        _, _, a = actualizar(YAML, [("instagram", "ZZZ", {"views": 1})], "2026-11-14")
        self.assertTrue(any("ZZZ" in x for x in a))


if __name__ == "__main__":
    unittest.main()
