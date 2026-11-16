"""Cifras de una campaña con varios creadores organizada por acciones del plan (ej. Premier 2026).

Produce los mismos campos que pipeline/metrics_creadores.py (la plantilla es la misma,
templates/reporte-creadores.html) y además `plan`: el avance de las acciones contratadas.

Fuentes y regla («cada variable con su valor más reciente»):
  metricas.yaml  (scripts/importar_plan.py) las acciones del Excel: estado, KPI, alcance, visualizaciones e
                 interacciones. El alcance siempre es del Excel (no es público).
  publicas.yaml  cifras públicas de las publicaciones confirmadas en el scouting: visualizaciones (Instagram
                 sin Facebook + Facebook aparte), me gusta, comentarios, compartidos, guardados de TikTok y
                 fecha real. Reemplazan a las del Excel.
  Interacciones: TikTok = me gusta + comentarios + compartidos + guardados públicos. Instagram = el mayor
                 entre el total del Excel (incluye guardados, que no son públicos) y lo público.
  Piezas no encontradas en el scouting: cifras del Excel, marcadas «sin verificar».

Definiciones:
  cumplimiento del KPI = alcance logrado (acciones con resultados) ÷ KPI de las acciones contratadas
                         (todas, también las que faltan por ejecutar), como en el Excel.
  tasa de interacción  = interacciones ÷ alcance (reels y videos).
"""
from __future__ import annotations

from typing import Any

from pipeline.metrics import MESES, fecha_corta

ESTADOS = ["EJECUTADO", "EN APROBACIÓN", "NO EJECUTADO", "PENDIENTE DE REGISTRO", "SIN ESTADO"]
ESTADO_TXT = {"EJECUTADO": "Ejecutadas", "EN APROBACIÓN": "En aprobación", "NO EJECUTADO": "No ejecutadas",
              "PENDIENTE DE REGISTRO": "Pendiente de registro", "SIN ESTADO": "Sin estado"}


def _n(v: Any) -> float:
    return v or 0


def _lvl(er: float, tasa: dict) -> str:
    return "alta" if er >= tasa.get("alta_desde", 0.10) else "baja" if er < tasa.get("baja_bajo", 0.06) else "media"


def _formato(a: dict) -> str:
    f = a["formato"].lower()
    return "historia" if "historia" in f else "tt" if a["plataforma"] == "TikTok" else "reel"


