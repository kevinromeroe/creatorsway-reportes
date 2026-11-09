# RUNBOOK · Reportes CreatorsWay

Sitio: **https://creatorsway.datalitica.com.co** · Repo público `kevinromeroe/creatorsway-reportes` (GitHub Pages).

## Roles

- **Kevin** recibe el Excel del creador, hace el DNS y revisa el reporte y los PDF antes de compartirlos.
- **Claude** importa, edita, prueba, construye y sube los cambios desde el clon local (`Documents/GitHub/creatorsway-reportes`).
- El workflow **Pruebas + PDF** corre en GitHub al subir cambios: pasa las pruebas, regenera los PDF y los sube.

## Cómo está organizado

```
config/cliente.yaml                     agencia y umbrales de la tasa
config/campanas/<id>/campana.yaml       marca, creador, piezas, nombres de historias y textos curados
config/campanas/<id>/metricas.yaml      cifras privadas importadas del Excel (no se edita a mano)
config/campanas/<id>/publicas.yaml      cifras públicas de Instagram, TikTok y Facebook (las captura Datalítica)
config/campanas/<id>/conversacion.yaml  resumen de comentarios (scripts/analizar_comentarios*.py)
assets/                                 logos (sin fondo)
templates/reporte.html                  diseño aprobado, campaña de un creador: Resumen, Instagram, TikTok y Facebook
templates/reporte-creadores.html        campaña con varios creadores (toma los estilos de reporte.html)
templates/portada.html                  raíz del sitio: una tarjeta por campaña
index.html                              la portada (la genera scripts/build_reporte.py)
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

## Fuentes de datos: tres redes, dos orígenes

Cada pieza de contenido fijo se publica el mismo día en **Instagram** (reel), **TikTok** (video) y **Facebook** (el mismo reel, por publicación cruzada desde Instagram, en la página oficial del creador; para Juan Food Time es «Juan FoodTime», `facebook.com/foodtimecali`).

| Dato | De dónde sale | Archivo |
|---|---|---|
| Visualizaciones, me gusta o reacciones, comentarios y compartidos de las 3 redes; guardados de TikTok | **Público**, lo lee Datalítica en cada plataforma con Claude en Chrome | `publicas.yaml` |
| Alcance de Instagram y TikTok, guardados y reposts de Instagram, tiempo de reproducción, seguidores nuevos, audiencia de TikTok e historias | **Privado**, del Excel del creador (Instagram Insights y TikTok Studio) | `metricas.yaml` |
| Comentarios de las 3 redes | **Público**, captura local | `datos/capturas/` (no se sube) → `conversacion.yaml` |

Reglas:

- **Las cifras públicas mandan.** Si una métrica existe en las dos fuentes, el reporte usa la pública (es exacta; el Excel copia valores abreviados como 156 K).
- **Ojo con la publicación cruzada.** En Instagram Insights, «Visualizaciones» suma Instagram + Facebook. Por eso las visualizaciones de Instagram se toman de la cifra pública **solo de Instagram** (`ig_play_count`) y las de Facebook (`fb_play_count`) van en su propia red. Con esto la validación del 6 de noviembre de 2026 encontró que el 38 % de lo que el Excel atribuía a Instagram era de Facebook (`docs/VALIDACION_2026-11-06.md`).
- **Facebook no publica alcance ni guardados.** Su tasa es interacciones ÷ visualizaciones y no entra en la tasa de la campaña, que se calcula con Instagram y TikTok. Sus reacciones desde 10 mil vienen abreviadas (se marcan con ≈).

### Cómo se capturan las cifras públicas (Claude en Chrome)

- **Instagram** (sesión iniciada en Chrome): `/api/v1/media/<id>/info/` con el encabezado `x-ig-app-id: 936619743392459`; el `<id>` sale del código del enlace del reel. Campos: `ig_play_count`, `fb_play_count`, `like_count`, `comment_count`, `reshare_count`. Los guardados no son públicos.
- **TikTok** (sin sesión): la página de cada video trae `__UNIVERSAL_DATA_FOR_REHYDRATION__` → `itemStruct.statsV2` (`playCount`, `diggCount`, `commentCount`, `shareCount`, `collectCount`). Los enlaces `vt.tiktok.com` redirigen al video.
- **Facebook** (sesión iniciada en Chrome): en `facebook.com/<página>/reels/` se ubican los reels por fecha y por las visualizaciones que da `fb_play_count`. En `facebook.com/reel/<id>`, los botones traen el dato en su `aria-label`: «Me gusta, N reacciones», «Comentario, N comentarios», «Compartir, N veces compartido».

Las cifras se escriben en `publicas.yaml` con la fecha de captura.

## A. Actualizar las cifras de una campaña existente

1. Capturar las cifras públicas de las 3 redes y actualizar `publicas.yaml` (sección «Fuentes de datos»). Guardar el Excel nuevo en la carpeta de insumos del creador.
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
5. **Portada:** la raíz `https://creatorsway.datalitica.com.co/` lista todas las campañas (la más reciente primero, por `periodo.hasta`); cada una vive en `https://creatorsway.datalitica.com.co/<marca>-<año>/`.
6. **Revisar en local y subir** (pasos 4 y 5 de la sección A).

