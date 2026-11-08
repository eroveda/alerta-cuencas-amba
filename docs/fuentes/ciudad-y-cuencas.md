# Fase 0 — Datos de la Ciudad de Buenos Aires y geometrías de cuencas (AMBA)

Verificación hecha el 2026-11-03 desde la máquina del proyecto, con `curl` (sin cambiar el User-Agent) y, cuando curl estaba bloqueado, con un fetch web externo para **leer** fichas de datasets. Las descargas están en `data/samples/geo/` (son datos no confiables: no se ejecutó nada de ahí). La validación se hizo con shapely 2.2 y pyproj 3.8 en un venv aparte, corriendo bajo `heavy.sh` (cgroup de 2 GB).

Convenciones: ✅ usable · ⚠️ con limitaciones · ❌ no accesible. "Verificado" quiere decir descargado y abierto. Lo que no se pudo verificar está marcado como tal.

---

## 1. Tabla resumen

| # | Fuente | URL exacta | Formato / CRS | Licencia | Tamaño | Estado |
|---|---|---|---|---|---|---|
| 1 | SAT CABA (red hidrometeorológica, tiempo real) | — (no se encontró endpoint público) | — | — | — | ❌ |
| 2 | BA Data — portal y API CKAN | `https://data.buenosaires.gob.ar/api/3/action/package_search?q=...` | JSON (CKAN) | — | — | ❌ con curl desde esta IP (WAF "Request Rejected") |
| 3 | BA Data — **Cuencas CABA** (12 cuencas) | `https://cdn.buenosaires.gob.ar/datosabiertos/datasets/secretaria-de-desarrollo-urbano/cuencas/cuencas.geojson` | GeoJSON, CRS84 | CC-BY-2.5-AR | 97 KB | ✅ (1 geometría inválida, se repara) |
| 4 | BA Data — **Arroyos** entubados/conductos | `https://cdn.buenosaires.gob.ar/datosabiertos/datasets/secretaria-de-desarrollo-urbano/arroyos/arroyos.geojson` | GeoJSON MultiLineString, CRS84 | CC-BY-2.5-AR | 22 KB | ✅ |
| 5 | BA Data — **Riesgo hídrico** (Código Urbanístico, mapa 7.2.8.3.1) | `https://cdn.buenosaires.gob.ar/datosabiertos/datasets/secretaria-de-desarrollo-urbano/riesgo-hidrico/riesgo-hidrico.geojson` | GeoJSON **sin `crs`, coordenadas en GKBA** | CC-BY-2.5-AR | 96 KB | ⚠️ (hay que reproyectar) |
| 6 | BA Data — **Sumideros** (5 zonas) | `https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-espacio-publico-e-higiene-urbana/sumideros/sumideros-zona-{1..5}.csv` | CSV con columna WKT (POLYGON, lon/lat) | CC-BY-2.5-AR | 6,5 MB en total (27.652 filas) | ✅ |
| 7 | BA Data — **Barrios populares CABA** | `https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-desarrollo-humano-y-habitat/barrios-populares/barrios_populares_poligono.geojson` | GeoJSON, CRS84 | CC-BY-2.5-AR | 252 KB (132 polígonos) | ✅ |
| 8 | BA Data — **Barrios** (48) | `https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-educacion/barrios/barrios.geojson` | GeoJSON, CRS84 | CC-BY-2.5-AR (según el portal) | 741 KB | ✅ |
| 9 | BA Data — Registro de precipitaciones (mensual, desde 1991) | ficha `https://data.buenosaires.gob.ar/dataset/registro-precipitaciones-ciudad` | CSV/XLSX | CC-BY-2.5-AR | ? | ⚠️ (no se encontró la URL del CDN; mensual, no sirve para alertas) |
| 10 | BA Data — Información meteorológica (TMI APRA) | `https://cdn.buenosaires.gob.ar/datosabiertos/datasets/agencia-de-proteccion-ambiental/informacion-meteorologica/informacion-meteorologica-2012.csv` | CSV horario | CC-BY-2.5-AR | 1,6 MB | ⚠️ histórico 2011–2012 solamente |
| 11 | BA Data — Pasos bajo nivel | — | — | — | — | ❌ no se encontró en el buscador del portal |
| 12 | EPOK / USIG (`epok.buenosaires.gob.ar`) | `https://epok.buenosaires.gob.ar/getCategorias/` | JSON | — | — | ❌ timeout por https (por http da 302) |
| 13 | **COHIFE — Cuencas hídricas de Argentina** | `http://datos.energia.gob.ar/dataset/2c8b870a-7d6b-4ad0-ace0-86c4a9c9e3c0/resource/ace98ef1-e7a8-4d5d-8f44-2e85a2d824a4/download/cuencas-hdricas-cohife.zip` | SHP, EPSG:4326 | CC-BY-4.0 | ZIP 29,7 MB (SHP 84 MB, 291 cuencas) | ✅ |
| 14 | **INA — sistema a5, áreas (cuencas de pronóstico)** | `https://alerta.ina.gob.ar/a5/obs/areal/areas?format=geojson` | GeoJSON, EPSG:4326 | no declarada | 32,8 MB (336 áreas) | ✅/⚠️ (licencia sin declarar, 5 inválidas en el AMBA) |
| 15 | IGN — WFS hidrografía (cursos y espejos de agua) | `https://wms.ign.gob.ar/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=ign:lineas_de_aguas_continentales_perenne&outputFormat=application/json&bbox=-35.2,-59.6,-34.2,-57.7,urn:ogc:def:crs:EPSG::4326` | GeoJSON vía WFS 2.0 | CC-BY-4.0 (IGN; no se comprobó en la respuesta) | 817 líneas perennes en la bbox del AMBA | ✅ red de drenaje · ❌ no publica polígonos de cuencas |
| 16 | **HydroBASINS v1c Sudamérica** nivel 8 y nivel 12 | `https://data.hydrosheds.org/file/HydroBASINS/standard/hybas_sa_lev08_v1c.zip` · `.../hybas_sa_lev12_v1c.zip` | SHP, EPSG:4326 | HydroSHEDS (libre, con atribución) | 30 MB / 72,7 MB | ✅ como respaldo (poco preciso en llanura) |
| 17 | ADA PBA — portal Riesgo Hídrico: mapas de peligrosidad | `https://riesgohidrico.ada.gba.gov.ar/mapas-de-peligrosidad-por-cuencas/` | PDF en Google Drive, JPG y visor GIS | no declarada | — | ⚠️ PDF/imagen; vector solo en un caso (ver 18) |
| 18 | ADA PBA — exportación KML de Google My Maps | `https://www.google.com/maps/d/kml?mid=1LnbbM9SdajyhjPRds9Ha4RqwGmenE_E&forcekml=1` (peligrosidad, La Plata sur) · `mid=1C8X6R838ZeQgn_x0PJGEZKmdNFX_WFw` (peligrosidad, Luján) · `mid=1K7byO75qFtA2ZKmZ0HPBJHgZLTaK6Y0` (puntos de monitoreo) | KML, EPSG:4326 | no declarada | 1,4 MB / 3,4 MB / 1,1 MB | ⚠️ |
| 19 | ADA PBA — visor `gis.ada.gba.gov.ar` (capa `cuencas_ssrh2`, `peligrosidad_el_gato`, etc.) | `https://gis.ada.gba.gov.ar/gis/?l=cuencas_ssrh2&b=13` | OpenLayers + backend propio | — | — | ❌ backend `process/?process=1&action=1` → `{"error":"-1"}`; no hay `/geoserver` |
| 20 | ADA PBA — "niveles escalas" | `https://gis.ada.gba.gov.ar/data/niveles_escalas` | SPA con reCAPTCHA | — | — | ❌ para uso automático |
| 21 | ACUMAR — datos abiertos (CKAN) | `https://datos.acumar.gov.ar/api/3/action/package_search?q=cuenca` | CKAN JSON | ODbL / CC-BY | 27 datasets | ❌ para geometrías (no hay ningún SHP/GeoJSON del límite de cuenca) |
| 22 | ACUMAR — geoservicios | probados `geoportal.`, `geoserver.`, `geo.acumar.gob.ar/geoserver` | — | — | — | ❌ sin respuesta |
| 23 | **RENABAP — barrios populares (nación)** | `https://archivo.infraestructura.gob.ar/dataset/ssisu/20231205_info_publica.geojson` (también `.gpkg` y `.csv`) | GeoJSON/GPKG | CC-BY | — | ❌ hoy: HTTP 200 con una página HTML "Sistema en mantenimiento" |
| 24 | RENABAP — factores de riesgo GBA | `https://archivo.infraestructura.gob.ar/dataset/ssisu/renabap-factores-de-riesgo` | ZIP | CC-BY | — | ❌ mismo mantenimiento; no hay copia en Wayback |
| 25 | IDEBA / ADA / Geoinfra (geoservidores provinciales) | `ide.gba.gob.ar`, `geo.gba.gob.ar`, `geoinfra.minfra.gba.gob.ar`, `ada.gba.gob.ar` | — | — | — | ❌ sin respuesta. Ojo: el dominio vigente de ADA es `ada.gba.gov.ar`, no `.gob.ar` |

