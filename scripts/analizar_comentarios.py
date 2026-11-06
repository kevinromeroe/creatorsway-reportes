#!/usr/bin/env python3
"""analizar_comentarios.py — Clasifica los comentarios capturados y escribe conversacion.yaml.

Lee datos/capturas/<id>/klarens-{ig,tt}-<fecha>.json (locales, no se versionan; los captura
Claude en Chrome) y produce config/campanas/<id>/conversacion.yaml con cifras agregadas y
unos pocos comentarios de ejemplo sin nombre de usuario. Solo ese resumen se publica.

Cada comentario recibe un tema (reglas en orden de prioridad) y, si habla del suero o de la
marca, un tono hacia el producto.

Uso:
    python scripts/analizar_comentarios.py klarens-2026
    python scripts/analizar_comentarios.py klarens-2026 --muestra   # imprime ejemplos por tema
"""
from __future__ import annotations

import json
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
    "humor": "Humor y detalles del video",
    "receta": "Preguntas y adaptaciones de la receta",
    "fit": "Debate sobre si es fit",
    "marca": "El suero y la marca",
    "etiqueta": "Etiquetan a otra persona",
    "otros": "Otros",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


R = lambda p: re.compile(p)  # noqa: E731
FIT = R(r"\bfit\b|grasa|sodio|calori|carbohidrat|\bcarbo|saludable|sello|octogon|advertenci|etiquetas? negras|"
        r"\bdieta|macros|kcal|\bazucar|diabet|exceso|almidon|glucosa en sangre|fat\b|engorda")
MARCA = R(r"klaren|suero|suerito|alqueria|sinuano|sour cream|crema agria|natilla|lacteo|valledupar|vallenato|kumis")
HUMOR = R(r"tenedor|tene?dor|enedor|cubierto|celular|iphone|movil|telefono|\bcel\b|nevera|congelador|550|segundos|"
          r"tomillo|oregano|otros 1[89]|faltaron 19|falto 19|y los otros|dijo 20|"
          r"patacon|toston|papacon|jaja|jeje|xd\b|\bjsj")
RECETA = R(r"receta|papa|horno|freidora|airfryer|air fryer|minuto|tiempo|molde|galleta|cantidad|ingredient|reemplaz|"
           r"sustitu|cambiar|en lugar|en vez|consig|compr|salsa|carne|osobuco|osso|queso|bocadillo|limon|glucosa|"
           r"gelatina|grenetina|crema|olla|porcion|personas|tamano|medida|cascara|plato|preparar|philadelphia|achira|"
           r"arequipe|mermelada|yogur|platano|pasta|cebolla|vino|romero|zanahoria|ajo|paprika|sazon|especia")
PREGUNTA = R(r"\?|^(como|cuanto|cuantos|cuantas|donde|que puedo|con que|cual|puedo|se puede|si no tengo)\b")
ADAPTA = R(r"lo hare con|la hare con|lo hice con|la hice|lo hice|me quedo|no me quedo|no quedaron|se me (pegaron|desbarat)|"
           r"le falto|debiste|deberias|sacate un|hazlo con|podrias hacer|mejor con|con platano|con papa dulce|sin freidora|no tengo (freidora|airfryer|horno)")
POS = R(r"rico|ric[ou]ta|delici|deli\b|antojo|agua la boca|hambre|quiero|necesito|me encanta|amo\b|lo amo|"
        r"espectacular|brutal|increible|perfect|divin|sabros|uff|wow|woo|genial|excelente|top\b|favorit|"
        r"se ve|lo hare|la hare|tengo que hacer|hay que hacer|gracias|10 de 10|chevere|bacan|que vaina|belleza|"
        r"orgullo|el mejor|la mejor|mejor suero")
NEG_MARCA = R(r"malo|malisimo|feo|no me gusta|horrib|no es (suero|costeno)|nada de costeno|solo tiene el nombre|"
              r"industrial|quimico|procesad|alqueria|sinuano|casero|de verdad no|verdadero|propio suero|no sabe|sabe mal|"
              r"sabe a|exceso|sodio|grasa|sello|advertenci|octogon|sin marca|pueblo|botellita|bolsita")
