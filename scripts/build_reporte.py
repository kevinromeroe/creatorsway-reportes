#!/usr/bin/env python3
"""build_reporte.py — Genera el reporte web de cada campaña.

Lee config/cliente.yaml y config/campanas/<id>/{campana,metricas}.yaml, calcula las
cifras con pipeline/metrics.py y escribe <id>/index.html desde templates/reporte.html.
La raíz del sitio (index.html) redirige a la campaña indicada o a la última.

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


def build(campaign_id: str, client: dict) -> Path:
    data = build_data(client, load_campaign(campaign_id), load_metrics(campaign_id))
    html = TEMPLATE.read_text(encoding="utf-8")
    if MARKER not in html:
        raise RuntimeError(f"La plantilla no tiene el marcador {MARKER}")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out = PROJECT_ROOT / campaign_id / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html.replace(MARKER, payload), encoding="utf-8")
    log.info("reporte_ok", extra={"campaign": campaign_id, "tabs": data["tabs"],
                                   "views_all": data["totals"]["views_all"]})
    return out


def write_root_redirect(target: str) -> None:
    (PROJECT_ROOT / "index.html").write_text(
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url={target}/">'
        '<meta name="robots" content="noindex"><title>Reportes CreatorsWay</title></head>'
        f'<body><a href="{target}/">Ir al reporte</a></body></html>',
        encoding="utf-8",
    )


def main() -> int:
    client = load_client()
    ids = sys.argv[1:] or campaign_ids()
    for cid in ids:
        build(cid, client)
    write_root_redirect(campaign_ids()[-1])
    print(f"[DONE] Reportes generados: {', '.join(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