def build_data(client: dict, camp: dict, met: dict, conv: dict | None = None, pub: dict | None = None) -> dict:
    tasa = client.get("tasa", {})
    pub = pub or {}
    cr = {c["id"]: {**c, "avatar": f"assets/{camp['id']}/avatar-{c.get('ig') or c.get('tt')}.jpg", "tipo": "Contratado"}
          for c in camp["creadores"]}
    por_excel = {c["excel"]: c["id"] for c in camp["creadores"]}
    acc = {a["fila"]: {**a, "creador": por_excel[a["talento"]]} for a in met["acciones"]}

    def kpi_out(a):
        k, al = a["kpi"], a["alcance"]
        return {"tipo": a["estado"].capitalize(), "kpi": k, "alcance": _n(al), "proyectado": None,
                "cumple": (al or 0) >= k if k else None, "pct": (al or 0) / k if k else None,
                "estado_excel": a["estado"]}

    # ---------- reels y videos ----------
    pieces, usadas = [], set()
    for p in camp["piezas"]:
        a, red = acc[p["fila"]], p["red"]
        usadas.add(p["fila"])
        codigo = p.get("codigo")
        pb = (pub.get("instagram" if red == "ig" else "tiktok") or {}).get(str(codigo)) if codigo else None
        if codigo and pb is None:
            raise ValueError(f"Fila {p['fila']}: sin cifras públicas para {codigo}")
        if pb:
            likes, comments, shares = pb["likes"], pb["comments"], pb["shares"]
            saves = pb.get("saves") if red == "tt" else None
            publico = likes + comments + shares + _n(saves)
            inter = publico if red == "tt" else max(_n(a["inter"]), publico)
            v, fbv, fecha = pb["views"], _n(pb.get("fb_views")), str(pb["fecha"])
            url = (f"https://www.instagram.com/reel/{codigo}/" if red == "ig"
                   else f"https://www.tiktok.com/@{pb['cuenta']}/video/{codigo}")
            collab = "premier" in str(pb.get("coautor") or "").lower() if red == "ig" else None
        else:
            likes = comments = shares = saves = None
            inter, v, fbv, fecha, url, collab = _n(a["inter"]), _n(a["views"]), 0, a.get("fecha_excel"), None, None
        reach = a["alcance"]
        er = inter / reach if reach else 0
        c = cr[p["creador"]]
        pieces.append({
            "id": str(codigo or f"fila-{p['fila']}"), "fila": p["fila"], "creador": p["creador"], "red": red,
            "t": p["titulo"], "fecha": fecha, "f": fecha_corta(fecha) if fecha else "sin fecha",
            "url": url, "img": f"assets/{camp['id']}/reel-{codigo}.jpg" if pb and red == "ig" else None,
            "verificada": bool(pb), "collab": collab if collab is not None else True, "dur_s": (pb or {}).get("dur_s"),
            "v": v, "fbv": fbv, "r": reach, "likes": likes, "comments": comments,
            "shares": shares, "s": saves, "i": inter, "er": er, "lvl": _lvl(er, tasa),
            "excel_views": a["views"], "excel_inter": a["inter"], "kpi": kpi_out(a), "estado": a["estado"],
            "cuenta_handle": c.get("ig") if red == "ig" else c.get("tt"),
        })
    pieces.sort(key=lambda x: (x["fecha"] or "9999", x["fila"]))

    # ---------- historias (solo Excel) ----------
    stories = []
    for f in camp.get("historias", []):
        a = acc[f]
        usadas.add(f)
        stories.append({"creador": a["creador"], "fila": f, "fecha": a.get("fecha_excel"),
                        "f": fecha_corta(a["fecha_excel"]) if a.get("fecha_excel") else "sin fecha",
                        "viewers": _n(a["alcance"]), "views": a["views"], "inter": a["inter"],
                        "sin_alcance": a["alcance"] is None, "sticker": None, "link": None, "visits": 0,
                        "kpi": kpi_out(a), "nota": a.get("nota")})
    sobran = [f for f, a in acc.items() if a["cuenta"] and f not in usadas]
    if sobran:
        raise ValueError(f"Acciones con resultados sin pieza ni historia en campana.yaml: {sobran}")

    # ---------- plan ----------
    estados = {e: 0 for e in ESTADOS}
    for a in acc.values():
        estados[a["estado"]] = estados.get(a["estado"], 0) + 1
    con = [a for a in acc.values() if a["cuenta"]]
    sin = [a for a in acc.values() if not a["cuenta"]]
    plan = {"total": len(acc), "con_resultados": len(con), "faltan": len(sin),
            "estados": [{"k": k, "label": ESTADO_TXT.get(k, k.capitalize()), "n": n} for k, n in estados.items() if n],
            "kpi_faltante": sum(_n(a["kpi"]) for a in sin),
            "por_creador": [], "pendientes": []}
    for c in camp["creadores"]:
        A = [a for a in acc.values() if a["creador"] == c["id"]]
        plan["por_creador"].append({"id": c["id"], "plan": len(A), "con": sum(a["cuenta"] for a in A),
                                    "estados": {e: sum(a["estado"] == e for a in A) for e in ESTADOS}})
    for a in sorted(sin, key=lambda a: (a["creador"], a["fila"])):
        plan["pendientes"].append({"creador": a["creador"], "red": "tt" if a["plataforma"] == "TikTok" else "ig",
                                   "formato": a["formato"], "estado": a["estado"], "kpi": a["kpi"]})

    # ---------- KPI ----------
    kpi_total = sum(_n(a["kpi"]) for a in acc.values())
    alcance = sum(_n(a["alcance"]) for a in con)
    filas_res = [x["kpi"] for x in pieces + stories]
    top = max(pieces, key=lambda p: p["r"] or 0)
    kpi = {"kpi": kpi_total, "alcance": alcance, "pct": alcance / kpi_total, "proyectado": None, "pct_proyectado": None,
           "piezas": len(filas_res), "cumplen": sum(bool(k["cumple"]) for k in filas_res),
           "acciones": len(acc), "kpi_ejecutado": sum(_n(a["kpi"]) for a in con),
           "sin_macro": {"kpi": kpi_total, "alcance": alcance - top["r"], "pct": (alcance - top["r"]) / kpi_total,
                         "piezas": len(filas_res) - 1, "cumplen": sum(bool(k["cumple"]) for k in filas_res) - bool(top["kpi"]["cumple"]),
                         "proyectado": None, "pct_proyectado": None},
           "macro": [], "top_pieza": {"t": top["t"], "red": top["red"], "creador": cr[top["creador"]]["nombre"],
                                      "r": top["r"], "share": top["r"] / alcance},
           "bonificado_alcance": 0, "bonificado_piezas": 0, "alcance_verificado": alcance}

    # ---------- creadores ----------
    conv = conv or {}
    cpz = conv.get("piezas", {})
    crs = []
    for c in cr.values():
        P = [p for p in pieces if p["creador"] == c["id"]]
        S = [s for s in stories if s["creador"] == c["id"]]
        A = [a for a in acc.values() if a["creador"] == c["id"]]
        k = sum(_n(a["kpi"]) for a in A)
        al = sum(_n(a["alcance"]) for a in A if a["cuenta"])
        reach = sum(_n(p["r"]) for p in P)
        inter = sum(p["i"] for p in P)
        tono = {}
        for p in P:
            for t, n in cpz.get(p["id"], {}).get("tono", {}).items():
                tono[t] = tono.get(t, 0) + n
        rows = [x["kpi"] for x in P + S]
        crs.append({
            "id": c["id"], "nombre": c["nombre"], "ig": c.get("ig"), "tt": c.get("tt"), "tipo": "Contratado",
            "avatar": c["avatar"], "piezas": [p["id"] for p in P],
            "n_reels": sum(p["red"] == "ig" for p in P), "n_tt": sum(p["red"] == "tt" for p in P), "n_hist": len(S),
            "kpi": k, "alcance": al, "pct": al / k if k else None, "cumple": al >= k if k else None,
            "piezas_kpi": len(rows), "piezas_cumplen": sum(bool(r["cumple"]) for r in rows),
            "plan": len(A), "faltan": sum(not a["cuenta"] for a in A),
            "sin_verificar": sum(not p["verificada"] for p in P),
            "bonificado": 0, "v": sum(p["v"] + p["fbv"] for p in P) + sum(_n(s["views"]) for s in S),
            "reach": reach, "i": inter, "er": inter / reach if reach else None,
            "comments": sum(_n(p["comments"]) for p in P), "tono": tono,
        })
    crs.sort(key=lambda c: -(c["pct"] or 0))

    # ---------- redes y totales ----------
    def net(red):
        P = [p for p in pieces if p["red"] == red]
        v, r, i = sum(p["v"] for p in P), sum(_n(p["r"]) for p in P), sum(p["i"] for p in P)
        V = [p for p in P if p["verificada"]]
        return {"n": len(P), "v": v, "r": r, "i": i, "er": i / r if r else 0, "likes": sum(_n(p["likes"]) for p in V),
                "comments": sum(_n(p["comments"]) for p in V), "shares": sum(_n(p["shares"]) for p in V),
                "s": sum(_n(p["s"]) for p in V), "fbv": sum(p["fbv"] for p in P), "verificadas": len(V)}

    nets = {"ig": net("ig"), "tt": net("tt")}
    st = {"n": len(stories), "viewers": sum(s["viewers"] for s in stories), "views": sum(_n(s["views"]) for s in stories),
          "inter": sum(_n(s["inter"]) for s in stories), "sticker": 0, "link": 0, "visits": 0,
          "sin_alcance": sum(s["sin_alcance"] for s in stories)}
    reach = nets["ig"]["r"] + nets["tt"]["r"]
    inter = nets["ig"]["i"] + nets["tt"]["i"]
    totals = {
        "views_ig": nets["ig"]["v"], "views_tt": nets["tt"]["v"], "views_fb": nets["ig"]["fbv"], "views_st": st["views"],
        "views_all": nets["ig"]["v"] + nets["tt"]["v"] + nets["ig"]["fbv"] + st["views"],
        "reach": reach, "reach_all": reach + st["viewers"], "inter": inter, "er": inter / reach,
        "saves": nets["tt"]["s"], "shares": nets["ig"]["shares"] + nets["tt"]["shares"],
        "comments": nets["ig"]["comments"] + nets["tt"]["comments"],
        "excel_views": met["control"]["views"], "excel_inter": met["control"]["inter"],
    }
    if totals["reach_all"] != kpi["alcance"]:
        raise ValueError(f"El alcance por pieza ({totals['reach_all']}) no cuadra con el Excel ({kpi['alcance']})")

    # ---------- insights ----------
    vis = lambda p: p["v"] + p["fbv"]  # noqa: E731
    by_v = sorted(pieces, key=lambda p: -vis(p))
    tot_pv = sum(vis(p) for p in pieces)
    contr_c = [c for c in crs if c["kpi"]]
    cumplen_c = [c for c in contr_c if c["cumple"]]
    fmt = {}
    for key, red in (("ig", "ig"), ("tt", "tt")):
        R = [p["kpi"] for p in pieces if p["red"] == red]
        fmt[key] = (sum(bool(k["cumple"]) for k in R), len(R))
    Sk = [s["kpi"] for s in stories]
    V = [p for p in pieces if p["verificada"]]
    by_er = sorted(V, key=lambda p: -p["er"])
    tt_jft = next((p for p in pieces if p["fila"] == "90"), None)
    ins = {
        "top_piece": by_v[0]["t"], "top_creador": cr[by_v[0]["creador"]]["nombre"], "top_red": by_v[0]["red"],
        "top_share_views": vis(by_v[0]) / tot_pv, "top_views": vis(by_v[0]),
        "macro_nombre": None, "macro_pct": None, "macro_reach_share": kpi["top_pieza"]["share"],
        "creadores_cumplen": [c["nombre"] for c in cumplen_c], "n_creadores_kpi": len(contr_c),
        "casi": [{"nombre": c["nombre"], "pct": c["pct"]} for c in contr_c if not c["cumple"] and c["pct"] >= 0.95],
        "micro_cumplen": 0, "n_micro": 0,
        "ig_cumplen": fmt["ig"][0], "n_ig_kpi": fmt["ig"][1], "tt_cumplen": fmt["tt"][0], "n_tt_kpi": fmt["tt"][1],
        "st_cumplen": sum(bool(k["cumple"]) for k in Sk), "n_st_kpi": len(Sk),
        "fb_share_meta": totals["views_fb"] / (totals["views_fb"] + totals["views_ig"]),
        "tt_reach_share": nets["tt"]["r"] / reach, "saves_share": None,
        "inter_per_100": inter / reach * 100,
        "nocollab": [{"t": p["t"], "creador": cr[p["creador"]]["nombre"], "f": p["f"]}
                     for p in pieces if p["red"] == "ig" and p["verificada"] and not p["collab"]],
        "ig_verificadas": sum(p["red"] == "ig" and p["verificada"] for p in pieces), "er_top": {"t": by_er[0]["t"], "er": by_er[0]["er"],
                                                                          "creador": cr[by_er[0]["creador"]]["nombre"]},
        "n_alta": sum(p["lvl"] == "alta" for p in pieces), "n_pieces": len(pieces),
        "verificadas": len(V), "sin_verificar": [{"t": p["t"], "creador": cr[p["creador"]]["nombre"], "red": p["red"],
                                                  "r": p["r"], "fila": p["fila"]} for p in pieces if not p["verificada"]],
        "alcance_sin_verificar": sum(_n(p["r"]) for p in pieces if not p["verificada"]),
        "tt_jft": {"excel_inter": tt_jft["excel_inter"], "publico": tt_jft["i"], "estado": tt_jft["estado"]} if tt_jft else None,
        "st_top": None,
    }
    data = {
        "id": camp["id"], "tipo": "creadores", "modelo": "plan", "marca": camp["marca"],
        "periodo": camp["periodo"]["texto"], "periodo_largo": _periodo(camp),
        "estado_campana": camp.get("estado_campana"), "corte_excel": str(camp["periodo"].get("corte_excel") or ""),
        "publicasCapturado": str(pub.get("capturado") or ""),
        "tabs": ["resumen", "creadores", "instagram", "tiktok"],
        "creadores": crs, "pieces": pieces, "stories": stories, "nets": nets, "storiesTotal": st,
        "totals": totals, "kpi": kpi, "insights": ins, "plan": plan,
        "conv": _conv(conv, pieces, cr),
    }
    return data


def _periodo(camp: dict) -> str:
    from datetime import date
    a, b = date.fromisoformat(str(camp["periodo"]["desde"])), date.fromisoformat(str(camp["periodo"]["hasta"]))
    return f"{a.day} de {MESES[a.month - 1]} al {b.day} de {MESES[b.month - 1]} de {b.year}"


def _conv(conv: dict, pieces: list, cr: dict):
    from pipeline.metrics_creadores import _conv as base
    return base(conv, pieces, cr) if conv else None
