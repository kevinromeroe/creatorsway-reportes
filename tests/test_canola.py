"""Pruebas de cuadre de la campaña con varios creadores (canola-2026).

Las cifras esperadas salen del Excel de la campaña (hoja Cumplimiento KPI) y de la captura
pública del 9 de noviembre de 2026 (publicas.yaml). Si se actualiza la captura, se actualizan aquí.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.metrics_creadores import build_data  # noqa: E402
from pipeline.util.config import load_campaign, load_client, load_conversation, load_metrics, load_public  # noqa: E402

CID = "canola-2026"


def data():
    return build_data(load_client(), load_campaign(CID), load_metrics(CID), load_conversation(CID), load_public(CID))


class TestCanola(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = data()

    def test_kpi_cuadra_con_el_excel(self):
        k = self.d["kpi"]
        self.assertEqual((k["kpi"], k["alcance"], k["piezas"], k["cumplen"]), (760_500, 1_110_960, 27, 11))
        self.assertAlmostEqual(k["pct"], 1.4608, places=4)
        self.assertEqual((k["sin_macro"]["kpi"], k["sin_macro"]["alcance"]), (748_500, 738_852))
        self.assertAlmostEqual(k["sin_macro"]["pct"], 0.9871, places=4)
        self.assertEqual((k["bonificado_alcance"], k["bonificado_piezas"]), (156_978, 3))
        self.assertEqual(k["proyectado"], 1_179_081)

    def test_alcance_por_pieza_igual_a_la_hoja_de_kpi(self):
        self.assertEqual(self.d["totals"]["reach_all"], self.d["kpi"]["alcance_verificado"])
        self.assertEqual(self.d["kpi"]["alcance_verificado"], 1_267_938)

    def test_visualizaciones_publicas(self):
        t = self.d["totals"]
        self.assertEqual((t["views_ig"], t["views_tt"], t["views_fb"], t["views_st"]), (1_394_954, 195_195, 55_537, 267_638))
        self.assertEqual(t["views_all"], 1_913_324)

    def test_interacciones_y_tasa(self):
        t, n = self.d["totals"], self.d["nets"]
        self.assertEqual((n["ig"]["i"], n["tt"]["i"], t["inter"]), (128_594, 20_093, 148_687))
        self.assertAlmostEqual(t["er"], 148_687 / 1_037_913)

    def test_creadores_que_cumplen(self):
        cumplen = {c["nombre"] for c in self.d["creadores"] if c["cumple"]}
        self.assertEqual(cumplen, {"Jenn Yummy", "Cocina Anto", "Susana Gómez", "Naty Farah", "Juliana Cocina"})
        self.assertEqual(len(self.d["creadores"]), 14)
        self.assertEqual(sum(c["kpi"] for c in self.d["creadores"]), self.d["kpi"]["kpi"])

    def test_cumplimiento_por_formato(self):
        i = self.d["insights"]
        self.assertEqual((i["ig_cumplen"], i["n_ig_kpi"], i["tt_cumplen"], i["n_tt_kpi"], i["st_cumplen"], i["n_st_kpi"]),
                         (5, 17, 3, 4, 3, 6))

    def test_conversacion(self):
        c = self.d["conv"]
        self.assertEqual((c["n"], c["creadores_resp"], c["total"]), (546, 186, 761))
        self.assertEqual((c["tono"]["negativo"], c["tono"]["duda"], c["tono"]["positivo"]), (42, 31, 4))
        self.assertEqual(c["crit_top"]["creador"], "Jenn Yummy")


if __name__ == "__main__":
    unittest.main()
