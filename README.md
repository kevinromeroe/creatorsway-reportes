# Reportes de contenido · CreatorsWay

Reporte web de las campañas de los creadores de **CreatorsWay** con sus marcas, con un PDF descargable por pestaña.
Hecho por Datalítica. Primera campaña: **Juan Food Time × KLAREN'S** (julio a octubre de 2026).

## Qué muestra

| Pestaña | Contenido |
|---|---|
| **Resumen** | 5 cifras de la campaña, visualizaciones por pieza en las dos redes, resultados por red, lo que dice la gente (comentarios por tema y tono hacia la marca), hallazgos y detalle por pieza y red |
| **Instagram** | Cifras de los reels, visualizaciones y tasa por reel, retención y seguidores nuevos, conversación, detalle por reel e historias |
| **TikTok** | Cifras de los videos, visualizaciones y tasa por video, audiencia (no seguidores, mujeres y hombres), conversación y detalle por video |
| **Facebook** | Los mismos reels publicados en la página del creador: visualizaciones, reacciones, comentarios, compartidos, reparto frente a Instagram, conversación y detalle por reel |

La raíz `/` muestra la campaña de `portada` (config/cliente.yaml); cada campaña también vive en su carpeta (`/klarens-2026/`).
Cada pestaña tiene su PDF en `/<campaña>/pdf/<pestaña>.pdf`, que baja el botón **Descargar PDF**.

## Fuentes

- **Cifras públicas** (visualizaciones, me gusta o reacciones, comentarios, compartidos) de Instagram, TikTok y Facebook: las lee Datalítica con Claude en Chrome → `config/campanas/<id>/publicas.yaml`.
- **Cifras privadas** (alcance, guardados de Instagram, tiempo de reproducción, seguidores nuevos, audiencia de TikTok e historias): Excel del creador → `metricas.yaml`.
- Las visualizaciones de Instagram en el Excel incluyen las de Facebook (publicación cruzada); el reporte las separa. Detalle en [`docs/RUNBOOK.md`](docs/RUNBOOK.md#fuentes-de-datos-tres-redes-dos-orígenes).

## Fórmulas

Todas se calculan una sola vez en [`pipeline/metrics.py`](pipeline/metrics.py); la plantilla solo las formatea.

- **Interacciones** de un reel o video = me gusta + comentarios + compartidos + guardados (+ reposts en Instagram).
- **Tasa de interacción** = interacciones ÷ alcance, en Instagram y TikTok. Facebook no publica alcance: su indicador es interacciones ÷ visualizaciones. Alta desde 10 %, baja por debajo de 6 % ([`config/cliente.yaml`](config/cliente.yaml)).
- **Alcance de la campaña** = suma del alcance de cada pieza (una misma cuenta puede contarse en varias piezas).
- **Visualizaciones totales** = reels + videos + historias.
- **EMV y ROI**: apagados hasta tener el benchmark de la marca y el pago (`emv` en `cliente.yaml`, `pago_cop` en la campaña).

## Flujo

```
Excel del creador (Insights)          no se versiona
   │  scripts/importar_excel.py
   ▼
config/campanas/<id>/metricas.yaml    cifras
config/campanas/<id>/campana.yaml     piezas, nombres y textos curados
   │  scripts/build_reporte.py        ← en local
   ▼
<id>/index.html                       se revisa en local y se sube con Commit + Push
   │  workflow "Pruebas + PDF"        pruebas de cuadre + PDF por pestaña (Playwright)
   ▼
<id>/pdf/*.pdf  →  GitHub Pages
```

## Correr en local

```bash
pip install -r requirements.txt
python scripts/importar_excel.py klarens-2026 "ruta/al/Informe.xlsx"
python -m unittest discover tests
python scripts/build_reporte.py
python -m http.server 8812
```

Detalle de la operación en [`docs/RUNBOOK.md`](docs/RUNBOOK.md).
