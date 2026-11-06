"""Pruebas de cuadre: las cifras del reporte deben coincidir con el Excel y con los textos curados.

Correr con:  python -m unittest discover tests
"""
import re
import unittest

from pipeline.metrics import build_data
from pipeline.util.config import load_campaign, load_client, load_conversation, load_metrics


class CuadreKlarens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.camp = load_campaign("klarens-2026")
        cls.d = build_data(load_client(), cls.camp, load_metrics("klarens-2026"), load_conversation("klarens-2026"))
        cls.by = {p["slug"]: p for p in cls.d["pieces"]}

    def test_totales_de_la_campana(self):
        t = self.d["totals"]
        self.assertEqual(t["views_all"], 8_453_580)
        self.assertEqual(t["reach_all"], 5_432_236)
        self.assertEqual(t["inter_all"], 753_509)
        self.assertEqual(t["newf_ig"], 7_384)
        self.assertAlmostEqual(t["er"], 0.1552, places=4)
        self.assertEqual(t["saves"], 217_325)

    def test_redes(self):
        n = self.d["nets"]
        self.assertAlmostEqual(n["ig"]["er"], 0.1668, places=4)
        self.assertAlmostEqual(n["tt"]["er"], 0.1463, places=4)
        self.assertEqual(round(n["tt"]["non_followers"] * 100), 80)

    def test_piezas(self):
        p = self.by["almuerzos-fit"]
        self.assertEqual(p["i"], 542_629)
        self.assertTrue(p["best"])
        self.assertEqual(round(p["share_inter"] * 100), 72)
        self.assertEqual(self.by["suero-costeno"]["lvl"], "baja")
        self.assertEqual(self.by["suero-costeno"]["sv"], 770)
        self.assertEqual([x["lvl"] for x in self.d["pieces"]], ["alta", "alta", "baja", "alta"])

    def test_historias(self):
        st = self.d["storiesTotal"]
        self.assertEqual(st["views"], 693_599)
        self.assertEqual(st["sticker"], 1_683)
        self.assertEqual(st["brand_sticker"], 1_468)   # sin el sticker de @charliepessellini
        self.assertEqual(round(st["top_sticker_share"] * 100), 91)
        self.assertEqual(st["event"]["views"], 291_754)
        self.assertTrue(self.d["stories"][0]["top"])
        self.assertEqual(self.d["tabs"], ["resumen", "instagram", "tiktok"])

    def test_conversacion(self):
        c = self.d["conv"]
        self.assertEqual(c["n"], 1_136)
        self.assertEqual(c["total"], 1_399)
        t = c["tono"]
        self.assertEqual((t["positivo"], t["negativo"], t["duda"]), (61, 29, 51))
        self.assertEqual(t["neg_autenticidad"] + t["neg_salud"], t["negativo"])
        self.assertGreaterEqual(c["opinion_pos"], 0.6)          # el texto dice "2 de cada 3"
        self.assertEqual(c["fit_top_piece"], "20 almuerzos fit")
        self.assertEqual(round(c["fit_top_share"] * 100), 97)
        self.assertEqual(c["marca_top_piece"], "Suero costeño")
        self.assertEqual(c["destacados"][0]["tema"], "Humor y detalles del video")

    def test_insights_de_redes(self):
        ig, tt = self.d["insIg"], self.d["insTt"]
        self.assertEqual(round(ig["top_share_views"] * 100), 56)
        self.assertEqual(round(ig["er_diff_pts"], 1), 2.0)
        self.assertEqual(ig["comments"], 768)
        self.assertTrue(ig["watch_best_is_newf_best"])
        self.assertEqual(round(tt["reach_vs_other"] * 100), 30)
        self.assertEqual(tt["inter_vs_other"], 48_948)
        self.assertEqual(tt["wins_vs_other"], ["Suero costeño"])
        self.assertTrue(tt["shortest_is_top"] and tt["longest_is_low"])

    def test_insights_del_resumen(self):
        i = self.d["insights"]
        self.assertEqual(round(i["views_per_reach"], 1), 1.6)
        self.assertEqual(round(i["tt_reach_share"] * 100), 57)
        self.assertEqual(round(i["newf_best_share"] * 100), 92)
        self.assertEqual(round(i["top_vs_second"], 1), 2.7)
        self.assertEqual(i["ig_wins_er"], 3)
        self.assertTrue(i["low_is_last_in_both"])

    def test_textos_curados_coinciden_con_las_cifras(self):
        """Cada porcentaje escrito a mano en las notas debe salir de los datos."""
        p = self.by
        notas = {
            "almuerzos-fit": [round(p["almuerzos-fit"]["share_inter"] * 100)],
            "cheesecake": [round(p["cheesecake"]["er"] * 100, 1)],
            "suero-costeno": [round(p["suero-costeno"]["er"] * 100, 1)],
            "ossobuco": [round(p["ossobuco"]["er"] * 100, 1)],
        }
        for slug, esperados in notas.items():
            citados = [float(x.replace(",", ".")) for x in re.findall(r"(\d+(?:,\d)?) %", p[slug]["nota"])]
            self.assertEqual(citados, esperados, slug)
        h = [round(x["v"] * 100, 1) for x in self.d["hallazgos"]]
        self.assertEqual(h, [72.4, 29.0, 4.9])
        self.assertIn("80 %", self.camp["textos"]["redes"]["texto"])
        self.assertIn("16,7 % frente a 14,6 %", self.camp["textos"]["redes"]["texto"])


if __name__ == "__main__":
    unittest.main()
