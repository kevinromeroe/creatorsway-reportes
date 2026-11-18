"""Pruebas de cuadre de la campaña por acciones del plan (premier-2026).

Cifras esperadas: Excel «Premier 2026 - Base para informe actualizada» (corte 13 nov 2026; hoja Resumen)
y captura pública del 15 nov 2026 de las 18 publicaciones confirmadas en el scouting.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.metrics_plan import build_data  # noqa: E402
from pipeline.util.config import load_campaign, load_client, load_conversation  # noqa: E402
from tests import foto  # noqa: E402

CID = "premier-2026"


class TestPremier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Foto fija (corte aprobado del 15-nov), para que las actualizaciones automáticas no rompan el cuadre
        cls.met = foto.metricas(CID)
        cls.d = build_data(load_client(), load_campaign(CID), cls.met, load_conversation(CID), foto.publicas(CID))

    def test_importacion_cuadra_con_la_hoja_resumen(self):
        c = self.met["control"]
        A = self.met["acciones"]
        con = [a for a in A if a["cuenta"]]
        self.assertEqual(len(A), 48)
        self.assertEqual(sum(a["kpi"] for a in A), c["kpi"])
        self.assertEqual(sum(a["alcance"] or 0 for a in con), c["alcance"])
        self.assertEqual(sum(a["views"] or 0 for a in con), c["views"])
        self.assertEqual(sum(a["inter"] or 0 for a in con), c["inter"])

    def test_kpi(self):
        k = self.d["kpi"]
        self.assertEqual((k["kpi"], k["alcance"], k["piezas"], k["cumplen"]), (3_555_600, 9_463_783, 32, 15))  # 18-nov: sin la 2.ª réplica de Tatan (excluir)
        self.assertAlmostEqual(k["pct"], 2.6617, places=4)  # 18-nov: KPI sin la fila 84
        self.assertEqual(k["top_pieza"]["r"], 4_987_659)
        self.assertAlmostEqual(k["sin_macro"]["pct"], 1.2589, places=4)  # 18-nov: KPI sin la fila 84

    def test_plan(self):
        p = self.d["plan"]
        self.assertEqual((p["total"], p["con_resultados"], p["faltan"], p["kpi_faltante"]), (47, 32, 15, 1_026_800))  # 18-nov: fila 84 excluida
        self.assertEqual({e["k"]: e["n"] for e in p["estados"]},
                         {"EJECUTADO": 31, "EN APROBACIÓN": 6, "NO EJECUTADO": 9, "PENDIENTE DE REGISTRO": 1})  # 18-nov: fila 84 (SIN ESTADO) excluida

    def test_verificacion(self):
        P = self.d["pieces"]
        self.assertEqual(len(P), 22)
        self.assertEqual(sum(p["verificada"] for p in P), 18)
        self.assertEqual(sorted(p["fila"] for p in P if not p["verificada"]), ["106", "76", "77", "82"])

    def test_cifras_publicas(self):
        t = self.d["totals"]
        self.assertEqual((t["views_ig"], t["views_tt"], t["views_fb"], t["views_st"]),
                         (10_195_242, 14_576_654, 3_323_708, 304_347))
        self.assertEqual(t["inter"], 1_277_101)
        jft = next(p for p in self.d["pieces"] if p["fila"] == "90")
        self.assertEqual((jft["v"], jft["i"], jft["excel_inter"]), (5_700_000, 426_576, 2_869_357))

    def test_creadores_que_cumplen(self):
        cumplen = {c["nombre"] for c in self.d["creadores"] if c["cumple"]}
        self.assertEqual(cumplen, {"Juan Food Time", "Jeison Recetas", "Foggy Repostería", "Tatan Arroyo"})
        self.assertEqual(sum(c["kpi"] for c in self.d["creadores"]), 3_555_600)

    def test_conversacion(self):
        c = self.d["conv"]
        self.assertEqual((c["n"], c["creadores_resp"]), (1_902, 161))
        self.assertEqual((c["tono"]["negativo"], c["tono"]["duda"], c["tono"]["positivo"]), (47, 9, 1))


if __name__ == "__main__":
    unittest.main()
