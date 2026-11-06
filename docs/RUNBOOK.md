# RUNBOOK · Reportes CreatorsWay

Sitio: **https://creatorsway.datalitica.com.co** · Repo público `kevinromeroe/creatorsway-reportes` (GitHub Pages).

## Roles

- **Kevin** recibe el Excel del creador, hace el DNS y revisa el reporte y los PDF antes de compartirlos.
- **Claude** importa, edita, prueba, construye y sube los cambios desde el clon local (`Documents/GitHub/creatorsway-reportes`).
- El workflow **Pruebas + PDF** corre en GitHub al subir cambios: pasa las pruebas, regenera los PDF y los sube.

## Cómo está organizado

```
config/cliente.yaml                     agencia, umbrales de la tasa y `portada` (campaña que se ve en la raíz)
config/campanas/<id>/campana.yaml       marca, creador, piezas, nombres de historias y textos curados
config/campanas/<id>/metricas.yaml      cifras importadas del Excel (no se edita a mano)
assets/                                 logos (sin fondo)
templates/reporte.html                  diseño aprobado: Resumen, Instagram y TikTok
index.html                              la raíz muestra la campaña de `portada`
<id>/index.html y <id>/pdf/             reporte y PDF de cada campaña
legal/                                  términos de uso y política de datos (Ley 1581 de 2012)
```

El `<id>` de una campaña es `<marca>-<año>`, por ejemplo `klarens-2026`.

## Formato del Excel que entrega el creador

Un archivo con tres hojas, con la fila de encabezados empezando en «ID contenido» o «ID historia»:

| Hoja | Columnas que se leen (por nombre) |
|---|---|
| **Instagram reels** | ID contenido, Fecha publicación, Enlace, Visualizaciones, Alcance / espectadores, Me gusta, Comentarios, Reposts, Compartidos, Guardados, Tiempo promedio reproducción (s), Nuevos seguidores, Colaboración, Precisión |
| **TikTok videos** | ID contenido, Fecha publicación, Hora, Enlace, Duración (s), Visualizaciones, Alcance / total espectadores, Me gusta, Comentarios, Compartidos, Guardados, Espectadores nuevos %, Espectadores recurrentes %, No seguidores %, Seguidores %, Hombres %, Mujeres %, Precisión |
| **Instagram stories** | ID historia, Fecha, Descripción, Espectadores, Visualizaciones, Interacciones, Me gusta, Respuestas, Compartidos, Toques en sticker, Toques en enlace, Avances, Retrocesos, Abandonos, Siguiente historia, Visitas al perfil, Nuevos seguidores, Seguidores %, No seguidores %, Notas |

- Una pieza de contenido fijo es un reel y un video publicados **el mismo día**: la fecha los une.
- En **Notas** de cada historia va el sticker, por ejemplo `Sticker: @klarenscol`. Así el reporte cuenta solo los toques al sticker de la marca.
- Si cambia el nombre de una columna, el importador se detiene y dice cuál falta.
- El Excel **nunca** se sube al repo: se guarda en `Dashboard Comapan/Juan-Food-Time/insumos/datos/` (o la carpeta del creador).

## A. Actualizar las cifras de una campaña existente

1. Guardar el Excel nuevo en la carpeta de insumos del creador.
2. Importar (en **PowerShell**, porque la ruta tiene tildes):
   ```powershell
   cd C:\Users\kevin\Documents\GitHub\creatorsway-reportes
   python scripts/importar_excel.py klarens-2026 "<ruta completa del Excel>"
   ```
3. Correr las pruebas:
   ```powershell
   python -m unittest discover tests
   ```
   Las pruebas comparan los porcentajes escritos a mano en `campana.yaml` (notas y hallazgos) con las cifras nuevas.
   Si una falla, actualizar ese texto y, si cambió una cifra esperada, la prueba correspondiente en `tests/test_metrics.py`.
4. Construir y revisar en local:
   ```powershell
   python scripts/build_reporte.py
   python -m http.server 8812
   ```
   Abrir `http://localhost:8812/` y revisar Resumen, Instagram y TikTok.
5. Subir: commit + push a `main`. El workflow regenera los PDF y GitHub Pages publica en uno o dos minutos.

Los insights que acompañan cada cifra se calculan solos desde los datos (`pipeline/metrics.py`), así que se actualizan con el Excel.
Los textos curados (hallazgos, notas por pieza, texto de redes e historias) sí se revisan a mano.

## B. Agregar una pieza o una historia a la campaña

1. Agregar la fila en el Excel (mismo día en Instagram y TikTok si es contenido fijo).
2. En `campana.yaml`:
   - pieza nueva: `slug`, `fecha`, `titulo`, `corto`, `nota` y, si aplica, `colaboracion`;
   - historia nueva: su nombre visible en la lista `historias`, en el mismo orden del Excel.
