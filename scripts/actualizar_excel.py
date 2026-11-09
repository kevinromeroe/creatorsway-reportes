#!/usr/bin/env python3
"""actualizar_excel.py — Escribe las cifras públicas dentro del Excel de la campaña.

El Excel de la campaña es la fuente única y continua del dato:
  - lo que se ve en línea (visualizaciones, me gusta, comentarios, compartidos; guardados y duración en
    TikTok; reproducciones y reacciones de Facebook; fecha real de publicación) se actualiza en el Excel
    con la captura de config/campanas/<id>/publicas.yaml;
  - lo que no es público (alcance, impresiones, guardados y reposts de Instagram, tiempo de reproducción,
    seguidores nuevos, audiencia, historias, KPI) se conserva tal como viene del Excel.

Cada celda que cambia guarda su valor anterior en un comentario de Excel, la columna «Fuente» dice de
dónde sale cada cifra y «Fecha corte cifras públicas» registra la fecha de captura. Antes de escribir se
guarda un respaldo del Excel en la subcarpeta `respaldo/`.

Cómo se une cada fila con su cifra pública:
  - campaña con varios creadores (`tipo: creadores`): por el ID de la fila (campana.yaml → piezas → excel)
    y el código del reel o id del video;
  - campaña de un creador: por la fecha de publicación (una pieza por día).

Facebook:
  - varios creadores: las reproducciones de la publicación cruzada van en «Publicación cruzada Facebook»
    de la hoja de reels;
  - un creador con página propia en Facebook: se escribe (o crea) la hoja «Facebook reels», con
    visualizaciones, reacciones, comentarios, compartidos y enlace de cada reel.

Uso (PowerShell, la ruta tiene tildes):
    python -m scripts.actualizar_excel <id> "<ruta del Excel>"
    python scripts/importar_excel.py   <id> "<ruta del Excel>"
"""
from __future__ import annotations

import shutil
import sys
from copy import copy
from datetime import date, datetime
from pathlib import Path

import openpyxl
from openpyxl.comments import Comment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.util.config import load_campaign, load_public  # noqa: E402
from scripts.importar_excel import norm  # noqa: E402

CORTE = "Fecha corte cifras públicas"
AUTOR = "Datalítica"
FB_HOJA = "Facebook reels"

# columna del Excel (normalizada) → campo de publicas.yaml
IG = {"visualizaciones": "views", "me gusta": "likes", "comentarios": "comments", "compartidos": "shares"}
IG_FB = {"publicacion cruzada facebook": "fb_views"}   # solo campañas con varios creadores (columna numérica)
TT = {"duracion (s)": "dur_s", "visualizaciones": "views", "me gusta": "likes", "comentarios": "comments",
      "compartidos": "shares", "guardados": "saves"}
FB = {"visualizaciones": "views", "reacciones": "likes", "comentarios": "comments", "compartidos": "shares"}
FB_COLS = ["ID contenido", "Fecha publicación", "Nombre / descripción", "Enlace", "Plataforma", "Formato",
           "Visualizaciones", "Reacciones", "Comentarios", "Compartidos", "Precisión", "Fuente", CORTE]
FUENTE = {
    "ig": "Públicas Datalítica {f}: visualizaciones (solo Instagram), me gusta, comentarios y compartidos{fb} · "
          "{orig}: alcance, reposts, guardados y demás",
    "tt": "Públicas Datalítica {f}: duración, visualizaciones, me gusta, comentarios, compartidos y guardados · "
          "{orig}: alcance y audiencia",
    "fb": "Públicas Datalítica {f}: página de Facebook del creador (visualizaciones de la API de Instagram; "
          "reacciones, comentarios y compartidos del reel)",
}


def _iso(v) -> str:
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def _header(ws):
    for r in ws.iter_rows(min_row=1, max_row=15):
        if r[0].value and norm(r[0].value).startswith("id contenido"):
            return r[0].row, {norm(c.value): c.column for c in r if c.value}
    raise ValueError(f"Sin encabezados en {ws.title}")


def _style(src, dst) -> None:
    for a in ("font", "fill", "border", "alignment", "number_format"):
        setattr(dst, a, copy(getattr(src, a)))


