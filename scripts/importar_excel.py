#!/usr/bin/env python3
"""importar_excel.py — Pasa el Excel de métricas del creador a metricas.yaml.

El Excel trae una hoja por formato (Instagram reels, TikTok videos, Instagram stories)
con una fila de encabezados que empieza en "ID contenido" o "ID historia". Las columnas
se leen por nombre, así que el orden puede cambiar.

El Excel no se versiona (contiene datos privados de Insights); solo se guardan las cifras.

Uso:
    python scripts/importar_excel.py klarens-2026 "ruta/al/Informe.xlsx"
"""
from __future__ import annotations

import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

import openpyxl
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.util.config import CAMPAIGNS_DIR  # noqa: E402


def norm(s: object) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


# nombre interno → encabezado del Excel (normalizado)
IG = {"id": "id contenido", "fecha": "fecha publicacion", "nombre": "nombre / descripcion", "url": "enlace", "views": "visualizaciones",
      "reach": "alcance / espectadores", "likes": "me gusta", "comments": "comentarios", "reposts": "reposts",
      "shares": "compartidos", "saves": "guardados", "watch_s": "tiempo promedio reproduccion (s)",
      "new_followers": "nuevos seguidores", "collab": "colaboracion", "precision": "precision",
      "fb_views": "publicacion cruzada facebook", "corte": "fecha corte cifras publicas", "fuente_dato": "fuente"}
TT = {"id": "id contenido", "fecha": "fecha publicacion", "hora": "hora", "nombre": "nombre / descripcion", "url": "enlace", "dur_s": "duracion (s)",
      "views": "visualizaciones", "reach": "alcance / total espectadores", "likes": "me gusta",
      "comments": "comentarios", "shares": "compartidos", "saves": "guardados",
      "new_viewers": "espectadores nuevos %", "returning_viewers": "espectadores recurrentes %",
      "non_followers": "no seguidores %", "followers": "seguidores %", "men": "hombres %", "women": "mujeres %",
      "precision": "precision", "corte": "fecha corte cifras publicas", "fuente_dato": "fuente"}
# Hoja opcional de cumplimiento de KPI (tabla «Detalle normalizado»)
KPI = {"fecha": "fecha publicacion", "creador": "creador", "plataforma": "plataforma", "formato": "formato",
       "tipo": "tipo de accion", "alcance": "alcance verificado", "proyeccion": "proyeccion",
       "alcance_proyectado": "alcance proyectado", "kpi": "kpi alcance", "estado": "estado kpi verificado"}
REQUERIDAS = {"id", "fecha"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ST = {"id": "id historia", "fecha": "fecha", "descripcion": "descripcion", "viewers": "espectadores",
      "views": "visualizaciones", "inter": "interacciones", "likes": "me gusta", "replies": "respuestas",
      "shares": "compartidos", "sticker_taps": "toques en sticker", "link_taps": "toques en enlace",
      "forward": "avances", "back": "retrocesos", "exits": "abandonos", "next_story": "siguiente historia",
      "profile_visits": "visitas al perfil", "new_followers": "nuevos seguidores",
      "followers": "seguidores %", "non_followers": "no seguidores %", "notas": "notas"}


def _fecha(v):
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, str) and ISO.match(v.strip()):
        return v.strip()
    return None


def read_sheet(wb, sheet_name: str, cols: dict[str, str], header_first: str = "id ") -> list[dict]:
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and norm(r[0]).startswith(header_first))
    header = [norm(h) for h in rows[hi]]
    idx = {}
    for key, name in cols.items():
        if name in header:
            idx[key] = header.index(name)
        elif key in REQUERIDAS:
            raise KeyError(f"La hoja «{sheet_name}» no tiene la columna «{name}»")
        else:
            print(f"  aviso: la hoja «{sheet_name}» no tiene «{name}»; queda vacía")
    out = []
    for r in rows[hi + 1:]:
        if not r or not _fecha(r[idx["fecha"]]):
            continue
        rec = {}
        for key in cols:
            if key not in idx:
                rec[key] = None
                continue
            v = r[idx[key]]
            if key == "fecha":
                v = _fecha(v)
            elif isinstance(v, datetime):
                v = v.date().isoformat()
            elif isinstance(v, float) and v.is_integer() and not key.endswith(("%", "_s")) and key not in TT_PCT:
                v = int(v)
            elif v == "":
                v = None
            if key == "url" and v:
                v = str(v).split("?")[0]   # sin parámetros de rastreo del enlace compartido
            rec[key] = v
        out.append(rec)
    return out


TT_PCT = {"new_viewers", "returning_viewers", "non_followers", "followers", "men", "women"}


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    cid, xlsx = sys.argv[1], Path(sys.argv[2])
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    data = {
        "fuente": xlsx.name,
        "importado": date.today().isoformat(),
        "instagram": read_sheet(wb, "Instagram reels", IG),
        "tiktok": read_sheet(wb, "TikTok videos", TT),
        "historias": read_sheet(wb, "Instagram stories", ST),
    }
    if "Cumplimiento KPI" in wb.sheetnames:
        data["kpi"] = read_sheet(wb, "Cumplimiento KPI", KPI, header_first="fecha publicacion")
    out = CAMPAIGNS_DIR / cid / "metricas.yaml"
    out.write_text("# Generado por scripts/importar_excel.py — no editar a mano.\n"
                   + yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"[OK] {out.relative_to(ROOT)}: {len(data['instagram'])} reels, "
          f"{len(data['tiktok'])} videos, {len(data['historias'])} historias"
          + (f", {len(data['kpi'])} filas de KPI" if "kpi" in data else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
