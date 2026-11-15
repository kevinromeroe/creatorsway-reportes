#!/usr/bin/env python3
"""actualizar_publicas.py: aplica las lecturas del día a config/campanas/<id>/publicas.yaml (CreatorsWay).

Uso (desde la raíz del repo):
    python scripts/actualizar_publicas.py <lista.json> <lecturas.json> [--prueba]

- lista.json la arma ~/ops/influencers/lista.py creatorsway: cada publicación trae `codigo` (código del reel
  o id del video, o una clave propia cuando el enlace es corto), `campana`, `seccion` (instagram | tiktok) y
  `clave` (la clave de esa publicación en publicas.yaml: código o fecha).
- lecturas.json: {"fecha", "publicaciones": {codigo: {views, likes, comments, shares, saves}}}.

Reglas (las mismas de LCI y Polar, validadas por Kevin el 13-nov-2026):
1. Una cifra solo se actualiza si SUBE; si la lectura es menor, se conserva la anterior.
2. Nada se borra; lo que no se leyó queda igual. El resto de la línea (fecha, cuenta, coautor, fb_views…)
   no se toca. Facebook no se actualiza aquí.
3. Las vistas de Instagram por Apify son solo de Instagram (comparadas con ig_play_count el 14-nov-2026 en las
   18 piezas de Canola). Apify no da compartidos de Instagram: se conservan.
Después: python -m scripts.actualizar_excel <id> "<Excel>" e importar_excel.py (docs/RUNBOOK.md).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPOS = ("views", "likes", "comments", "shares", "saves")


def entero(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().replace(",", "")
    m = re.fullmatch(r"([\d.]+)\s*([KkMm]?)", s)
    if not m:
        return None
    n = float(m.group(1)) * {"": 1, "k": 1e3, "m": 1e6}[m.group(2).lower()]
    return None if m.group(2) else int(n)   # cifras abreviadas no se usan (no son exactas)


def actualizar(texto: str, items: list[tuple[str, str, dict]], fecha: str):
    """items = [(seccion, clave, lectura)]. Devuelve (texto_nuevo, cambios, avisos)."""
    cambios, avisos = [], []
    lineas = texto.split("\n")
    seccion = None
    pend = {(s, str(k)): l for s, k, l in items}
    for i, ln in enumerate(lineas):
        m = re.match(r"^(\w+):\s*$", ln)
        if m:
            seccion = m.group(1)
            continue
        m = re.match(r'^(  )("?)([\w.:-]+)\2: \{(.*)\}\s*$', ln)
        if not m or (seccion, m.group(3)) not in pend:
            continue
        lect, cuerpo = pend.pop((seccion, m.group(3))), m.group(4)
        for campo in CAMPOS:
            nuevo = entero(lect.get(campo))
            mm = re.search(rf"\b{campo}: (\d+)", cuerpo)
            if nuevo is None or not mm:
                continue
            antes = int(mm.group(1))
            if nuevo > antes:
                cuerpo = cuerpo[:mm.start(1)] + str(nuevo) + cuerpo[mm.end(1):]
                cambios.append(f"{m.group(3)} {campo}: {antes} → {nuevo}")
            elif nuevo < antes:
                cambios.append(f"{m.group(3)} {campo}: se conserva {antes} (lectura menor: {nuevo})")
        lineas[i] = f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(2)}: {{{cuerpo}}}"
    for (s, k) in pend:
        avisos.append(f"{s} {k}: no está en publicas.yaml")
    texto = "\n".join(lineas)
    texto = re.sub(r"^capturado: .*$", f"capturado: {fecha}", texto, count=1, flags=re.M)
    return texto, cambios, avisos


def main() -> None:
    lista = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    lect = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    prueba = "--prueba" in sys.argv
    pubs = lect.get("publicaciones") or {}
    por_campana: dict[str, list] = {}
    for p in lista["publicaciones"]:
        if p["codigo"] in pubs:
            por_campana.setdefault(p["campana"], []).append((p["seccion"], p["clave"], pubs[p["codigo"]]))
    for cid, items in sorted(por_campana.items()):
        f = ROOT / "config" / "campanas" / cid / "publicas.yaml"
        nuevo, cambios, avisos = actualizar(f.read_text(encoding="utf-8"), items, lect["fecha"])
        print(f"== {cid}")
        print("\n".join(cambios) or "Sin cambios.")
        for a in avisos:
            print("AVISO", a)
        if avisos:
            sys.exit(f"{cid}: publicaciones que no están en publicas.yaml")
        if not prueba:
            f.write_text(nuevo, encoding="utf-8")


if __name__ == "__main__":
    main()