## D. Comentarios de las publicaciones (conversación)

Las secciones "Lo que dice la gente" (Resumen) y "Conversación en Instagram/TikTok" salen de los comentarios públicos de cada publicación.

1. **Captura con Claude en Chrome** (sesión de Instagram y Facebook iniciada en Chrome; TikTok no la necesita). Claude abre cada publicación y, desde la misma página, lee los comentarios y sus respuestas con la API interna del sitio:
   - Instagram: `/api/v1/media/<id>/comments/` y `/child_comments/` (el `<id>` sale del código del enlace del reel), con pausas entre páginas.
   - TikTok: `/api/comment/list/` y `/api/comment/list/reply/` con el `aweme_id` del video (los enlaces `vt.tiktok.com` redirigen al video).
   - Facebook: en `facebook.com/reel/<id>` se abre el panel de comentarios, se cambia el orden a «Todos los comentarios», se pulsan los «Ver respuestas» y se leen los `div[role="article"]`. Se quitan los nombres de quien comenta y de las personas etiquetadas (las etiquetas quedan como «@»).
   Se guarda texto, me gusta y si es respuesta. **No se guardan nombres de usuario.**
2. **Guardado:** Chrome descarga un JSON por publicación (`klarens-ig-<fecha>.json`, `klarens-tt-<fecha>.json`, `klarens-fb-<fecha>.json`) a Descargas. Chrome pide permitir varias descargas por sitio, y solo descarga si la descarga se lanza en una llamada aparte de la captura (no después de una espera larga). Si bloquea, se leen los comentarios como texto y se escribe el archivo a mano. Se mueven a `datos/capturas/<campaña>/`, que **no** se sube al repo.
3. **Análisis:**
   ```powershell
   python scripts/analizar_comentarios.py klarens-2026 --muestra
   ```
   Clasifica cada comentario en un tema (antojo y elogio, humor del video, el suero y la marca, debate fit, preguntas de receta, etiquetas, otros; las respuestas heredan el tema de su hilo) y, si habla del suero o de la marca, su tono (positivo, negativo, duda). Con `--muestra` imprime ejemplos por tema para revisar que las reglas clasifiquen bien; si algo queda mal, se ajustan las reglas del script.
4. Escribe `config/campanas/<campaña>/conversacion.yaml` con cifras agregadas y tres comentarios destacados sin usuario: es lo único que se publica.
5. Pruebas, build, revisión y subida (pasos 3 a 5 de la sección A). Las pruebas verifican las cifras que citan los textos.

Las plataformas no exponen todos los comentarios (borrados, filtrados u ocultos): el reporte dice cuántos se leyeron frente al total que reporta cada plataforma.

## E. Campaña con varios creadores y KPI de alcance (ej. Canola Life 2026)

Cuando una marca contrata a varios creadores con una meta de alcance por pieza, se usa `tipo: creadores` en `campana.yaml`.

