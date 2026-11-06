"""Cálculo único de las cifras del reporte.

Todas las cifras salen de `build_data()`; la plantilla solo las formatea, así que el
mismo número es idéntico en cada pestaña y en el PDF.

Definiciones:
  interacciones (reel/video) = me gusta + comentarios + compartidos + guardados (+ reposts en Instagram)
  tasa de interacción        = interacciones ÷ alcance
  alcance de la campaña      = suma del alcance de cada pieza (una cuenta puede repetirse entre piezas)
  visualizaciones totales    = reels + videos + historias
  etiqueta de la tasa        = Alta / Media / Baja según config/cliente.yaml
"""
from __future__ import annotations

import re
from datetime import date
from statistics import mean
from typing import Any

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
MES3 = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def fecha_larga(iso: str) -> str:
    d = date.fromisoformat(str(iso))
    return f"{d.day} de {MESES[d.month - 1]}"


def fecha_corta(iso: str) -> str:
    d = date.fromisoformat(str(iso))
    return f"{d.day} {MES3[d.month - 1]}"


def _n(v: Any) -> float:
    return v or 0


def _post(m: dict[str, Any], net: str) -> dict[str, Any]:
    inter = _n(m["likes"]) + _n(m["comments"]) + _n(m["shares"]) + _n(m["saves"]) + _n(m.get("reposts"))
    out = {
        "net": net, "url": m.get("url"), "v": m["views"], "r": m["reach"], "likes": _n(m["likes"]),
        "comments": _n(m["comments"]), "shares": _n(m["shares"]) + _n(m.get("reposts")),
        "s": _n(m["saves"]), "i": inter, "er": inter / m["reach"],
    }
    if net == "ig":
        out.update(watch_s=m.get("watch_s"), newf=_n(m.get("new_followers")))
    else:
        out.update(dur_s=m.get("dur_s"), non_followers=m.get("non_followers"), women=m.get("women"),
                   men=m.get("men"), new_viewers=m.get("new_viewers"), returning=m.get("returning_viewers"))
    return out


def _sticker_handle(nota: Any) -> str | None:
    m = re.search(r"@([A-Za-z0-9_.]+)", str(nota or ""))
    return m.group(1).lower() if m else None


def _sum(posts: list[dict[str, Any]], key: str) -> float:
    return sum(p[key] for p in posts)


def level(er: float, cfg: dict[str, float]) -> str:
    if er >= cfg["alta_desde"]:
        return "alta"
    if er < cfg["baja_bajo"]:
        return "baja"
    return "media"


ORDEN_TEMAS = ["antojo", "humor", "marca", "fit", "receta", "etiqueta", "otros"]


def _temas(t: dict[str, int], nombres: dict[str, str]) -> list[dict[str, Any]]:
    n = sum(t.values()) or 1
    return [{"k": k, "label": nombres[k], "n": t.get(k, 0), "share": t.get(k, 0) / n}
            for k in ORDEN_TEMAS if t.get(k, 0)]


