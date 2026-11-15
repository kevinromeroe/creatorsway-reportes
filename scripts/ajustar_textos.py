#!/usr/bin/env python3
"""ajustar_textos.py: pone al día los porcentajes que citan los textos curados cuando cambian las cifras.

Uso (desde la raíz del repo): python scripts/ajustar_textos.py [--prueba]

Decisión de Kevin (14-nov-2026): en la actualización automática, los porcentajes de los textos se actualizan
solos. Solo cambia el NÚMERO dentro del mismo texto («10,6 %» → «10,3 %»); la redacción no se toca.
Cada texto sabe de qué dato sale su porcentaje (TEXTOS); la prueba tests/test_metrics.py::TextosKlarensHoy
verifica después que todo cuadre con los datos de hoy. Imprime cada cambio.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.metrics import build_data  # noqa: E402
from pipeline.util.config import (CAMPAIGNS_DIR, load_campaign, load_client, load_conversation,  # noqa: E402
                                  load_metrics, load_public)

# campaña → slug de la pieza → (dato de la pieza, decimales). Mismo origen que la prueba de textos curados.
TEXTOS = {
    "klarens-2026": {
        "almuerzos-fit": ("share_inter", 0),
        "cheesecake": ("er", 1),
        "suero-costeno": ("er", 1),
        "ossobuco": ("er", 1),
    },
}
PCT = re.compile(r"\d+(?:,\d)? %")


def fmt(v: float, dec: int) -> str:
    return (f"{v * 100:.{dec}f}".replace(".", ",")) + " %"


def ajustar(cid: str, prueba: bool) -> list[str]:
    camp = load_campaign(cid)
    d = build_data(load_client(), camp, load_metrics(cid), load_conversation(cid), load_public(cid))
    piezas = {p["slug"]: p for p in d["pieces"]}
    f = CAMPAIGNS_DIR / cid / "campana.yaml"
    t = f.read_text(encoding="utf-8")
    cambios = []
    for slug, (dato, dec) in TEXTOS[cid].items():
        a = t.index(f"- slug: {slug}\n")
        nota = t.index("nota:", a)
        fin = t.find("\n  - ", nota)
        fin = len(t) if fin < 0 else fin
        bloque = t[nota:fin]
        m = PCT.search(bloque)
        if not m:
            continue
        nuevo = fmt(piezas[slug][dato], dec)
        if m.group(0) != nuevo:
            cambios.append(f"{cid} {slug}: «{m.group(0)}» → «{nuevo}»")
            bloque = bloque[:m.start()] + nuevo + bloque[m.end():]
            t = t[:nota] + bloque + t[fin:]
    if cambios and not prueba:
        f.write_text(t, encoding="utf-8")
    return cambios


if __name__ == "__main__":
    out = [c for cid in TEXTOS for c in ajustar(cid, "--prueba" in sys.argv)]
    print("\n".join(out) or "Textos al día.")