---

## 2. Ciudad de Buenos Aires

### 2.1 Sistema de Alerta de Tormentas (SAT) / red hidrometeorológica — ❌
- Hay notas oficiales (2018 y 2020) que describen el SAT: 34 a 46 estaciones meteorológicas e hidráulicas, limnígrafos y caudalímetros en los arroyos, y radar en Merlo. **No se encontró ningún visor público ni API con datos en tiempo real.**
- `https://buenosaires.gob.ar/sat` redirige (301) a `/gcaba_historico/sat`, que devuelve 404. `sat.buenosaires.gob.ar` y `alertas.buenosaires.gob.ar` no resuelven o no responden.
- `mapa.buenosaires.gob.ar` carga, pero el HTML no referencia ningún servicio hidrometeorológico. EPOK, el backend de capas de USIG, no respondió por https, así que no se pudieron inspeccionar sus categorías.
- En BA Data no hay ningún dataset con lecturas del SAT. Lo más parecido es *Información Meteorológica* (torres TMI de APRA, datos horarios de 2011–2012) y el *Registro de precipitaciones* (mensual, DGEyC). Ninguno sirve para alertas.
- **Conclusión:** para pluviometría y niveles en tiempo real en CABA hay que buscar otras fuentes (SMN, INA a5, redes colaborativas). Eso queda fuera de este informe.