def build_conversation(conv: dict[str, Any], pieces: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Cifras e insights de la conversación a partir de conversacion.yaml."""
    if not conv:
        return None
    nombres = conv["temas"]
    tot = conv["total"]
    tono = tot["tono_marca"]
    opin = tono.get("positivo", 0) + tono.get("negativo", 0)
    slug_name = {p["slug"]: p["s"] for p in pieces}
    fit_by_piece = {slug: sum(r["temas"].get("fit", 0) for r in d.values()) for slug, d in conv["piezas"].items()}
    fit_top = max(fit_by_piece, key=fit_by_piece.get)
    marca_share = {slug: sum(r["temas"].get("marca", 0) for r in d.values()) / max(1, sum(r["capturados"] for r in d.values()))
                   for slug, d in conv["piezas"].items()}
    marca_top = max(marca_share, key=marca_share.get)
    redes = {}
    for k, r in conv["redes"].items():
        redes[k] = {"n": r["capturados"], "total": r["total_plataforma"], "temas": _temas(r["temas"], nombres),
                    "tono": r["tono_marca"]}
    dest = conv.get("destacados", {})
    return {
        "n": tot["capturados"], "total": tot["total_plataforma"], "coverage": tot["capturados"] / tot["total_plataforma"],
        "temas": _temas(tot["temas"], nombres),
        "tono": {"positivo": tono.get("positivo", 0), "negativo": tono.get("negativo", 0), "duda": tono.get("duda", 0),
                 "neutro": tono.get("neutro", 0), "neg_autenticidad": tono.get("neg_autenticidad", 0),
                 "neg_salud": tono.get("neg_salud", 0), "duda_fuera": tono.get("duda_fuera", 0)},
        "opinion_pos": tono.get("positivo", 0) / opin if opin else None,
        "fit_top_piece": slug_name[fit_top], "fit_top_share": fit_by_piece[fit_top] / max(1, tot["temas"].get("fit", 0)),
        "marca_top_piece": slug_name[marca_top], "marca_top_share": marca_share[marca_top],
        "redes": redes,
        "destacados": [{**d, "tema": nombres[k], "pieza": slug_name.get(d["pieza"], d["pieza"])}
                       for k in ("humor", "marca", "fit") for d in dest.get(k, [])[:1]],
    }


def build_data(client: dict[str, Any], camp: dict[str, Any], met: dict[str, Any],
               conv: dict[str, Any] | None = None) -> dict[str, Any]:
    tasa = client["tasa"]
    ig_by = {r["fecha"]: r for r in met["instagram"]}
    tt_by = {r["fecha"]: r for r in met["tiktok"]}

    pieces = []
    for pz in camp["piezas"]:
        f = str(pz["fecha"])
        if f not in ig_by or f not in tt_by:
            raise KeyError(f"La pieza {pz['slug']} ({f}) no está en las dos hojas del Excel")
        ig, tt = _post(ig_by[f], "ig"), _post(tt_by[f], "tt")
        p = {
            "slug": pz["slug"], "t": pz["titulo"], "s": pz["corto"], "fecha": f, "f": fecha_larga(f),
            "collab": pz.get("colaboracion"), "nota": " ".join(str(pz.get("nota", "")).split()),
            "ig": ig, "tt": tt,
            "v": ig["v"] + tt["v"], "r": ig["r"] + tt["r"], "i": ig["i"] + tt["i"], "sv": ig["s"] + tt["s"],
            "sh": ig["shares"] + tt["shares"],
        }
        p["er"] = p["i"] / p["r"]
        p["lvl"] = level(p["er"], tasa)
        pieces.append(p)

    igs = [p["ig"] for p in pieces]
    tts = [p["tt"] for p in pieces]
    allp = igs + tts
    t_inter = _sum(allp, "i")
    best = max(pieces, key=lambda p: p["i"])
    for p in pieces:
        p["best"] = p is best
        p["share_inter"] = p["i"] / t_inter

    def net_tot(ps: list[dict[str, Any]]) -> dict[str, Any]:
        d = {k: _sum(ps, k) for k in ("v", "r", "i", "s", "shares")}
        d["er"] = d["i"] / d["r"]
        return d

    ig_t, tt_t = net_tot(igs), net_tot(tts)
    ig_t["newf"] = _sum(igs, "newf")
    ig_t["watch_s"] = mean(p["watch_s"] for p in igs if p["watch_s"])
    tt_t["non_followers"] = mean(p["non_followers"] for p in tts if p["non_followers"] is not None)
    tt_t["women"] = mean(p["women"] for p in tts if p["women"] is not None)
    tt_t["men"] = mean(p["men"] for p in tts if p["men"] is not None)
    tt_t["new_viewers"] = mean(p["new_viewers"] for p in tts if p["new_viewers"] is not None)
    tt_t["dur_s"] = mean(p["dur_s"] for p in tts if p["dur_s"])

    # historias
    names = camp.get("historias") or []
    stories = []
    for k, h in enumerate(met["historias"]):
        stories.append({
            "name": names[k] if k < len(names) else (h.get("descripcion") or f"Historia {k + 1}"),
            "fecha": h["fecha"], "f": fecha_corta(h["fecha"]), "views": _n(h["views"]), "viewers": _n(h["viewers"]),
            "inter": _n(h["inter"]), "likes": _n(h["likes"]), "replies": _n(h["replies"]), "shares": _n(h["shares"]),
            "sticker": h.get("sticker_taps"), "visits": _n(h["profile_visits"]), "newf": _n(h["new_followers"]),
            "followers": h.get("followers"), "sticker_handle": _sticker_handle(h.get("notas")),
        })
    brand = camp["marca"]["handle"].lower()
    for s in stories:
        s["brand_sticker"] = s["sticker"] if s["sticker"] is not None and s["sticker_handle"] == brand else None
    st_t = {k: sum(_n(s[k]) for s in stories) for k in ("views", "viewers", "inter", "sticker", "visits", "newf")}
    st_t["brand_sticker"] = sum(_n(s["brand_sticker"]) for s in stories)
    top_story = max(stories, key=lambda s: _n(s["brand_sticker"]))
    for s in stories:
        s["top"] = s is top_story
    st_t["top_sticker_share"] = _n(top_story["brand_sticker"]) / st_t["brand_sticker"] if st_t["brand_sticker"] else None
    st_t["top_f"] = top_story["f"]
    # Grupo de historias del mismo día (p. ej. un evento) con más visualizaciones
    days: dict[str, list[dict[str, Any]]] = {}
    for s in stories:
        days.setdefault(s["fecha"], []).append(s)
    ev = max((g for g in days.values() if len(g) > 1), key=lambda g: sum(x["views"] for x in g), default=None)
    st_t["event"] = None if not ev else {
        "f": ev[0]["f"], "n": len(ev), "views": sum(x["views"] for x in ev),
        "brand_sticker": sum(_n(x["brand_sticker"]) for x in ev)}

    totals = {
        "views_all": ig_t["v"] + tt_t["v"] + st_t["views"],
        "reach_all": ig_t["r"] + tt_t["r"] + st_t["viewers"],
        "inter_all": t_inter + st_t["inter"],
        "views": ig_t["v"] + tt_t["v"], "reach": ig_t["r"] + tt_t["r"], "inter": t_inter,
        "er": t_inter / (ig_t["r"] + tt_t["r"]),
        "saves": ig_t["s"] + tt_t["s"], "shares": ig_t["shares"] + tt_t["shares"],
        "newf_ig": ig_t["newf"] + st_t["newf"],
    }
    totals["saves_share_inter"] = totals["saves"] / t_inter

    worst = min(pieces, key=lambda p: p["er"])
    valores = {
        "top_share_inter": best["share_inter"],
        "saves_share_inter": totals["saves_share_inter"],
        "min_er": worst["er"],
    }
    hallazgos = [{"v": valores[h["valor"]], "titulo": h["titulo"], "texto": " ".join(h["texto"].split())}
                 for h in camp["textos"]["hallazgos"]]

    share = [{"k": k, "ig": ig_t[key], "tt": tt_t[key]} for k, key in
             (("Visualizaciones", "v"), ("Alcance", "r"), ("Interacciones", "i"), ("Guardados", "s"), ("Compartidos", "shares"))]

    # Insights del resumen: cada frase de la plantilla se arma con estos valores.
    by_views = sorted(pieces, key=lambda p: p["v"], reverse=True)
    newf_best = max(pieces, key=lambda p: p["ig"]["newf"])
    ig_wins = [p for p in pieces if p["ig"]["er"] > p["tt"]["er"]]
    insights = {
        "views_per_reach": totals["views_all"] / totals["reach_all"],
        "tt_reach_share": tt_t["r"] / (ig_t["r"] + tt_t["r"]),
        "inter_per_100": totals["er"] * 100,
        "newf_best_piece": newf_best["s"],
        "newf_best_share": newf_best["ig"]["newf"] / totals["newf_ig"],
        "top_piece": by_views[0]["s"],
        "top_vs_second": by_views[0]["v"] / by_views[1]["v"],
        "second_piece": by_views[1]["s"],
        "low_piece": by_views[-1]["s"],
        "low_is_last_in_both": all(by_views[-1][k]["v"] == min(p[k]["v"] for p in pieces) for k in ("ig", "tt")),
        "ig_wins_er": len(ig_wins),
        "tt_wins_er_pieces": [p["s"] for p in pieces if p not in ig_wins],
        "n_pieces": len(pieces),
    }

    def net_insights(k: str, other: str) -> dict[str, Any]:
        n, o = (ig_t, tt_t) if k == "ig" else (tt_t, ig_t)
        top = max(pieces, key=lambda p: p[k]["v"])
        ps = [p[k] for p in pieces]
        return {
            "top_piece": top["s"], "top_share_views": top[k]["v"] / n["v"],
            "views_per_reach": n["v"] / n["r"],
            "saves_share": n["s"] / n["i"],
            "er_diff_pts": (n["er"] - o["er"]) * 100,
            "reach_vs_other": n["r"] / o["r"] - 1,
            "inter_vs_other": n["i"] - o["i"],
            "views_vs_other": n["v"] - o["v"],
            "n_alta": sum(1 for p in ps if p["er"] >= tasa["alta_desde"]),
            "low_piece": min(pieces, key=lambda p: p[k]["er"])["s"],
            "low_er": min(p["er"] for p in ps),
            "comments": sum(p["comments"] for p in ps),
            "comments_share": sum(p["comments"] for p in ps) / n["i"],
            "wins_vs_other": [p["s"] for p in pieces if p[k]["er"] > p[other]["er"]],
        }

    ins_ig = net_insights("ig", "tt")
    best_watch = max(pieces, key=lambda p: p["ig"]["watch_s"] or 0)
    newf_top = max(pieces, key=lambda p: p["ig"]["newf"])
    ins_ig.update(watch_best_piece=best_watch["s"], watch_best_s=best_watch["ig"]["watch_s"],
                  watch_best_is_newf_best=best_watch is newf_top, newf_top_piece=newf_top["s"],
                  newf_top_share=newf_top["ig"]["newf"] / ig_t["newf"], newf_top=newf_top["ig"]["newf"])
    ins_tt = net_insights("tt", "ig")
    shortest = min(pieces, key=lambda p: p["tt"]["dur_s"] or 1e9)
    longest = max(pieces, key=lambda p: p["tt"]["dur_s"] or 0)
    ins_tt.update(
        dur_min=shortest["tt"]["dur_s"], dur_max=longest["tt"]["dur_s"], shortest=shortest["s"], longest=longest["s"],
        shortest_is_top=shortest is max(pieces, key=lambda p: p["tt"]["v"]),
        longest_is_low=longest is min(pieces, key=lambda p: p["tt"]["v"]),
        women_max_piece=max(pieces, key=lambda p: p["tt"]["women"] or 0)["s"],
        women_max=max(p["tt"]["women"] or 0 for p in pieces),
        women_min_piece=min(pieces, key=lambda p: p["tt"]["women"] or 1)["s"],
        women_min=min(p["tt"]["women"] or 1 for p in pieces))

    tabs = ["resumen", "instagram", "tiktok"]
    return {
        "id": camp["id"], "marca": camp["marca"], "creador": camp["creador"], "periodo": camp["periodo"]["texto"],
        "textos": {"subtitulo": camp["textos"]["subtitulo"], "redes": camp["textos"]["redes"],
                   "historias": camp["textos"]["historias"]},
        "agencia": client["agencia"]["nombre"],
        "totals": totals, "insights": insights, "conv": build_conversation(conv or {}, pieces), "insIg": ins_ig, "insTt": ins_tt, "nets": {"ig": ig_t, "tt": tt_t}, "share": share, "pieces": pieces,
        "stories": stories, "storiesTotal": st_t, "hallazgos": hallazgos, "tabs": tabs,
        "pago": camp.get("pago_cop"), "fuente": met.get("fuente"), "importado": met.get("importado"),
    }