3. Seguir los pasos 2 a 5 de la sección A.

## C. Campaña nueva (otra marca u otro creador)

1. **Insumos:** Excel con el formato de arriba y el logo de la marca **sin fondo** (PNG transparente) en `assets/logo-<marca>-sin-fondo.png`.
2. **Carpeta de la campaña:** copiar `config/campanas/klarens-2026/` a `config/campanas/<marca>-<año>/` y editar `campana.yaml`:
   - `id`, `marca` (nombre, handle sin @, logo), `creador`, `periodo`, `pago_cop: null`;
   - `piezas`, `historias` y `textos` (subtítulo, redes, historias y los tres hallazgos).
   Borrar el `metricas.yaml` copiado: lo genera el importador.
3. **Importar y construir:**
   ```powershell
   python scripts/importar_excel.py <marca>-<año> "<ruta del Excel>"
   python scripts/build_reporte.py <marca>-<año>
   ```
4. **Pruebas:** agregar en `tests/test_metrics.py` una clase de cuadre para la campaña nueva, copiando la de KLAREN'S con las cifras del Excel nuevo. Correr `python -m unittest discover tests`.
5. **Qué se ve en la raíz:** si la campaña nueva debe ser la que se abre en `https://creatorsway.datalitica.com.co/`, cambiar `portada` en `config/cliente.yaml`. Las demás quedan en `https://creatorsway.datalitica.com.co/<marca>-<año>/`.
6. **Revisar en local y subir** (pasos 4 y 5 de la sección A).

## D. Comentarios de las publicaciones (conversación)

Las secciones "Lo que dice la gente" (Resumen) y "Conversación en Instagram/TikTok" salen de los comentarios públicos de cada publicación.

1. **Captura con Claude en Chrome** (sesión de Instagram iniciada en Chrome; TikTok no la necesita). Claude abre cada publicación y, desde la misma página, lee los comentarios y sus respuestas con la API interna del sitio:
   - Instagram: `/api/v1/media/<id>/comments/` y `/child_comments/` (el `<id>` sale del código del enlace del reel), con pausas entre páginas.
   - TikTok: `/api/comment/list/` y `/api/comment/list/reply/` con el `aweme_id` del video (los enlaces `vt.tiktok.com` redirigen al video).
   Se guarda texto, me gusta y si es respuesta. **No se guardan nombres de usuario.**
2. **Guardado:** Chrome descarga un JSON por publicación (`klarens-ig-<fecha>.json`, `klarens-tt-<fecha>.json`) a Descargas (Chrome pide permitir varias descargas). Se mueven a `datos/capturas/<campaña>/`, que **no** se sube al repo.
3. **Análisis:**
   ```powershell
   python scripts/analizar_comentarios.py klarens-2026 --muestra
   ```
   Clasifica cada comentario en un tema (antojo y elogio, humor del video, el suero y la marca, debate fit, preguntas de receta, etiquetas, otros; las respuestas heredan el tema de su hilo) y, si habla del suero o de la marca, su tono (positivo, negativo, duda). Con `--muestra` imprime ejemplos por tema para revisar que las reglas clasifiquen bien; si algo queda mal, se ajustan las reglas del script.
4. Escribe `config/campanas/<campaña>/conversacion.yaml` con cifras agregadas y tres comentarios destacados sin usuario: es lo único que se publica.
5. Pruebas, build, revisión y subida (pasos 3 a 5 de la sección A). Las pruebas verifican las cifras que citan los textos.

Las plataformas no exponen todos los comentarios (borrados, filtrados u ocultos): el reporte dice cuántos se leyeron frente al total que reporta cada plataforma.

## EMV y ROI

Están apagados (`emv: null` en `cliente.yaml`, `pago_cop: null` en la campaña). Se activan cuando se tenga el pago de la marca y el benchmark de EMV acordado para ella.

## PDF en local

Con el servidor local en el puerto 8812:

```bash
PYTHONIOENCODING=utf-8 PDF_BASE_URL=http://localhost:8812 python scripts/render_pdf.py klarens-2026
```

## Publicación (hecha el 6 de noviembre de 2026)

1. DNS de `datalitica.com.co`: registro `CNAME  creatorsway  →  kevinromeroe.github.io` (lo hace Kevin).
2. Repo público `kevinromeroe/creatorsway-reportes`. `robots.txt` y la etiqueta `noindex` bloquean a los buscadores.
3. *Settings → Pages → Deploy from a branch → main / (root)*. El dominio se toma del archivo `CNAME`.
4. Cuando GitHub emite el certificado: *Enforce HTTPS*.