### 2.2 BA Data (data.buenosaires.gob.ar)
- **Gotcha principal:** desde esta máquina, cualquier request con curl a `data.buenosaires.gob.ar` (incluida la home y `/api/3/action/*`) devuelve **HTTP 200 con una página HTML "Request Rejected"** de un WAF. Con un fetch web externo las fichas sí se leyeron, así que el bloqueo depende del cliente o de la IP. No se intentó esquivarlo. **La API CKAN no se pudo usar para descubrir datasets automáticamente.**
- **El CDN `cdn.buenosaires.gob.ar/datosabiertos/datasets/<organización>/<dataset>/<archivo>` sí responde** sin bloqueo (no permite listar directorios: 403). Las URLs de la tabla se encontraron combinando la ficha del dataset con el patrón de nombres. Los links `/dataset/<slug>/resource/<id>/download` de las fichas pasan por el dominio bloqueado.
- Que la respuesta sea 200 no alcanza: hay que validar que el contenido sea JSON o CSV, porque el WAF también responde 200.

**Cuencas (12 polígonos).** Larrazábal y Escalada, Elía, Boca-Barracas, Ochoa, Erezcano y San Pedrito, Radio Antiguo, Ugarteche, **Maldonado (98,3 km²)**, **Vega (19,6 km²)**, **White (2,2 km²)**, **Medrano (54,4 km²)** y **Cildáñez (36,8 km²)**.
- "Cuenca White" es inválida (*Ring Self-intersection*). Con `make_valid` queda como Polygon válido. La versión reparada está en `caba/cuencas_caba_valid_4326.geojson`.
- Las cuencas de Maldonado, Medrano y Cildáñez **se extienden más allá de CABA** (hacia La Matanza, Tres de Febrero y San Martín). Por ejemplo, Maldonado llega hasta -58,59 de longitud. O sea que son la cuenca completa, no el tramo porteño.
- Comparación con COHIFE (IoU): Maldonado 0,86 y Medrano 0,85. Son coherentes entre sí.
- Ficha: Secretaría de Desarrollo Urbano, actualización anual, última el 28/07/2026.