1. **Excel de la campaña** (lo entrega la agencia): hojas *Instagram reels*, *TikTok videos* e *Instagram stories* (mismo formato de arriba, con la columna «Nombre / descripción») y **Cumplimiento KPI** (Fecha publicación, Creador, Plataforma, Formato, Tipo de acción, Alcance verificado, Proyección, Alcance proyectado, KPI alcance, Estado KPI verificado). Se guarda en `Dashboard Comapan/CreatorsWay-<marca>/insumos/datos/`.

**Regla de esta campaña: el Excel es la fuente única y continua del dato.** Lo que se ve en línea se actualiza *dentro* del Excel; lo que no es público (alcance, impresiones, guardados y reposts de Instagram, historias, KPI) se usa tal como viene en el Excel. El reporte lee solo el Excel.

2. **`campana.yaml`** (a mano): `tipo: creadores`, `marca` (con `handle` de la cuenta coautora), `creadores` (id, nombre visible, `excel` = nombre en la hoja de KPI, cuentas de Instagram y TikTok, tipo de acción), `piezas` (fila del Excel → código del reel o id del video, creador, título; `collab: false` si el reel no está marcado como colaboración) e `historias`. El build se detiene si una fila de KPI queda sin publicación, si una pieza no tiene visualizaciones o si el alcance por pieza no cuadra con la hoja de KPI.
3. **Captura pública** (Claude en Chrome) en `publicas.yaml`, con la clave de cada publicación: Instagram por código del reel (`views` = solo Instagram, `fb_views` = reproducciones en Facebook de la publicación cruzada, `coautor`, fecha real), TikTok por id del video (con guardados y duración). Las reacciones y comentarios de Facebook de la publicación cruzada quedan en la página de cada creador y no se suman.
4. **Actualizar el Excel e importar** (PowerShell, la ruta tiene tildes):
   ```powershell
   python -m scripts.actualizar_excel canola-2026 "<ruta del Excel>"
   python scripts/importar_excel.py canola-2026 "<ruta del Excel>"
   ```
   `actualizar_excel` guarda primero un respaldo en `insumos/datos/respaldo/`, escribe visualizaciones, me gusta, comentarios, compartidos, «Publicación cruzada Facebook» (y en TikTok duración y guardados), corrige la fecha si la publicación real es otra (también en la hoja de KPI), deja el valor anterior de cada celda en un comentario, llena «Fuente» y agrega la columna «Fecha corte cifras públicas». Imprime cada celda que cambió.
5. **Fotos y portadas:** `assets/<id>/avatar-<cuenta de Instagram>.jpg` y `assets/<id>/reel-<código>.jpg` (los enlaces de imagen vienen en la misma respuesta de la API de Instagram; se bajan con Python y se reducen a 360 px).
6. **Comentarios:** captura en `datos/capturas/<id>/ig-comentarios.txt` y `tt-comentarios.txt` (formato en `scripts/analizar_comentarios_creadores.py`; sin nombres de usuario, marcando con `C` las respuestas del creador) y luego `python scripts/analizar_comentarios_creadores.py <id> --muestra`. Si Chrome bloquea la descarga, se vuelca el texto en la página y se lee con `get_page_text`.
7. **Pruebas:** `tests/test_canola.py` cuadra el KPI con el Excel y las cifras públicas con la captura. Se copia para una campaña nueva.
8. Build, revisión en local, PDF y subida como en la sección A.

## EMV y ROI

Están apagados (`emv: null` en `cliente.yaml`, `pago_cop: null` en la campaña). Se activan cuando se tenga el pago de la marca y el benchmark de EMV acordado para ella.

## PDF en local

Con el servidor local en el puerto 8812:

```bash
PYTHONIOENCODING=utf-8 PDF_BASE_URL=http://localhost:8812 python scripts/render_pdf.py klarens-2026 canola-2026
```

## Publicación (hecha el 6 de noviembre de 2026)

1. DNS de `datalitica.com.co`: registro `CNAME  creatorsway  →  kevinromeroe.github.io` (lo hace Kevin).
2. Repo público `kevinromeroe/creatorsway-reportes`. `robots.txt` y la etiqueta `noindex` bloquean a los buscadores.
3. *Settings → Pages → Deploy from a branch → main / (root)*. El dominio se toma del archivo `CNAME`.
4. Cuando GitHub emite el certificado: *Enforce HTTPS*.