POS_MARCA = R(r"mejor|rico|delici|deli\b|amo\b|lo amo|favorit|\bfav\b|top|espectacular|orgullo|uff|tapon del frasco|joya|"
              r"encant|chimba|buen|excelente|lo maximo|papa de los sueros|la dio toda|todo que ver|sabros|cajas|presente")
DUDA = R(r"que es (el |ese )?suero|suero es\b.*\?|lo mismo que|se (le )?conoce|reemplaz|sustitu|cambiar (el|por)|"
         r"en (lugar|vez) del? suero|no (lo )?(consigo|encuentro|venden|se consigue)|donde (consigo|comprar|puedo|se consigue)|"
         r"extranjero|europa|espana|panama|mexico|ecuador|argentina|omit|crema agria|sour cream|yogur|natilla|vinagre")
SALUD = R(r"exceso|sodio|grasa|sello|advertenci|octogon|fat|calori")
FUERA = R(r"extranjero|europa|espana|panama|mexico|ecuador|argentina|costa rica|brasil|venezuela|alemania|"
          r"no (lo )?(consigo|encuentro|venden|se consigue)|aqui no|donde vivo|mi pais|soy de")
EMOJI_POS = set("😍🤤😋❤🔥👏🥰😻🙌💯✨👌🫠🤩💖💙💚♥😮")
EMOJI_HUMOR = set("😂🤣😆😹")


def tema(t: str) -> str:
    n = norm(t)
    letras = re.sub(r"[^a-z]", "", re.sub(r"@\S+", "", n))
    if not letras:  # solo emojis, menciones o signos
        if re.fullmatch(r"(@\S*\s*)+", n):  # "@" solo: etiqueta anonimizada
            return "etiqueta"
        chars = set(t)
        if chars & EMOJI_HUMOR:
            return "humor"
        if chars & EMOJI_POS:
            return "antojo"
        return "otros"
    if FIT.search(n):
        return "fit"
    if MARCA.search(n):
        return "marca"
    if HUMOR.search(n):
        return "humor"
    if ADAPTA.search(n) or (PREGUNTA.search(t if "?" in t else n) and RECETA.search(n)):
        return "receta"
    if POS.search(n):
        return "antojo"
    return "otros"


def tono_marca(t: str) -> str | None:
    """Tono hacia el suero/la marca, solo si el comentario lo menciona."""
    n = norm(t)
    if not MARCA.search(n) and not re.search(r"\bsuero|klaren", n):
        return None
    neg, pos = bool(NEG_MARCA.search(n)), bool(POS_MARCA.search(n))
    if DUDA.search(n) and not (pos and "klaren" in n):
        return "duda"   # qué es, dónde se consigue o con qué reemplazarlo
    if "?" in t and not pos:
        return "duda"
    if not pos and set(t) & EMOJI_POS:
        pos = True
    if neg and not pos:
        return "negativo"
    if pos and not neg:
        return "positivo"
    if pos and neg:  # "el klarens es mejor que el casero" → positivo si nombra a la marca
        return "positivo" if "klaren" in n else "negativo"
    return "neutro"