def _col(ws, hrow: int, cols: dict, name: str) -> int:
    """Columna por nombre; si no existe la crea al final copiando el estilo del encabezado anterior."""
    key = norm(name)
    if key in cols:
        return cols[key]
    c = ws.max_column + 1
    dst = ws.cell(hrow, c, name)
    _style(ws.cell(hrow, c - 1), dst)
    ws.column_dimensions[dst.column_letter].width = 16
    cols[key] = c
    return c


def _set(cell, nuevo, cambios: list, ref: str, origen: str) -> None:
    viejo = cell.value
    if isinstance(viejo, float) and viejo.is_integer():
        viejo = int(viejo)
    if isinstance(viejo, (datetime, date)):
        viejo = _iso(viejo)
    if viejo == nuevo:
        return
    cell.value = nuevo
    cell.comment = Comment(f"Antes: {'vacío' if viejo is None else viejo} ({origen}). "
                           f"Actualizado con la cifra pública.", AUTOR)
    cambios.append((ref, viejo, nuevo))


def _hoja_fb(wb, ig):
    """Hoja «Facebook reels» con el formato de la hoja de reels de Instagram (se crea si no existe)."""
    if FB_HOJA in wb.sheetnames:
        return wb[FB_HOJA]
    ws = wb.create_sheet(FB_HOJA, wb.sheetnames.index("TikTok videos") + 1)
    hrow, _ = _header(ig)
    titulo = str(ig.cell(1, 1).value or "").split("—")[0].strip()
    ws.cell(1, 1, f"{titulo} — Facebook Reels" if titulo else FB_HOJA)
    ws.cell(2, 1, "Fuente: cifras públicas de la página de Facebook del creador, leídas por Datalítica "
                  "(publicación cruzada de los reels de Instagram). Facebook no publica alcance ni guardados.")
    for r in (1, 2):
        _style(ig.cell(r, 1), ws.cell(r, 1))
    for i, name in enumerate(FB_COLS, 1):
        _style(ig.cell(hrow, min(i, ig.max_column)), ws.cell(hrow, i, name))
        ws.column_dimensions[ws.cell(hrow, i).column_letter].width = ig.column_dimensions[
            ig.cell(hrow, min(i, ig.max_column)).column_letter].width or 16
    return ws