**Arroyos (18 líneas).** San Pedrito, Erezcano, Teuco, Cildáñez, Maldonado, Vega, White, Medrano, Ugarteche, Perdriel, Elía-Iguazú, aliviadores, túneles aliviadores del Maldonado, segundo emisario del Vega y conductos. Tienen atributos `tipo` y `sentido` (norte/sur). Están todas las geometrías válidas.

**Riesgo hídrico (51 MultiPolygon).** Atributos: `Entity` = "LWPolyline" (resto de un CAD) y `m2`.
- **Gotcha:** el archivo no tiene miembro `crs` y las coordenadas están en metros (x≈94.000–110.000), lo que viola RFC 7946. El sistema es **GKBA (Gauss-Krüger Buenos Aires)**: `+proj=tmerc +lat_0=-34.629269 +lon_0=-58.4633 +k=0.9999980 +x_0=100000 +y_0=100000 +ellps=intl +units=m`.
- **Verificado:** el área calculada después de reproyectar coincide con el campo `m2` en menos de 0,05 % (1.212.000 contra 1.212.024 m²) y los polígonos caen dentro de CABA.
- **Cuidado:** EPSG:9498 ("POSGAR 2007 / CABA 2019") **no** sirve; ubica los polígonos unos 90 km al este.
- La versión reproyectada a 4326 está en `caba/riesgo-hidrico_4326.geojson`.
- Es una capa normativa (zonas de prevención del Código Urbanístico), no un mapa de amenaza modelado, y no tiene atributo de nivel de riesgo.

**Sumideros.** Son 5 CSV (zonas 1 a 5) con `WKT` (pequeños POLYGON), `diametro`, `nro_sumi`, `calle_1`, `calle_2`, `altura` y `tipo_sumi`. Hay filas con valores vacíos o en 0 (por ejemplo `id=2`). Hay un SHP en la ficha, pero no se probó su URL en el CDN.

**Barrios populares CABA.** 132 polígonos con `tipo` (villa, asentamiento, etc.) y `nombre`. La ficha se actualiza trimestralmente (última el 03/11/2026). La misma ficha incluye manzanas y tejido urbano; no se buscaron sus URLs en el CDN.

**Barrios (48).** Campos `nombre`, `comuna`, `perimetro_` y `area_metro`.

---

## 3. Geometrías de cuencas para el AMBA

### 3.1 COHIFE (Consejo Hídrico Federal, vía Secretaría de Energía / datos.gob.ar) — ✅
14 cuencas intersectan la bbox del AMBA y todas son válidas. Subconjunto guardado: `cohife/cohife_amba.geojson`. Campos: `CUENCA`, `SISTEMA__S` y `REG_HIDR`.

| Cuenca COHIFE | km² (Albers) |
|---|---|
| Arroyo Maldonado | 103,2 |
| Arroyo Medrano | 55,6 |
| Afluentes al río de la Plata en CABA (MultiPolygon) | 50,5 |
| Río Matanza-Riachuelo | 2.085 |
| Río Reconquista | 1.693 |
| Río Luján | 2.956 |
| Afluentes al río de la Plata en Buenos Aires (MultiPolygon: Sarandí, Santo Domingo, Quilmes, Berazategui, La Plata y otras **agrupadas**) | 3.238 |
| Afluentes al río Paraná en Buenos Aires | 1.945 |
| Delta del río Paraná | 18.787 |
| Arroyo Escobar · Arroyo de la Cruz · Areco · Samborombón · Salado | — |

Gotchas:
- El SHP nacional pesa 84 MB descomprimido y 1 registro tiene shape NULL. Conviene recorrerlo registro por registro (pyshp) y filtrar por bbox.
- Los nombres de archivo dentro del ZIP tienen "í" en una codificación rota (`cuencas-h�dricas-...`). Hay que renombrarlos al extraer.
- Vega, White y Cildáñez **no** vienen separados.

