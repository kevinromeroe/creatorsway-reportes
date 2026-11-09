#!/usr/bin/env python3
"""analizar_comentarios_creadores.py — Conversación de una campaña con varios creadores.

Lee datos/capturas/<id>/{ig,tt}-comentarios.txt (locales, no se versionan; los captura Claude en
Chrome sin nombres de usuario) y escribe config/campanas/<id>/conversacion.yaml con cifras
agregadas y unos pocos comentarios de ejemplo. Solo ese resumen se publica.

Formato de captura (una línea por comentario):
    #<código del reel o id del video> <total que reporta la plataforma>
    tipo|autor|me_gusta|texto      tipo c = comentario, rN = respuesta al comentario N de la publicación
                                   autor C = el creador de la publicación; vacío = público
Las respuestas de los creadores no cuentan como conversación del público: se cuentan aparte.

Cada comentario del público recibe un tema y, si habla del aceite, del esparcible o de la marca,
un tono hacia el producto (negativo, duda, positivo o neutro). Las reglas son de Canola Life;
para otra marca se ajustan las listas de palabras de este archivo.

Uso:
    python scripts/analizar_comentarios_creadores.py canola-2026
    python scripts/analizar_comentarios_creadores.py canola-2026 --muestra   # ejemplos por tema y tono
"""
from __future__ import annotations

import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.util.config import CAMPAIGNS_DIR, load_campaign  # noqa: E402

