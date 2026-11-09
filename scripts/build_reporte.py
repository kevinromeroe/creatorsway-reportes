#!/usr/bin/env python3
"""build_reporte.py — Genera el reporte web de cada campaña y la portada del sitio.

Lee config/cliente.yaml y config/campanas/<id>/{campana,metricas,publicas,conversacion}.yaml,
calcula las cifras y escribe <id>/index.html:
  - campaña de un creador (tipo por defecto): pipeline/metrics.py + templates/reporte.html
  - campaña con varios creadores (`tipo: creadores`): pipeline/metrics_creadores.py +
    templates/reporte-creadores.html, que toma los estilos de templates/reporte.html.
La raíz del sitio (index.html) es la portada: una tarjeta por campaña (templates/portada.html).

Uso:
    python scripts/build_reporte.py                  # todas las campañas
    python scripts/build_reporte.py canola-2026      # una campaña (la portada se regenera con todas)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import metrics, metrics_creadores  # noqa: E402
from pipeline.util.config import PROJECT_ROOT, campaign_ids, load_campaign, load_client, load_conversation, load_metrics, load_public  # noqa: E402
from pipeline.util.log import get_logger  # noqa: E402

log = get_logger("build_reporte")
TEMPLATES = PROJECT_ROOT / "templates"
MARKER = "/*__DATA__*/null"
CSS_MARKER = "/*__CSS__*/"
REDES = {"ig": "Instagram", "tt": "TikTok", "fb": "Facebook"}


def _base_css() -> str:
    """Estilos del diseño aprobado, tal como están en templates/reporte.html."""
    html = (TEMPLATES / "reporte.html").read_text(encoding="utf-8")
    return re.search(r"<style>(.*?)</style>", html, re.S).group(1)


def render(template: str, data: dict, **extra) -> str:
    html = (TEMPLATES / template).read_text(encoding="utf-8")
    if MARKER not in html:
        raise RuntimeError(f"{template} no tiene el marcador {MARKER}")
    if CSS_MARKER in html:
        html = html.replace(CSS_MARKER, _base_css())
    payload = json.dumps({**data, **extra}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return html.replace(MARKER, payload)


def build(campaign_id: str, client: dict) -> dict:
    camp = load_campaign(campaign_id)
    multi = camp.get("tipo") == "creadores"
    mod = metrics_creadores if multi else metrics
    data = mod.build_data(client, camp, load_metrics(campaign_id), load_conversation(campaign_id), load_public(campaign_id))
    out = PROJECT_ROOT / campaign_id / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render("reporte-creadores.html" if multi else "reporte.html", data, pdfBase="pdf"), encoding="utf-8")
    log.info("reporte_ok", extra={"campaign": campaign_id, "tabs": data["tabs"], "views_all": data["totals"]["views_all"]})
    return data


def _short(v: float) -> str:
    if v >= 1e6:
        return f"{v / 1e6:.2f} M".replace(".", ",")
    if v >= 1e4:
        return f"{round(v / 1e3)} K"
    return f"{round(v):,}".replace(",", ".")


def _pct(v: float, d: int = 1) -> str:
    return f"{v * 100:.{d}f} %".replace(".", ",")


def _lista(xs: list[str]) -> str:
    return xs[0] if len(xs) < 2 else ", ".join(xs[:-1]) + " y " + xs[-1]


def tarjeta(cid: str, d: dict) -> dict:
    """Lo que la portada muestra de cada campaña."""
    t = d["totals"]
    if d.get("tipo") == "creadores":
        crs = sorted(d["creadores"], key=lambda c: -c["alcance"])
        return {"id": cid, "marca": d["marca"]["nombre"], "logo": d["marca"]["logo"], "logo_ancho": True,
                "quien": f"{len(crs)} creadores", "avatares": [c["avatar"] for c in crs[:4]],
                "periodo": d["periodo_largo"],
                "resumen": f"{len(d['pieces'])} publicaciones en Instagram y TikTok y {len(d['stories'])} historias, "
                           f"con metas de alcance por contrato.",
                "cifras": [[_pct(d["kpi"]["pct"], 0), "del KPI de alcance"], [_short(t["views_all"]), "visualizaciones"],
                           [_pct(t["er"]), "tasa de interacción"]]}
    return {"id": cid, "marca": d["marca"]["nombre"], "logo": d["marca"]["logo"], "logo_ancho": False,
            "quien": d["creador"]["nombre"], "avatares": [d["creador"]["avatar"]] if d["creador"].get("avatar") else [],
            "periodo": d["periodo"],
            "resumen": f"{len(d['pieces'])} recetas publicadas en {_lista([REDES[k] for k in d['netList']])}, e historias.",
            "cifras": [[_short(t["views_all"]), "visualizaciones"], [_short(t["reach_all"]), "de alcance"],
                       [_pct(t["er"]), "tasa de interacción"]]}


def write_root(built: dict[str, dict]) -> None:
    order = sorted(built, key=lambda c: str(load_campaign(c)["periodo"]["hasta"]), reverse=True)
    data = {"campanas": [tarjeta(c, built[c]) for c in order]}
    (PROJECT_ROOT / "index.html").write_text(render("portada.html", data), encoding="utf-8")
    log.info("portada_ok", extra={"campaigns": order})


def main() -> int:
    client = load_client()
    ids = sys.argv[1:] or campaign_ids()
    built = {cid: build(cid, client) for cid in ids}
    for cid in campaign_ids():  # la portada lista todas las campañas
        if cid not in built:
            built[cid] = build(cid, client)
    write_root(built)
    print(f"[DONE] Reportes generados: {', '.join(ids)} · portada con {len(built)} campañas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