### 3.2 INA — sistema a5 (`/a5/obs/areal/areas`) — ✅ (licencia sin declarar)
- 336 áreas en total, 38 en el AMBA. Campos: `id`, `nombre`, `exutorio` (punto de cierre) y parámetros de modelo.
- Para el AMBA: **Reconquista - RN9**, **Luján** en varios tramos (Jáuregui, Mercedes, Luján-RN9), **Río Matanza - Puente La Noria**, Samborombón, "Cuencas de aporte al Río de la Plata por margen derecha" y **subcuencas de la Matanza-Riachuelo**: Aguirre, Barreiro, Cañuelas, Cebey, Chacón, Cañada Pantanosa, del Rey, Don Mario, Matanza Alto, Intermedio y Rectificado, Morales, Ortega, **Riachuelo**, Rodríguez y Santa Catalina.
- Gotchas:
  - 5 polígonos inválidos (Barreiro, Cañuelas, Don Mario, Matanza Alto e Intermedio). Se reparan con `make_valid`.
  - Hay duplicados y basura: "rio matanza en puente La Noria" mide 0,001° y sería un placeholder.
  - Varias áreas son cuencas **hasta una estación**, no la cuenca entera. Por ejemplo, Reconquista llega hasta RN9 y no hasta la desembocadura.
  - Bajarlo cuesta 32 MB por llamada y no se probó si acepta filtros por bbox o id.
- Subconjunto guardado: `ina/ina_areas_amba.geojson`.

### 3.3 IGN — WFS — ✅ para la red hídrica, ❌ para cuencas
- `GetCapabilities` publica 192 capas. Las de hidrografía son `lineas_de_aguas_continentales_*`, `areas_de_aguas_continentales_*` y `puntos_*`. **No hay capas de cuencas.**
- `GetFeature` con bbox en el servidor funciona. Gotcha: en WFS 2.0 con `urn:ogc:def:crs:EPSG::4326` el orden de la bbox es **lat,lon** (`-35.2,-59.6,-34.2,-57.7`). Hay 817 líneas perennes en el AMBA.
- No se descargó la capa completa.

### 3.4 HydroBASINS v1c (Sudamérica) — ✅ como respaldo
- **Nivel 8:** 46 unidades en el AMBA (`hydrobasins/hybas_lev08_amba.geojson`). Contra COHIFE, unidas por >50 % de su área, el IoU da 0,92 en Matanza-Riachuelo (2.180 km²), 0,72 en Reconquista (2.266 km², sobreestima) y 0,89 en Luján.
- **Nivel 12:** 161 unidades en el AMBA (`hydrobasins/hybas_lev12_amba.geojson`).
  - El punto de La Plata/El Gato cae en una unidad de 190 km². Un estudio UNLP-MLP habla de unos 124 km², así que la sobreestima.
  - El punto de Sarandí cae en la unidad de desembocadura de la Matanza-Riachuelo (up_area 2.181 km²). En una llanura tan plana, **HydroBASINS no resuelve bien las cuencas costeras chicas.**
- Se descargaron los ZIP por nivel (30 y 73 MB). **No se descargó** el paquete completo `hybas_sa_lev01-12_v1c.zip` (334 MB).
- Los SHP descomprimidos se borraron después de filtrar; quedaron los ZIP.

### 3.5 ADA PBA (Autoridad del Agua / Subsecretaría de Recursos Hídricos) — ⚠️
- El portal `riesgohidrico.ada.gba.gov.ar` publica mapas de peligrosidad por cuenca para: San Francisco - Las Piedras - **Sarandí - Santo Domingo**, **El Gato**, Carnaval, Rodríguez, Maldonado-Garibaldi-Circunvalación-Zoológico, Pereyra, **Reconquista** (3 sectores), **Luján**, San Juan y Jiménez.
- Casi todos se publican como **PDF en Google Drive y JPG**. La versión vector está en el visor `gis.ada.gba.gov.ar` (capas `peligrosidad_el_gato`, `peligrosidad_las_piedras`, `peligrosidad_reconquista`, `cuencas_ssrh2`), cuyo backend no responde sin sesión.
- **Vector que sí se pudo bajar:** el KML exportado de los Google My Maps embebidos.
  - `1LnbbM9...` tiene 800 polígonos de peligrosidad (alta, media, baja, muy baja a nula) con atributo `cuenca`. Solo cubre **Abascay y El Pescado** (La Plata sur), no El Gato. El agregado por cuenca está en `ada_mymaps/laplata_peligrosidad_por_cuenca.geojson`.
  - `1C8X6R...` es peligrosidad de Luján (1.481 polígonos, atributos PELI y Partido).
  - `1K7byO...` son 58 puntos de monitoreo visual y los distritos de la DPH.