def cargar(cid: str) -> dict[str, list[dict]]:
    base = ROOT / "datos" / "capturas" / cid
    out = {}
    for f in sorted(base.glob("klarens-*-*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out[f"{ {'instagram': 'ig', 'tiktok': 'tt', 'facebook': 'fb'}[d['red']] }|{d['fecha']}"] = d
    return out


def main() -> int:
    cid = sys.argv[1]
    muestra = "--muestra" in sys.argv
    camp = load_campaign(cid)
    caps = cargar(cid)
    piezas = {str(p["fecha"]): p for p in camp["piezas"]}
    marca_handle = camp["marca"]["handle"].lower()

    resumen = {"temas": TEMAS, "redes": {}, "piezas": {}, "total": {}}
    tot_temas, tot_tono, tot_n, tot_cap = Counter(), Counter(), 0, 0
    ejemplos: dict[str, list] = defaultdict(list)
    por_red: dict[str, dict] = {}
    for key, d in caps.items():
        red, fecha = key.split("|")
        cs = [c for c in d["comentarios"] if (c.get("t") or "").strip()]
        temas, tonos = Counter(), Counter()
        padre_tema: dict[str, str] = {}
        ultimo = "otros"
        for c in cs:
            tm = tema(c["t"])
            if not c.get("p"):
                ultimo = tm
                padre_tema[str(c.get("id"))] = tm
            elif tm in ("otros", "etiqueta"):  # la respuesta sigue el tema de su hilo
                tm = padre_tema.get(str(c.get("parent")), ultimo) if c.get("parent") else ultimo
            temas[tm] += 1
            tn = tono_marca(c["t"])
            if tn:
                tonos[tn] += 1
                nn = norm(c["t"])
                if tn == "negativo":
                    tonos["neg_salud" if SALUD.search(nn) else "neg_autenticidad"] += 1
                if tn == "duda" and FUERA.search(nn):
                    tonos["duda_fuera"] += 1
            ejemplos[tm].append((c.get("l", 0), red, fecha, c["t"]))
        pz = piezas[fecha]
        resumen["piezas"].setdefault(pz["slug"], {})[red] = {
            "capturados": len(cs), "total_plataforma": d["total"],
            "temas": dict(temas), "tono_marca": dict(tonos),
        }
        r = por_red.setdefault(red, {"capturados": 0, "total_plataforma": 0, "temas": Counter(), "tono_marca": Counter()})
        r["capturados"] += len(cs); r["total_plataforma"] += d["total"]; r["temas"] += temas; r["tono_marca"] += tonos
        tot_temas += temas; tot_tono += tonos; tot_n += len(cs); tot_cap += d["total"]
    resumen["redes"] = {k: {**v, "temas": dict(v["temas"]), "tono_marca": dict(v["tono_marca"])} for k, v in por_red.items()}
    resumen["total"] = {"capturados": tot_n, "total_plataforma": tot_cap, "temas": dict(tot_temas), "tono_marca": dict(tot_tono)}
    # Comentarios destacados: los de más me gusta por tema (sin usuarios ni menciones)
    destacados = {}
    for tm, lst in ejemplos.items():
        if tm in ("otros", "etiqueta"):  # no se publican ejemplos fuera de tema
            continue
        lst.sort(key=lambda x: -x[0])
        dest = []
        for likes, red, fecha, t in lst:
            limpio = re.sub(r"@\S+", "", t).strip()
            if len(re.sub(r"[^A-Za-zÁÉÍÓÚáéíóúñ]", "", limpio)) < 12 or marca_handle in norm(t):
                continue
            dest.append({"texto": limpio[:180], "me_gusta": likes, "red": red, "pieza": piezas[fecha]["slug"]})
            if len(dest) == 3:
                break
        destacados[tm] = dest
    resumen["destacados"] = destacados
    out = CAMPAIGNS_DIR / cid / "conversacion.yaml"
    out.write_text("# Generado por scripts/analizar_comentarios.py — no editar a mano.\n"
                   + yaml.safe_dump(resumen, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"[OK] {out.relative_to(ROOT)}: {tot_n} comentarios clasificados de {tot_cap}")
    print({TEMAS[k]: v for k, v in tot_temas.most_common()}, dict(tot_tono))
    if muestra:
        for tm in TEMAS:
            print(f"\n== {TEMAS[tm]} ({tot_temas[tm]})")
            for likes, red, fecha, t in sorted(ejemplos[tm], key=lambda x: -x[0])[:14]:
                print(f"  {red} {fecha} [{likes}] {re.sub(chr(10), ' ', t)[:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