def main() -> int:
    cid, xlsx = sys.argv[1], Path(sys.argv[2])
    camp, pub = load_campaign(cid), load_public(cid)
    multi = camp.get("tipo") == "creadores"
    fecha = str(pub["capturado"])
    piezas = {p["excel"]: p for p in camp.get("piezas", [])} if multi else {}

    respaldo = xlsx.parent / "respaldo" / f"{xlsx.stem} (antes de {fecha}).xlsx"
    respaldo.parent.mkdir(exist_ok=True)
    if not respaldo.exists():
        shutil.copy2(xlsx, respaldo)

    wb = openpyxl.load_workbook(xlsx)
    cambios: list = []
    fechas: dict[tuple, str] = {}  # (red, fecha vieja) → fecha real
    origen = {}
    for hoja, red, mapa in (("Instagram reels", "ig", {**IG, **(IG_FB if multi else {})}), ("TikTok videos", "tt", TT)):
        ws = wb[hoja]
        hrow, cols = _header(ws)
        c_corte = _col(ws, hrow, cols, CORTE)
        datos = pub["instagram" if red == "ig" else "tiktok"]
        for r in range(hrow + 1, ws.max_row + 1):
            eid = ws.cell(r, 1).value
            if not eid:
                continue
            f_excel = _iso(ws.cell(r, cols["fecha publicacion"]).value)
            if multi:
                if eid not in piezas:
                    continue
                pb = datos[str(piezas[eid]["codigo"])]
            else:
                pb = datos.get(f_excel) or datos.get(date.fromisoformat(f_excel))
                if pb is None:
                    continue
            orig = str(ws.cell(r, cols["fuente"]).value or "Excel")
            orig = origen.setdefault((red, eid), orig if not orig.startswith("Públicas Datalítica") else orig.split("· ")[-1].split(":")[0])
            for col, campo in mapa.items():
                if campo in pb and col in cols:
                    _set(ws.cell(r, cols[col]), int(pb[campo]), cambios, f"{hoja} {eid} {col}", orig)
            real = str(pb.get("fecha") or f_excel)
            if real != f_excel:
                fechas[(red, f_excel)] = real
                _set(ws.cell(r, cols["fecha publicacion"]), real, cambios, f"{hoja} {eid} fecha", orig)
            ws.cell(r, cols["fuente"]).value = FUENTE[red].format(
                f=fecha, orig=orig, fb=" y reproducciones en Facebook" if multi else "")
            ws.cell(r, c_corte).value = fecha

    # Facebook como red propia (campaña de un creador con página de Facebook)
    if not multi and pub.get("facebook"):
        ig = wb["Instagram reels"]
        hrow_ig, cols_ig = _header(ig)
        ws = _hoja_fb(wb, ig)
        hrow, cols = _header(ws)
        filas = {_iso(ws.cell(r, 2).value): r for r in range(hrow + 1, ws.max_row + 1) if ws.cell(r, 1).value}
        ig_rows = {_iso(ig.cell(r, cols_ig["fecha publicacion"]).value): r for r in range(hrow_ig + 1, ig.max_row + 1)
                   if ig.cell(r, 1).value}
        for f, pb in sorted(pub["facebook"].items(), key=lambda kv: str(kv[0])):
            f = _iso(f)
            r = filas.get(f)
            if r is None:
                r = max([hrow, *filas.values()]) + 1
                filas[f] = r
                src = ig_rows.get(f)
                eid = str(ig.cell(src, 1).value).replace("IG-", "FB-", 1) if src else f"FB-{f}"
                nombre = ig.cell(src, cols_ig["nombre / descripcion"]).value if src else None
                for c, v in zip(range(1, 7), (eid, f, nombre, None, "Facebook", "Reel")):
                    ws.cell(r, c, v)
                if src:
                    for c in range(1, len(FB_COLS) + 1):
                        _style(ig.cell(src, min(c, ig.max_column)), ws.cell(r, c))
                cambios.append((f"{FB_HOJA} {eid}", None, "fila nueva"))
            eid = ws.cell(r, 1).value
            ws.cell(r, cols["enlace"]).value = pb.get("url")
            for col, campo in FB.items():
                _set(ws.cell(r, cols[col]), int(pb[campo]), cambios, f"{FB_HOJA} {eid} {col}", "vacío")
            ws.cell(r, cols["precision"]).value = (
                "Reacciones aproximadas: Facebook las abrevia desde 10 mil" if pb.get("likes_aprox") else "Exacto")
            ws.cell(r, cols["fuente"]).value = FUENTE["fb"].format(f=fecha)
            ws.cell(r, cols[norm(CORTE)]).value = fecha

    # La hoja de KPI une cada fila por fecha: si se corrigió una fecha, se corrige también allí.
    if fechas and "Cumplimiento KPI" in wb.sheetnames:
        ws = wb["Cumplimiento KPI"]
        hrow = next(c.row for row in ws.iter_rows(max_row=60) for c in row[:1]
                    if c.value and norm(c.value) == "fecha publicacion")
        cols = {norm(c.value): c.column for c in ws[hrow] if c.value}
        plat = {"Instagram": "ig", "TikTok": "tt"}
        for r in range(hrow + 1, ws.max_row + 1):
            c = ws.cell(r, cols["fecha publicacion"])
            red = plat.get(ws.cell(r, cols["plataforma"]).value)
            fmt = str(ws.cell(r, cols["formato"]).value or "")
            if red and not fmt.startswith("Historia") and (red, _iso(c.value)) in fechas:
                _set(c, fechas[(red, _iso(c.value))], cambios, f"Cumplimiento KPI fila {r} fecha", "Excel")

    wb.save(xlsx)
    print(f"[OK] {len(cambios)} celdas actualizadas en {xlsx.name} · respaldo: {respaldo.name}")
    for ref, a, b in cambios:
        print(f"  {ref}: {a} → {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