- Gotchas: la exportación de My Maps (`/maps/d/kml?mid=…&forcekml=1`) es un mecanismo no oficial y puede desaparecer, y ninguno de estos materiales declara licencia.

### 3.6 ACUMAR — ❌ para la geometría
- El CKAN `datos.acumar.gov.ar` (27 datasets) solo publica CSV: establecimientos, salud, ICV, etc. **No tiene el límite de cuenca en formato vectorial.**
- Las URLs de recursos apuntan a `datos.acumar.gob.ar`, mientras que el portal está en `.gov.ar`.
- Los geoservidores probados no responden.
- Como sustituto, la cuenca Matanza-Riachuelo de COHIFE y las subcuencas del INA cubren esta necesidad.

### 3.7 IDERA / Geoinfra / IDEBA — ❌ no verificados
No respondieron o no tienen un endpoint OGC conocido. No se encontró un catálogo IDERA con cuencas del AMBA. No se profundizó más.

---

## 4. Riesgo y vulnerabilidad

- **RENABAP (nacional):** ❌ hoy. Las URLs del catálogo de datos.gob.ar (registro actualizado el 2026-08-03) apuntan a `archivo.infraestructura.gob.ar`, que responde **HTTP 200 con una página HTML "Sistema en mantenimiento"**. Esto engaña a un validador que solo mire el status. No hay copia en Wayback Machine y `datosabiertos.desarrollosocial.gob.ar` no responde. Pasa lo mismo con el dataset de *factores de riesgo en barrios populares del GBA*, que tiene justamente datos de cercanía a riesgos hídricos y sería muy útil.
  - Acción: reintentar más adelante, siempre validando el content-type y la firma del archivo.
  - Mientras tanto, para CABA está el dataset propio de barrios populares (✅).
- **Zonas inundables de provincia:** solo se encontraron los mapas de peligrosidad de ADA (§3.5). Hay vector descargable para Luján y La Plata sur. El Gato, Sarandí-Santo Domingo y Reconquista están solo en PDF/JPG o en el visor sin API.
- **CABA:** la capa *Riesgo hídrico* (§2.2) es normativa y no indica nivel de amenaza.

---

## 5. Geometría recomendada por cuenca

