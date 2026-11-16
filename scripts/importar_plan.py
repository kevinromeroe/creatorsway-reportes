#!/usr/bin/env python3
"""importar_plan.py — Pasa a metricas.yaml un Excel de campaña organizado por acciones del plan.

Formato (ej. «Premier 2026 - Base para informe actualizada.xlsx»): la hoja «Detalle contenidos» tiene
una fila por acción contratada (también las no ejecutadas), con encabezados
  Origen fila · Talento · Plataforma · Contenido · Fecha publicación · Estado · KPI alcance ·
  Alcance logrado · Views · Interacciones · % KPI alcanzado · Cuenta para resultados · Observación / ajuste
y la hoja «Resumen» trae los totales de control (KPI, alcance, views, interacciones).

Las acciones sin número de fila (p. ej. «Escenario 3», agregadas para completar el plan) reciben un id
«E3-<n>». Las fechas inválidas del Excel (1970) se dejan vacías: la fecha real sale de la captura pública.

Uso (PowerShell, la ruta tiene tildes):
    python scripts/importar_plan.py premier-2026 "<ruta del Excel>"
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import openpyxl
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.util.config import CAMPAIGNS_DIR  # noqa: E402
from scripts.importar_excel import norm  # noqa: E402

COLS = {"fila": "origen fila", "talento": "talento", "plataforma": "plataforma", "formato": "contenido",
        "fecha": "fecha publicacion", "estado": "estado", "kpi": "kpi alcance", "alcance": "alcance logrado",
        "views": "views", "inter": "interacciones", "cuenta": "cuenta para resultados", "nota": "observacion / ajuste"}


def _num(v):
    if v is None or v == "":
        return None
    return int(v) if float(v).is_integer() else float(v)


def _fecha(v):
    if isinstance(v, datetime):
        v = v.date()
    if isinstance(v, date) and v.year >= 2020:
        return v.isoformat()
    return None


def main() -> int:
    cid, xlsx = sys.argv[1], Path(sys.argv[2])
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    ws = wb["Detalle contenidos"]
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and norm(r[0]) == "origen fila")
    head = [norm(h) for h in rows[hi]]
    idx = {k: head.index(v) for k, v in COLS.items()}
    acciones, extra = [], 0
    for r in rows[hi + 1:]:
        if not r or not r[idx["talento"]]:
            continue
        g = lambda k: r[idx[k]]  # noqa: E731
        fila = g("fila")
        if isinstance(fila, (int, float)):
            fid = str(int(fila))
        else:
            extra += 1
            fid = f"E3-{extra}"
        acciones.append({
            "fila": fid, "origen": str(fila), "talento": str(g("talento")).strip(), "plataforma": g("plataforma"),
            "formato": str(g("formato")).strip(), "fecha_excel": _fecha(g("fecha")), "estado": str(g("estado")).strip(),
            "kpi": _num(g("kpi")), "alcance": _num(g("alcance")), "views": _num(g("views")), "inter": _num(g("inter")),
            "cuenta": str(g("cuenta")).strip().upper() in ("SÍ", "SI"), "nota": g("nota"),
        })
    res = wb["Resumen"]
    vals = [c for c in next(r for r in res.iter_rows(values_only=True) if r and isinstance(r[0], (int, float)))]
    control = {"kpi": _num(vals[0]), "alcance": _num(vals[2]), "views": _num(vals[6]), "inter": _num(vals[8])}
    out = CAMPAIGNS_DIR / cid / "metricas.yaml"
    data = {"fuente": xlsx.name, "importado": date.today().isoformat(), "control": control, "acciones": acciones}
    out.write_text("# Generado por scripts/importar_plan.py — no editar a mano.\n"
                   + yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    con = [a for a in acciones if a["cuenta"]]
    chk = {"kpi": sum(a["kpi"] or 0 for a in acciones), "alcance": sum(a["alcance"] or 0 for a in con),
           "views": sum(a["views"] or 0 for a in con), "inter": sum(a["inter"] or 0 for a in con)}
    print(f"[OK] {out.relative_to(ROOT)}: {len(acciones)} acciones, {len(con)} con resultados")
    for k in control:
        print(f"  {k}: detalle {chk[k]:,} · resumen {control[k]:,} {'✓' if chk[k] == control[k] else '✗'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
