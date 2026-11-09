#!/usr/bin/env python3
"""actualizar_excel.py — Escribe las cifras públicas dentro del Excel de la campaña.

El Excel de la campaña es la fuente única y continua del dato:
  - lo que se ve en línea (visualizaciones, me gusta, comentarios, compartidos; guardados y duración en
    TikTok; reproducciones en Facebook de la publicación cruzada; fecha real de publicación) se actualiza
    en el Excel con la captura de config/campanas/<id>/publicas.yaml;
  - lo que no es público (alcance, impresiones, guardados y reposts de Instagram, historias, KPI) se
    conserva tal como viene del Excel.

Cada celda que cambia guarda su valor anterior en un comentario de Excel, la columna «Fuente» dice de
dónde sale cada cifra y «Fecha corte cifras públicas» registra la fecha de captura. Antes de escribir se
guarda un respaldo del Excel en la subcarpeta `respaldo/`.

Uso (PowerShell, la ruta tiene tildes):
    python scripts/actualizar_excel.py canola-2026 "<ruta del Excel>"
    python scripts/importar_excel.py   canola-2026 "<ruta del Excel>"
"""
from __future__ import annotations

import re
import shutil
import sys
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.comments import Comment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.util.config import load_campaign, load_public  # noqa: E402
from scripts.importar_excel import norm  # noqa: E402

CORTE = "Fecha corte cifras públicas"
AUTOR = "Datalítica"

# columna del Excel (normalizada) → campo de publicas.yaml
IG = {"visualizaciones": "views", "me gusta": "likes", "comentarios": "comments", "compartidos": "shares",
      "publicacion cruzada facebook": "fb_views"}
TT = {"duracion (s)": "dur_s", "visualizaciones": "views", "me gusta": "likes", "comentarios": "comments",
      "compartidos": "shares", "guardados": "saves"}
FUENTE = {
    "ig": "Públicas Datalítica {f}: visualizaciones (solo Instagram), me gusta, comentarios, compartidos y "
          "Facebook · Tráfico campañas Aura: alcance, reposts y guardados",
    "tt": "Públicas Datalítica {f}: duración, visualizaciones, me gusta, comentarios, compartidos y guardados · "
          "Tráfico campañas Aura: alcance y audiencia",
}


def _header(ws):
    for r in ws.iter_rows(min_row=1, max_row=15):
        if r[0].value and norm(r[0].value).startswith("id contenido"):
            return r[0].row, {norm(c.value): c.column for c in r if c.value}
    raise ValueError(f"Sin encabezados en {ws.title}")


def _col(ws, hrow: int, cols: dict, name: str) -> int:
    """Columna por nombre; si no existe la crea al final copiando el estilo del encabezado anterior."""
    key = norm(name)
    if key in cols:
        return cols[key]
    c = ws.max_column + 1
    src, dst = ws.cell(hrow, c - 1), ws.cell(hrow, c, name)
    for a in ("font", "fill", "border", "alignment", "number_format"):
        setattr(dst, a, copy(getattr(src, a)))
    ws.column_dimensions[dst.column_letter].width = 16
    cols[key] = c
    return c


def _set(cell, nuevo, cambios: list, ref: str) -> None:
    viejo = cell.value
    if isinstance(viejo, float) and viejo.is_integer():
        viejo = int(viejo)
    if viejo == nuevo:
        return
    cell.value = nuevo
    cell.comment = Comment(f"Antes: {'vacío' if viejo is None else viejo} (Tráfico campañas Aura). "
                           f"Actualizado con la cifra pública.", AUTOR)
    cambios.append((ref, viejo, nuevo))


def main() -> int:
    cid, xlsx = sys.argv[1], Path(sys.argv[2])
    camp, pub = load_campaign(cid), load_public(cid)
    fecha = str(pub["capturado"])
    piezas = {p["excel"]: p for p in camp["piezas"]}

    respaldo = xlsx.parent / "respaldo" / f"{xlsx.stem} (antes de {fecha}).xlsx"
    respaldo.parent.mkdir(exist_ok=True)
    if not respaldo.exists():
        shutil.copy2(xlsx, respaldo)

    wb = openpyxl.load_workbook(xlsx)
    cambios: list = []
    fechas: dict[tuple, str] = {}  # (creador en Excel, plataforma, fecha vieja) → fecha real
    for hoja, red, mapa in (("Instagram reels", "ig", IG), ("TikTok videos", "tt", TT)):
        ws = wb[hoja]
        hrow, cols = _header(ws)
        c_corte = _col(ws, hrow, cols, CORTE)
        for r in range(hrow + 1, ws.max_row + 1):
            eid = ws.cell(r, 1).value
            if not eid or eid not in piezas:
                continue
            p = piezas[eid]
            pb = pub["instagram" if red == "ig" else "tiktok"][str(p["codigo"])]
            for col, campo in mapa.items():
                if campo in pb:
                    _set(ws.cell(r, cols[col]), int(pb[campo]), cambios, f"{hoja} {eid} {col}")
            c_fecha = ws.cell(r, cols["fecha publicacion"])
            real = str(pb["fecha"])
            if str(c_fecha.value) != real:
                fechas[(red, str(c_fecha.value))] = real
                _set(c_fecha, real, cambios, f"{hoja} {eid} fecha")
            ws.cell(r, cols["fuente"]).value = FUENTE[red].format(f=fecha)
            ws.cell(r, c_corte).value = fecha

    # La hoja de KPI une cada fila por fecha: si se corrigió una fecha, se corrige también allí.
    if fechas:
        ws = wb["Cumplimiento KPI"]
        hrow = next(c.row for row in ws.iter_rows(max_row=60) for c in row[:1]
                    if c.value and norm(c.value) == "fecha publicacion")
        cols = {norm(c.value): c.column for c in ws[hrow] if c.value}
        plat = {"Instagram": "ig", "TikTok": "tt"}
        for r in range(hrow + 1, ws.max_row + 1):
            c = ws.cell(r, cols["fecha publicacion"])
            red = plat.get(ws.cell(r, cols["plataforma"]).value)
            fmt = str(ws.cell(r, cols["formato"]).value or "")
            if red and not fmt.startswith("Historia") and (red, str(c.value)) in fechas:
                _set(c, fechas[(red, str(c.value))], cambios, f"Cumplimiento KPI fila {r} fecha")

    wb.save(xlsx)
    print(f"[OK] {len(cambios)} celdas actualizadas en {xlsx.name} · respaldo: {respaldo.name}")
    for ref, a, b in cambios:
        print(f"  {ref}: {a} → {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
