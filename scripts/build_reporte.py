#!/usr/bin/env python3
"""build_reporte.py — Genera el reporte web de cada campaña.

Lee config/cliente.yaml y config/campanas/<id>/{campana,metricas}.yaml, calcula las
cifras con pipeline/metrics.py y escribe <id>/index.html desde templates/reporte.html.
La raíz del sitio (index.html) muestra directamente la campaña de `portada`
(config/cliente.yaml) o, si no está definida, la última; así el enlace que se comparte
es solo el dominio.

Uso:
    python scripts/build_reporte.py                  # todas las campañas
    python scripts/build_reporte.py klarens-2026     # una campaña
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.metrics import build_data  # noqa: E402
from pipeline.util.config import PROJECT_ROOT, campaign_ids, load_campaign, load_client, load_metrics  # noqa: E402
from pipeline.util.log import get_logger  # noqa: E402

log = get_logger("build_reporte")
TEMPLATE = PROJECT_ROOT / "templates" / "reporte.html"
MARKER = "/*__DATA__*/null"


def render(data: dict, pdf_base: str) -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    if MARKER not in html:
        raise RuntimeError(f"La plantilla no tiene el marcador {MARKER}")
    payload = json.dumps({**data, "pdfBase": pdf_base}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return html.replace(MARKER, payload)


def build(campaign_id: str, client: dict) -> dict:
    data = build_data(client, load_campaign(campaign_id), load_metrics(campaign_id))
    out = PROJECT_ROOT / campaign_id / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render(data, "pdf"), encoding="utf-8")
    log.info("reporte_ok", extra={"campaign": campaign_id, "tabs": data["tabs"],
                                   "views_all": data["totals"]["views_all"]})
    return data


def write_root(campaign_id: str, data: dict) -> None:
    """La raíz muestra el reporte de portada; sus PDF siguen en <campaña>/pdf/."""
    (PROJECT_ROOT / "index.html").write_text(render(data, f"{campaign_id}/pdf"), encoding="utf-8")
    log.info("portada_ok", extra={"campaign": campaign_id})


def main() -> int:
    client = load_client()
    ids = sys.argv[1:] or campaign_ids()
    portada = client.get("portada") or campaign_ids()[-1]
    built = {cid: build(cid, client) for cid in ids}
    if portada not in built:
        built[portada] = build(portada, client)
    write_root(portada, built[portada])
    print(f"[DONE] Reportes generados: {', '.join(ids)} · portada: {portada}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