| Cuenca del sistema | Geometría recomendada | Alternativa / validación | Confianza |
|---|---|---|---|
| **Maldonado** | BA Data *Cuencas* → "Cuenca Maldonado" (98 km², incluye el tramo bonaerense) | COHIFE "Arroyo Maldonado" (IoU 0,86) | Alta |
| **Medrano** | BA Data "Cuenca Medrano" (54 km²) | COHIFE "Arroyo Medrano" (IoU 0,85) | Alta |
| **Vega** | BA Data "Cuenca Vega" (19,6 km²) | — (COHIFE lo agrupa en "Afluentes … en CABA") | Media-alta (fuente única) |
| **Cildáñez** | BA Data "Cuenca Cildañez" (36,8 km²) | Se superpone con COHIFE Matanza-Riachuelo, porque el Cildáñez descarga en el Riachuelo | Media-alta |
| **White** | BA Data "Cuenca White" (2,2 km²) **después de `make_valid`** | — | Media (polígono reparado; cuenca muy chica, la granularidad de la alerta va a ser gruesa) |
| **Matanza-Riachuelo** | COHIFE "Río Matanza-Riachuelo" (2.085 km²) | INA: subcuencas (Riachuelo, Matanza Rectificado, Ortega, Aguirre…) para dividir en zonas; HydroBASINS L8 (IoU 0,92) | Alta |
| **Reconquista** | COHIFE "Río Reconquista" (1.693 km²) | INA "Reconquista - RN9" (parcial, hasta RN9); HydroBASINS L8 sobreestima (IoU 0,72) | Alta (COHIFE) |
| **Luján** | COHIFE "Río Luján" (2.956 km²) | INA tramos Luján (Jáuregui, Mercedes, RN9) para dividir en zonas; HydroBASINS L8 (IoU 0,89) | Alta |
| **Sarandí / Santo Domingo** | ⚠️ No hay polígono vectorial propio. Provisorio: recortar COHIFE "Afluentes al río de la Plata en Buenos Aires" a los partidos de Avellaneda y Quilmes, o usar las unidades HydroBASINS L12 6120017120 (Santo Domingo aprox., 183 km²) con revisión manual | Mapa de peligrosidad ADA "San Francisco - Las Piedras - Sarandí - Santo Domingo" (PDF/visor, sin vector) | Baja |
| **Costa y Delta (Tigre / San Fernando / costa RdlP)** | COHIFE "Delta del río Paraná" recortado a la bbox AMBA + "Afluentes al río Paraná en Buenos Aires" (parte sur) + franja norte de "Afluentes al río de la Plata en Buenos Aires" | Límites municipales del IGN (`ign_municipio.zip`) para definir zonas por partido | Media. Esta "cuenca" es más una zona costera de alerta por sudestada que una cuenca hidrográfica, así que conviene definirla por partidos o por cota |
| **La Plata (El Gato y otros)** | ⚠️ No hay polígono vectorial de El Gato. Provisorio: HydroBASINS L12 6120017190 (190 km², sobreestima frente a los ~124 km² de un estudio UNLP-MLP). Para el resto, COHIFE "Afluentes al río de la Plata en Buenos Aires" recortado al partido de La Plata | ADA: mapas de peligrosidad El Gato, Carnaval, Rodríguez y Maldonado-Garibaldi (PDF/visor); KML ADA para Abascay y El Pescado | Baja |

Para las dos cuencas en ⚠️ conviene delinearlas a partir de un MDE (MDE-Ar del IGN o MERIT-Hydro) usando la red de drenaje del WFS del IGN como guía, o pedirle los shapes a ADA o a la UNLP.

---

## 6. Archivos descargados (`data/samples/geo/`)

- `caba/`: `cuencas_caba.geojson` (original), `cuencas_caba_valid_4326.geojson` (reparado), `arroyos.geojson`, `riesgo-hidrico.geojson` (GKBA, original), `riesgo-hidrico_4326.geojson` (reproyectado), `riesgo-hidrico.csv`, `sumideros-zona-{1..5}.csv`, `barrios_populares_caba.geojson`, `barrios_caba.geojson`
- `cohife/`: `cohife.zip` (original; el SHP de 84 MB se borró después de filtrar), `.dbf/.prj/.shx/.cpg` y `cohife_amba.geojson`
- `ina/`: `ina_a5_areas.geojson` (completo, 32,8 MB) y `ina_areas_amba.geojson`
- `hydrobasins/`: `hybas_sa_lev08_v1c.zip`, `hybas_sa_lev12_v1c.zip`, `hybas_lev08_amba.geojson`, `hybas_lev12_amba.geojson` y la documentación técnica en PDF
- `ada_mymaps/`: 3 KML y `laplata_peligrosidad_por_cuenca.geojson`
- `renabap/MANTENIMIENTO_respuesta_html_no_es_geojson.html`: evidencia de la caída del servidor RENABAP; no es un dato

Los scripts de inspección (no forman parte del proyecto) están en `/tmp/claude-1000/-home-rove-proyectos-ni-o/725ae13a-202c-4d2f-af5e-d05adf6ed736/scratchpad/tools/`.

## 7. Qué no se pudo verificar
- Si existe algún endpoint público del SAT de CABA, quizás en apps móviles o en Oracle/BGH. No se encontró ninguno.
- Las URLs en el CDN de los SHP de BA Data, del CSV de precipitaciones y de las manzanas de barrios populares.
- La licencia de los datos del INA a5 y de los materiales de ADA.
- Si el WAF de BA Data bloquea por IP o por tipo de cliente. Desde el servidor de producción puede comportarse distinto: hay que probarlo ahí.
- El valor oficial de superficie de cada cuenca. Los km² de este informe son cálculos propios en Albers equivalente.
