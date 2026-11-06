# RUNBOOK · Reportes CreatorsWay

## Roles

- **Claude** edita los archivos en el clon local (`~/Documents/GitHub/creatorsway-reportes`) y los valida.
- **Tú** haces Commit + Push en GitHub Desktop.
- El HTML se genera y se revisa **en local**; el workflow **Pruebas + PDF** corre las pruebas y regenera los PDF al subirlo.

## Actualizar las cifras de una campaña

1. Guardar el Excel nuevo del creador en `Dashboard Comapan/Juan-Food-Time/insumos/datos/` (nunca en el repo).
2. `python scripts/importar_excel.py klarens-2026 "<ruta del Excel>"` (en PowerShell si la ruta tiene tildes).
3. Revisar que los textos de `campana.yaml` (notas y hallazgos) sigan cuadrando: `python -m unittest discover tests`.
   Si una prueba falla por un porcentaje citado, actualizar el texto.
4. `python scripts/build_reporte.py` y revisar en `http://localhost:8812/klarens-2026/`.
5. Commit + Push. El workflow regenera los PDF.

## Agregar una pieza

1. En `campana.yaml`, agregar la pieza con `slug`, `fecha` (la misma del Excel), `titulo`, `corto`, `nota` y, si aplica, `colaboracion`.
2. Importar el Excel, correr pruebas y build.

## Agregar una campaña nueva (otra marca u otro creador)

1. Crear `config/campanas/<marca>-<año>/campana.yaml` copiando el de KLAREN'S.
2. Logo de la marca sin fondo en `assets/`.
3. Importar, probar, construir y revisar.

## PDF en local

Con el servidor local corriendo en el puerto 8812:

```bash
PYTHONIOENCODING=utf-8 PDF_BASE_URL=http://localhost:8812 python scripts/render_pdf.py klarens-2026
```

## Publicación

Sitio: `https://creatorsway.datalitica.com.co` (repo público `kevinromeroe/creatorsway-reportes`, igual que LCI).
`robots.txt` y la etiqueta `noindex` bloquean a los buscadores.

1. DNS de `datalitica.com.co`: registro `CNAME  creatorsway  →  kevinromeroe.github.io` (lo hace Kevin).
2. Repo publicado en GitHub como `kevinromeroe/creatorsway-reportes`.
3. *Settings → Pages → Deploy from a branch → main / (root)*. El dominio se toma del archivo `CNAME`.
4. Cuando GitHub muestre el dominio verificado: marcar *Enforce HTTPS*.
