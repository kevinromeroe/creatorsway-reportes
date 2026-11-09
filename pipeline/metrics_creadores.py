"""Cifras de una campaña con varios creadores y KPI de alcance por contrato (ej. Canola Life 2026).

Igual que en pipeline/metrics.py, todas las cifras salen de aquí y la plantilla
(templates/reporte-creadores.html) solo las formatea.

Fuentes:
  publicas.yaml  visualizaciones, me gusta, comentarios y compartidos (y guardados de TikTok), leídos por
                 Datalítica en cada plataforma. Instagram sin Facebook; las reproducciones en Facebook de
                 la publicación cruzada se suman aparte (fb_views).
  metricas.yaml  Excel: alcance, guardados y reposts de Instagram, historias y la hoja "Cumplimiento KPI".
  campana.yaml   creadores y qué publicación corresponde a cada fila del Excel.

Definiciones:
  interacciones (reel/video) = me gusta + comentarios + compartidos + guardados (+ reposts en Instagram)
  tasa de interacción        = interacciones ÷ alcance (Instagram y TikTok)
  visualizaciones totales    = Instagram + TikTok + Facebook (publicación cruzada) + historias
  cumplimiento del KPI       = alcance verificado ÷ KPI, solo piezas contratadas (las bonificadas no tienen KPI)
  proyección                 = alcance proyectado del Excel (+7 % en reels y videos); es una estimación
                               y se muestra siempre aparte de lo verificado.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pipeline.metrics import MESES, fecha_corta

NET = {"ig": "Instagram", "tt": "TikTok"}
PLAT = {"ig": "Instagram", "tt": "TikTok"}


def _n(v: Any) -> float:
    return v or 0


def _lvl(er: float, tasa: dict) -> str:
    return "alta" if er >= tasa.get("alta_desde", 0.10) else "baja" if er < tasa.get("baja_bajo", 0.06) else "media"


def _periodo(desde: Any, hasta: Any) -> str:
    a, b = date.fromisoformat(str(desde)), date.fromisoformat(str(hasta))
    return f"{a.day} de {MESES[a.month - 1]} al {b.day} de {MESES[b.month - 1]} de {b.year}"


def build_data(client: dict, camp: dict, met: dict, conv: dict | None = None, pub: dict | None = None) -> dict:
    tasa = client.get("tasa", {})
    pub = pub or {}
    creadores = {c["id"]: {**c, "avatar": c.get("avatar") or f"assets/{camp['id']}/avatar-{c['ig']}.jpg"}
                 for c in camp["creadores"]}
    excel = {m["id"]: m for red in ("instagram", "tiktok", "historias") for m in met.get(red, [])}
    kpi_rows = list(met.get("kpi", []))
    usados: set[int] = set()

    def kpi_de(creador: dict, plataforma: str, formato_ok, fecha: str) -> dict | None:
        for i, r in enumerate(kpi_rows):
            if i in usados or r["creador"] != creador["excel"] or r["plataforma"] != plataforma:
                continue
            if str(r["fecha"]) == fecha and formato_ok(r["formato"]):
                usados.add(i)
                return r
        return None

    def kpi_out(r: dict | None) -> dict | None:
        if not r:
            return None
        k = r.get("kpi")
        return {"tipo": r["tipo"], "kpi": k, "alcance": r["alcance"], "proyectado": r.get("alcance_proyectado"),
                "cumple": (r["alcance"] >= k) if k else None, "pct": r["alcance"] / k if k else None,
                "estado_excel": r.get("estado")}

    # ---------- publicaciones ----------
    pieces = []
    for p in camp["piezas"]:
        cr, red, m = creadores[p["creador"]], p["red"], excel[p["excel"]]
        pb = pub.get("instagram" if red == "ig" else "tiktok", {}).get(str(p["codigo"]))
        if pb is None:
            raise ValueError(f"Sin cifras públicas para {p['codigo']}")
        likes, comments, shares = pb["likes"], pb["comments"], pb["shares"]
        saves = pb["saves"] if red == "tt" else _n(m.get("saves"))
        reposts = _n(m.get("reposts")) if red == "ig" else 0
        inter = likes + comments + shares + saves + reposts
        reach = m["reach"]
        er = inter / reach
        url = m["url"] if red == "ig" else f"https://www.tiktok.com/@{pb['cuenta']}/video/{p['codigo']}"
        k = kpi_out(kpi_de(cr, PLAT[red], (lambda f: f == "Reel") if red == "ig" else (lambda f: "TikTok" in f),
                           str(m["fecha"])))
        pieces.append({
            "id": str(p["codigo"]), "creador": cr["id"], "red": red, "t": p["titulo"],
            "fecha": str(pb["fecha"]), "f": fecha_corta(pb["fecha"]), "nota_fecha": p.get("nota_fecha"),
            "url": url, "img": f"assets/{camp['id']}/reel-{p['codigo']}.jpg" if red == "ig" else None,
            "collab": p.get("collab", True), "dur_s": pb.get("dur_s"),
            "v": pb["views"], "fbv": _n(pb.get("fb_views")), "r": reach, "likes": likes, "comments": comments,
            "shares": shares + reposts, "s": saves, "i": inter, "er": er, "lvl": _lvl(er, tasa),
            "excel_views": m.get("views"), "kpi": k,
        })
    pieces.sort(key=lambda x: x["fecha"])

    # ---------- historias (solo Excel) ----------
    stories = []
    for h in camp.get("historias", []):
        cr, m = creadores[h["creador"]], excel[h["excel"]]
        fmt = h.get("kpi_formato")
        k = kpi_out(kpi_de(cr, "Instagram", (lambda f, fmt=fmt: f == fmt) if fmt else (lambda f: f.startswith("Historia")),
                           str(m["fecha"])))
        stories.append({"creador": cr["id"], "fecha": str(m["fecha"]), "f": fecha_corta(m["fecha"]),
                        "viewers": m["viewers"], "views": m["views"], "inter": _n(m.get("inter")),
                        "sticker": m.get("sticker_taps"), "link": m.get("link_taps"), "visits": _n(m.get("profile_visits")),
                        "kpi": k})
    if len(usados) != len(kpi_rows):
        sobran = [kpi_rows[i] for i in range(len(kpi_rows)) if i not in usados]
        raise ValueError(f"Filas de KPI sin publicación: {sobran}")

    # ---------- KPI ----------
    filas = [x["kpi"] for x in pieces + stories if x["kpi"]]
    contr = [f for f in filas if f["kpi"]]

    def cumpl(rows):
        k = sum(r["kpi"] for r in rows)
        a = sum(r["alcance"] for r in rows)
        pr = sum(r["proyectado"] for r in rows)
        return {"kpi": k, "alcance": a, "pct": a / k, "proyectado": pr, "pct_proyectado": pr / k,
                "piezas": len(rows), "cumplen": sum(r["cumple"] for r in rows)}

    macro = [c["id"] for c in creadores.values() if c["tipo"] == "Macro reemplazo"]
    sin_macro = [x["kpi"] for x in pieces + stories if x["kpi"] and x["kpi"]["kpi"] and x["creador"] not in macro]
    kpi = {**cumpl(contr), "sin_macro": cumpl(sin_macro), "macro": [creadores[c]["nombre"] for c in macro],
           "bonificado_alcance": sum(f["alcance"] for f in filas if not f["kpi"]),
           "bonificado_piezas": sum(1 for f in filas if not f["kpi"]),
           "alcance_verificado": sum(f["alcance"] for f in filas)}

    # ---------- creadores ----------
    conv = conv or {}
    cpz = conv.get("piezas", {})
    crs = []
    for c in creadores.values():
        P = [p for p in pieces if p["creador"] == c["id"]]
        S = [s for s in stories if s["creador"] == c["id"]]
        rows = [x["kpi"] for x in P + S if x["kpi"] and x["kpi"]["kpi"]]
        k = sum(r["kpi"] for r in rows)
        a = sum(r["alcance"] for r in rows)
        reach = sum(p["r"] for p in P)
        inter = sum(p["i"] for p in P)
        tono = {}
        for p in P:
            for t, n in cpz.get(p["id"], {}).get("tono", {}).items():
                tono[t] = tono.get(t, 0) + n
        crs.append({
            "id": c["id"], "nombre": c["nombre"], "ig": c["ig"], "tt": c.get("tt"), "tipo": c["tipo"],
            "avatar": c["avatar"], "piezas": [p["id"] for p in P], "n_reels": sum(p["red"] == "ig" for p in P),
            "n_tt": sum(p["red"] == "tt" for p in P), "n_hist": len(S),
            "kpi": k, "alcance": a, "pct": a / k if k else None, "cumple": a >= k if k else None,
            "piezas_kpi": len(rows), "piezas_cumplen": sum(r["cumple"] for r in rows),
            "bonificado": sum(x["kpi"]["alcance"] for x in P + S if x["kpi"] and not x["kpi"]["kpi"]),
            "v": sum(p["v"] + p["fbv"] for p in P) + sum(s["views"] for s in S),
            "reach": reach, "i": inter, "er": inter / reach if reach else None,
            "comments": sum(p["comments"] for p in P), "tono": tono,
        })
    crs.sort(key=lambda c: -(c["pct"] or 0))

    # ---------- totales por red ----------
    def net(red):
        P = [p for p in pieces if p["red"] == red]
        v, r, i = sum(p["v"] for p in P), sum(p["r"] for p in P), sum(p["i"] for p in P)
        return {"n": len(P), "v": v, "r": r, "i": i, "er": i / r, "likes": sum(p["likes"] for p in P),
                "comments": sum(p["comments"] for p in P), "shares": sum(p["shares"] for p in P),
                "s": sum(p["s"] for p in P), "fbv": sum(p["fbv"] for p in P)}

    nets = {"ig": net("ig"), "tt": net("tt")}
    st = {"n": len(stories), "viewers": sum(s["viewers"] for s in stories), "views": sum(s["views"] for s in stories),
          "inter": sum(s["inter"] for s in stories), "sticker": sum(_n(s["sticker"]) for s in stories),
          "link": sum(_n(s["link"]) for s in stories), "visits": sum(s["visits"] for s in stories)}
    reach = nets["ig"]["r"] + nets["tt"]["r"]
    inter = nets["ig"]["i"] + nets["tt"]["i"]
    totals = {
        "views_ig": nets["ig"]["v"], "views_tt": nets["tt"]["v"], "views_fb": nets["ig"]["fbv"], "views_st": st["views"],
        "views_all": nets["ig"]["v"] + nets["tt"]["v"] + nets["ig"]["fbv"] + st["views"],
        "reach": reach, "reach_all": reach + st["viewers"], "inter": inter, "er": inter / reach,
        "saves": nets["ig"]["s"] + nets["tt"]["s"], "shares": nets["ig"]["shares"] + nets["tt"]["shares"],
        "comments": nets["ig"]["comments"] + nets["tt"]["comments"],
    }
    if totals["reach_all"] != kpi["alcance_verificado"]:
        raise ValueError(f"El alcance por pieza ({totals['reach_all']}) no cuadra con la hoja de KPI "
                         f"({kpi['alcance_verificado']})")

    # ---------- hallazgos e insights ----------
    by_v = sorted(pieces, key=lambda p: -(p["v"] + p["fbv"]))
    top = by_v[0]
    vis = lambda p: p["v"] + p["fbv"]  # noqa: E731
    tot_pv = sum(vis(p) for p in pieces)
    macro_c = next((c for c in crs if c["id"] in macro), None)
    contr_c = [c for c in crs if c["kpi"]]
    cumplen_c = [c for c in contr_c if c["cumple"]]
    casi = [c for c in contr_c if not c["cumple"] and c["pct"] >= 0.95]
    micro = [c for c in contr_c if c["tipo"] == "Micro"]
    tt_rows = [p for p in pieces if p["red"] == "tt" and p["kpi"] and p["kpi"]["kpi"]]
    ig_rows = [p for p in pieces if p["red"] == "ig" and p["kpi"] and p["kpi"]["kpi"]]
    st_rows = [s for s in stories if s["kpi"] and s["kpi"]["kpi"]]
    nocollab = [p for p in pieces if not p["collab"]]
    saves_share = totals["saves"] / inter
    by_er = sorted([p for p in pieces if p["red"] == "ig"], key=lambda p: -p["er"])
    ins = {
        "top_piece": top["t"], "top_creador": next(c["nombre"] for c in crs if c["id"] == top["creador"]),
        "top_share_views": vis(top) / tot_pv, "top_views": vis(top),
        "macro_nombre": macro_c["nombre"] if macro_c else None, "macro_pct": macro_c["pct"] if macro_c else None,
        "macro_reach_share": (macro_c["alcance"] / kpi["alcance"]) if macro_c else None,
        "creadores_cumplen": [c["nombre"] for c in cumplen_c], "n_creadores_kpi": len(contr_c),
        "casi": [{"nombre": c["nombre"], "pct": c["pct"]} for c in casi],
        "micro_cumplen": sum(c["cumple"] for c in micro), "n_micro": len(micro),
        "tt_cumplen": sum(p["kpi"]["cumple"] for p in tt_rows), "n_tt_kpi": len(tt_rows),
        "ig_cumplen": sum(p["kpi"]["cumple"] for p in ig_rows), "n_ig_kpi": len(ig_rows),
        "st_cumplen": sum(s["kpi"]["cumple"] for s in st_rows), "n_st_kpi": len(st_rows),
        "fb_share_meta": totals["views_fb"] / (totals["views_fb"] + totals["views_ig"]),
        "tt_reach_share": nets["tt"]["r"] / reach, "saves_share": saves_share,
        "inter_per_100": inter / reach * 100, "nocollab": [{"t": p["t"], "creador": next(c["nombre"] for c in crs if c["id"] == p["creador"]), "f": p["f"]} for p in nocollab],
        "er_top": {"t": by_er[0]["t"], "er": by_er[0]["er"], "creador": next(c["nombre"] for c in crs if c["id"] == by_er[0]["creador"])},
        "n_alta": sum(p["lvl"] == "alta" for p in pieces), "n_pieces": len(pieces),
        "st_top": max(stories, key=lambda s: s["viewers"]),
    }
    ins["st_top"] = {**ins["st_top"], "nombre": creadores[ins["st_top"]["creador"]]["nombre"]}

    data = {
        "id": camp["id"], "tipo": "creadores", "marca": camp["marca"], "periodo": camp["periodo"]["texto"],
        "periodo_largo": _periodo(camp["periodo"]["desde"], camp["periodo"]["hasta"]),
        "publicasCapturado": str(pub.get("capturado") or ""),
        "tabs": ["resumen", "creadores", "instagram", "tiktok"],
        "creadores": crs, "pieces": pieces, "stories": stories, "nets": nets, "storiesTotal": st,
        "totals": totals, "kpi": kpi, "insights": ins, "conv": _conv(conv, pieces, creadores),
    }
    return data


def _conv(conv: dict, pieces: list, creadores: dict) -> dict | None:
    if not conv:
        return None
    T = conv["total"]
    temas = conv["temas"]
    n = T["publico"]
    lst = [{"k": k, "label": temas[k], "n": v, "share": v / n} for k, v in
           sorted(T["temas"].items(), key=lambda kv: -kv[1]) if k not in ("otros", "etiqueta")]
    tono = {k: T["tono"].get(k, 0) for k in ("positivo", "negativo", "duda", "neutro")}
    marca_n = sum(tono.values())
    # publicación con más críticas al aceite
    crit = sorted(((p, conv["piezas"].get(p["id"], {}).get("tono", {}).get("negativo", 0)) for p in pieces),
                  key=lambda x: -x[1])
    dudas = sorted(((p, conv["piezas"].get(p["id"], {}).get("tono", {}).get("duda", 0)) for p in pieces),
                   key=lambda x: -x[1])
    pedidos = sorted(((p, conv["piezas"].get(p["id"], {}).get("temas", {}).get("pedido", 0)) for p in pieces),
                     key=lambda x: -x[1])
    nombre = lambda p: creadores[p["creador"]]["nombre"]  # noqa: E731
    redes = {}
    for k, r in conv.get("redes", {}).items():
        rn = r["capturados"]
        redes[k] = {"n": rn, "total": r["total_plataforma"],
                    "temas": [{"k": t, "label": temas[t], "n": v, "share": v / rn} for t, v in
                              sorted(r["temas"].items(), key=lambda kv: -kv[1]) if t not in ("otros", "etiqueta")],
                    "tono": {t: r["tono"].get(t, 0) for t in ("positivo", "negativo", "duda", "neutro")}}
    dest = []
    for tm in ("antojo", "critica", "producto", "pedido", "humor"):
        for q in conv.get("destacados", {}).get(tm, [])[:1]:
            dest.append({**q, "tema": temas[tm], "creador": creadores[q["creador"]]["nombre"]})
    return {
        "n": n, "total": T["total_plataforma"], "creadores_resp": T["respuestas_creadores"],
        "coverage": (n + T["respuestas_creadores"]) / T["total_plataforma"],
        "preguntas": T["preguntas"], "respondidas": T["preguntas_respondidas"],
        "temas": lst, "tono": tono, "marca_n": marca_n, "marca_share": marca_n / n,
        "duda_esparcible": T.get("duda_esparcible", 0), "duda_fuera": T.get("duda_fuera", 0),
        "neg_publicidad": T.get("neg_publicidad", 0),
        "crit_top": {"t": crit[0][0]["t"], "creador": nombre(crit[0][0]), "n": crit[0][1],
                     "share": crit[0][1] / max(1, tono["negativo"])},
        "duda_top": {"t": dudas[0][0]["t"], "creador": nombre(dudas[0][0]), "n": dudas[0][1]},
        "pedido_top": {"t": pedidos[0][0]["t"], "creador": nombre(pedidos[0][0]), "n": pedidos[0][1]},
        "top_crit_quote": (conv.get("destacados", {}).get("critica") or [None])[0],
        "redes": redes, "destacados": dest,
    }