TEMAS = {
    "antojo": "Antojo y elogio",
    "receta": "Preguntas y ajustes de la receta",
    "producto": "Dudas sobre el producto",
    "critica": "Críticas y debate sobre el aceite",
    "pedido": "Piden otra receta",
    "preparo": "Ya la prepararon",
    "humor": "Humor y comunidad",
    "etiqueta": "Etiquetan a otra persona",
    "otros": "Otros",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


R = lambda p: re.compile(p)  # noqa: E731
# Menciones del producto: el aceite, el esparcible (margarina de canola), la marca o la pauta.
MARCA = R(r"canola|canela life|aceite|esparcible|esparcir|margarina|untable|mantequilla|\bproducto\b|grasa|"
          r"publicidad|anuncio|patrocin|inflamac|arteria|cancer|toxic")
DEFENSA = R(r"recomendo usar aceite de canola|opcion saludable|no sabia que ese aceite|dejen de satanizar|"
            r"uso la misma marca")
NEGATIVO = R(r"salud|inflamat|inflamac|arteria|cancer|toxic|intoxic|danin|nociv|\bmal[oa]\b|malisim|lo peor|"
             r"para (maquinas|el coche|carro)|de carro|ultra ?procesad|hidrogenad|asesino|gonorrea|"
             r"aceites vegetales|grasas vegetales|grasa vegetal|terrible|eliminad|comestible|no va\b|"
             r"me perdiste|todo (iba )?bien (hasta|menos)|nunca mas|mejor (con )?mantequilla|mas sana|"
             r"menos mala|manteca|aceite de coco|de oliva|aguacate|gourmet|estas recomendando|"
             r"no me gusta freir|sin valores|esencia")
NEG_EMOJI = set("😢😭😞🥲")
PUBLICIDAD = R(r"publicidad|anuncio|pagando|patrocin|por plata|pautas|ganarse la plata")
DUDA = R(r"\?|que es|qtr|significa|se consigue|aclarame|misma duda|se refiere|cantidad")
FUERA = R(r"miami|\busa\b|mexico|argentin|vzla|venezuela|espana|chile|peru|ecuador")
ESPARCIBLE = R(r"esparcible|esparcir|untable|margarina")

PEDIDO = R(r"ensenanos|ensenamos|ensananos|me ensenas|^ensen|encurtid|en curtidos|^cebolla|hacer la cebolla|las cebollas|^receta|recetas del mundia+l|chimichurri|hagan una|una saludable|receta de postre|recetas del mundial|"
           r"plato de colombia|argentina para cuando|una pasta|toca grabar|me compartes")
PREPARO = R(r"los hice|la hice|lo hice|prepare tu receta|los he hecho|me quedaron|me quedo|quedaron brutales|"
            r"acabo de hacer|yo lo he preparado|yo los he preparado|me salen|me han salido")
RECETA = R(r"cantidad|molde|porcion|cuantos salen|gramos|\bgr\b|\bml\b|horno|hornear|freidora|air ?fryer|"
           r"sarten|cacerola|harina|queso crema|vinagre|waffle|freezer|refriger|temperatura|cuanto dura|"
           r"conserv|dura la|conseguir|picante|panko|panco|pan o\b|arequipe|manga|chocolate|crema|tsp|cucharad|pulverizad|medidas|"
           r"papel|en vez|en lugar|reemplaz|sustitu|cambiar|tip\b|ciernan|salsa|camarones|garbanzos|limon|"
           r"cocid|airfryer|pinchos|ralladura|tinto|rentable|azucar|bicarbonato|polvo de hornear")
PREGUNTA = R(r"\?|^(como|cuanto|cuantos|cuantas|donde|que|cual|puedo|se puede|hola)\b|si no tengo|me puedes decir|"
             r"me podrias|me dices|te referis|te refieres|me gustaria saber")
HUMOR = R(r"jaja|jsj|jeje|parecen (fresas|tomates)|tomate|silvy|domicilio|voz de|mal ensenando|rodar|nonna|dulcera|"
          r"ignorar tu contenido|piedad|partir los bizcocho|millonaria|sola?o para mi|crisis|quiero ser tu amiga|"
          r"que parche|morat|rodilla|pa cuando|abres aca")
POS = R(r"ric[oa]|ricur|riquisim|delici|\bdeli|antoj|hambre|quiero|necesito|encant|\bamo+\b|espectacular|brutal|"
        r"increible|perfect|divin|sabros|\buf+|wo+w|wao|genial|excelente|top|favorit|se ve|se ven|lo hare|la hare|"
        r"las voy|los voy|gracias|bellez|lind|bello|fantastic|buenisim|maravill|tremend|crocante|master|la mejor|"
        r"el mejor|talentosa|arte|yum+|nami|dame|dio+s|omg|pasada|recetaza|me apunto|munchies|pinton|interesante|"
        r"pinta|me pido|muero|bueno|que cosa|perfectas|lindura|te pasaste|queee|amiga|apunto|grosería|groseria")
EMOJI_POS = set("😍🤤😋❤🔥👏🥰😻🙌💯✨👌🫠🤩💖💙💚♥😮🤌🧡💛🫶")
EMOJI_HUMOR = set("😂🤣😆😹")


def tono(t: str) -> str | None:
    """Tono hacia el producto, solo si el comentario habla del aceite, el esparcible o la marca."""
    n = norm(t)
    if not MARCA.search(n):
        return None
    if DEFENSA.search(n):
        return "positivo"
    if NEGATIVO.search(n) or set(t) & NEG_EMOJI:
        return "negativo"
    if DUDA.search(t if "?" in t else n):
        return "duda"
    return "neutro"


def tema(t: str, tn: str | None) -> str:
    n = norm(t)
    if tn == "negativo" or (tn == "positivo" and "opcion saludable" in n):
        return "critica"
    if tn == "duda":
        return "producto"
    letras = re.sub(r"[^a-z]", "", re.sub(r"@\S*", "", n))
    if not letras:  # solo emojis, menciones o vacío (sticker o GIF)
        if n and re.fullmatch(r"(@\S*\s*)+", n):
            return "etiqueta"
        if set(t) & EMOJI_HUMOR:
            return "humor"
        if set(t) & EMOJI_POS:
            return "antojo"
        return "otros"
    if PEDIDO.search(n):
        return "pedido"
    if PREPARO.search(n):
        return "preparo"
    if RECETA.search(n) and (PREGUNTA.search(t if "?" in t else n) or "en vez" in n or "tip" in n):
        return "receta"
    if PREGUNTA.search(t if "?" in t else n) and RECETA.search(n):
        return "receta"
    if HUMOR.search(n) or set(t) & EMOJI_HUMOR:
        return "humor"
    if POS.search(n) or set(t) & EMOJI_POS:
        return "antojo"
    return "otros"


def cargar(cid: str) -> dict[str, dict]:
    """{código: {"red", "total", "cs": [{"i","p","c","l","t"}]}} desde los .txt de captura."""
    base = ROOT / "datos" / "capturas" / cid
    out: dict[str, dict] = {}
    for red in ("ig", "tt"):
        cur = None
        for line in (base / f"{red}-comentarios.txt").read_text(encoding="utf-8").splitlines():
            if line.startswith("# ") or line.startswith("#\t") or not line.strip():
                continue
            if line.startswith("#"):
                code, total = line[1:].split()
                cur = out[code] = {"red": red, "total": int(total), "cs": []}
                continue
            tipo, autor, likes, texto = line.split("|", 3)
            cur["cs"].append({"i": len(cur["cs"]), "p": int(tipo[1:]) if tipo.startswith("r") else None,
                              "c": autor == "C", "l": int(likes), "t": texto})
    return out


def main() -> int:
    cid = sys.argv[1]
    muestra = "--muestra" in sys.argv
    camp = load_campaign(cid)
    caps = cargar(cid)
    piezas = {str(p["codigo"]): p for p in camp["piezas"]}
    faltan = sorted(set(piezas) - set(caps))
    if faltan:
        raise SystemExit(f"Faltan comentarios de: {faltan}")

    tot_t, tot_tono, sub = Counter(), Counter(), Counter()
    por_red: dict[str, dict] = {}
    por_pieza: dict[str, dict] = {}
    ejemplos: dict[str, list] = defaultdict(list)
    ej_tono: dict[str, list] = defaultdict(list)
    n_pub = n_creador = n_total = preguntas = respondidas = 0
    for code, d in caps.items():
        red, pz = d["red"], piezas[code]
        temas, tonos = Counter(), Counter()
        tema_de: dict[int, str] = {}
        resp_creador = {c["p"] for c in d["cs"] if c["c"] and c["p"] is not None}
        pub = 0
        for c in d["cs"]:
            if c["c"]:
                n_creador += 1
                continue
            pub += 1
            tn = tono(c["t"])
            tm = tema(c["t"], tn)
            if c["p"] is not None and tm in ("otros", "etiqueta"):
                tm = tema_de.get(c["p"], tm)  # la respuesta sigue el tema de su hilo
            tema_de[c["i"]] = tm
            temas[tm] += 1
            if tn:
                tonos[tn] += 1
                nn = norm(c["t"])
                if tn == "negativo" and PUBLICIDAD.search(nn):
                    sub["neg_publicidad"] += 1
                if tn == "duda" and ESPARCIBLE.search(nn):
                    sub["duda_esparcible"] += 1
                if tn == "duda" and FUERA.search(nn):
                    sub["duda_fuera"] += 1
                ej_tono[tn].append((c["l"], red, pz, c["t"]))
            if c["p"] is None and "?" in c["t"]:
                preguntas += 1
                respondidas += c["i"] in resp_creador
            ejemplos[tm].append((c["l"], red, pz, c["t"]))
        por_pieza[code] = {"red": red, "creador": pz["creador"], "capturados": pub, "total_plataforma": d["total"],
                           "temas": dict(temas), "tono": dict(tonos)}
        r = por_red.setdefault(red, {"capturados": 0, "total_plataforma": 0, "temas": Counter(), "tono": Counter()})
        r["capturados"] += pub; r["total_plataforma"] += d["total"]; r["temas"] += temas; r["tono"] += tonos
        tot_t += temas; tot_tono += tonos; n_pub += pub; n_total += d["total"]

    def destacar(lst, k=3, excluir=None):
        out = []
        for likes, red, pz, t in sorted(lst, key=lambda x: -x[0]):
            limpio = re.sub(r"@\S*", "", t).strip()
            if len(re.sub(r"[^A-Za-zÁÉÍÓÚáéíóúñ]", "", limpio)) < 12 or (excluir and excluir.search(norm(t))):
                continue
            out.append({"texto": limpio[:200], "me_gusta": likes, "red": red, "pieza": pz["titulo"], "creador": pz["creador"]})
            if len(out) == k:
                break
        return out

    resumen = {
        "temas": TEMAS,
        "total": {"publico": n_pub, "total_plataforma": n_total, "respuestas_creadores": n_creador,
                  "preguntas": preguntas, "preguntas_respondidas": respondidas,
                  "temas": dict(tot_t), "tono": dict(tot_tono), **dict(sub)},
        "redes": {k: {**v, "temas": dict(v["temas"]), "tono": dict(v["tono"])} for k, v in por_red.items()},
        "piezas": por_pieza,
        "destacados": {tm: destacar(lst) for tm, lst in ejemplos.items() if tm not in ("otros", "etiqueta")},
        "destacados_tono": {tn: destacar(lst) for tn, lst in ej_tono.items()},
    }
    out = CAMPAIGNS_DIR / cid / "conversacion.yaml"
    out.write_text("# Generado por scripts/analizar_comentarios_creadores.py — no editar a mano.\n"
                   + yaml.safe_dump(resumen, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"[OK] {out.relative_to(ROOT)}: {n_pub} comentarios del público ({n_creador} respuestas de creadores) "
          f"de {n_total} que reportan las plataformas")
    print({TEMAS[k]: v for k, v in tot_t.most_common()}, dict(tot_tono), dict(sub), f"preguntas {respondidas}/{preguntas}")
    if muestra:
        for tm in TEMAS:
            print(f"\n== {TEMAS[tm]} ({tot_t[tm]})")
            for likes, red, pz, t in sorted(ejemplos[tm], key=lambda x: -x[0]):
                print(f"  {red} {pz['creador'][:12]:12} [{likes}] {t[:100]}")
        for tn in ("negativo", "duda", "positivo", "neutro"):
            print(f"\n## tono {tn} ({tot_tono[tn]})")
            for likes, red, pz, t in sorted(ej_tono[tn], key=lambda x: -x[0]):
                print(f"  {red} {pz['creador'][:12]:12} [{likes}] {t[:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
