# Fuentes meteorológicas: verificación de acceso por máquina (Fase 0)

Pruebas hechas el **2026-11-03, entre 23:13 y 23:20 hora argentina** (02:13 a 02:20 UTC del 04/11) con `curl` desde una IP residencial argentina (Cloudflare la ruteó a EZE). En ese momento llovía débil en el AMBA (lo confirman las observaciones), lo que vino bien para ver datos con señal.
Las muestras crudas están en `data/samples/meteo/` (datos no confiables: no ejecutar nada de ahí).

> Convención: "verificado" = lo probé y vi la respuesta. "No verificado" = lo dicen la documentación o el conocimiento previo, pero no lo pude comprobar.

## Tabla resumen

| # | Fuente / endpoint | Formato | Auth | HTTP | Actualización / latencia observada | Clasificación |
|---|---|---|---|---|---|---|
| 1 | **SMN CAP RSS**: `https://ssl.smn.gob.ar/CAP/AR.php` y los CAP XML enlazados | RSS 2.0 + CAP 1.2 (polígonos) | No | 200 | Se genera en cada request. El CAP se publica unos 16 s después de su `sent` | ✅ usable |
| 2 | SMN "Avisos a muy corto plazo" GeoRSS: `https://ssl.smn.gob.ar/feeds/avisocorto_GeoRSS.xml` | GeoRSS | No | 200 | No se pudo medir (no había ningún ACP vigente) | ⚠️ formato con ACP activo sin verificar |
| 3 | SMN open data "estado del tiempo": `https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=tiepre` | ZIP con TXT `;` en latin-1 | No | 200 | Horaria, con 1 a 2 h de latencia. **Sin mm de lluvia** | ⚠️ usable, poco útil para lluvia |
| 4 | SMN open data "dato horario": `https://ssl.smn.gob.ar/dpd/descarga_opendata.php?file=observaciones/datohorario{YYYYMMDD}.txt` | TXT de ancho fijo | No | 200 | Sale **al día siguiente** (el del día en curso viene vacío). **Sin precipitación** | ⚠️ solo histórico, sin lluvia |
| 5 | SMN API web `ws1.smn.gob.ar/v1/...` (alertas por área, pronóstico, radar) | JSON | **JWT** | 401 | — | ❌ sin token (no se pudo obtener) |
| 6 | SMN `www.smn.gob.ar`, `estaticos.smn.gob.ar` (radar), `ws.smn.gob.ar` | HTML/PNG/JSON | Desafío Cloudflare | 403 / 503 | — | ❌ no accesible por máquina |
| 7 | **Open-Meteo Forecast** (`minutely_15`, `hourly`) | JSON | No | 200 | Unos 1,1 s por request. En AMBA el `minutely_15` es **hora interpolada** | ✅ usable (free = no comercial) |
| 8 | Open-Meteo Flood API (GloFAS) | JSON | No | 200 | Diario, celda de 0,05° | ⚠️ accesible pero **inservible** para estas cuencas |
| 9 | Open-Meteo Archive (ERA5 / ERA5-Land) | JSON | No | 200 | — | ⚠️ accesible, **subestima groseramente** la lluvia convectiva |
| 10 | GDACS API `gdacsapi/api/events/geteventlist/SEARCH` + RSS | GeoJSON / RSS | No | 200 | Eventos FL derivados de GloFAS, días de demora | ⚠️ solo contexto, no sirve para alerta temprana |
| 11 | **METAR** (NOAA AWC): `https://aviationweather.gov/api/data/metar` | JSON / TXT | No | 200 | Horario + SPECI, menos de 20 min de latencia | ✅ usable (fenómeno presente, sin mm) |
| 12 | SYNOP vía Ogimet: `https://www.ogimet.com/cgi-bin/getsynop` | TXT (SYNOP crudo) | No | 200 | Horario, ~1 h de latencia. mm solo cada 6 h (grupo 6RRR) | ⚠️ usable con decodificación y bajo volumen |
| 13 | **GOES-19 GLM** (rayos) en AWS: `https://noaa-goes19.s3.amazonaws.com/` | NetCDF4, unos 370 KB cada 20 s | No | 200 | Unos 27 s desde el fin del período | ✅ usable (hay que procesar NetCDF) |
| 14 | GOES-19 ABI RRQPE (tasa de lluvia satelital), mismo bucket | NetCDF4, ~2 MB cada 10 min | No | 200 | **Hueco**: el último archivo es del 2026-11-02 16:50Z (unas 33 h de atraso) | ⚠️ intermitente |
| 15 | WMO Alert Hub / registro de fuentes CAP: `https://severeweather.wmo.int/json/sources.json` | JSON | No | 200 | — | ✅ confirma que el feed oficial de SMN es el #1 |
| 16 | Meteostat bulk: `https://data.meteostat.net/hourly/{YYYY}/87582.csv.gz` | CSV.gz | No | 200 | Diaria. La lluvia viene **rellenada con pronóstico** (`metno_forecast`) | ⚠️ solo backtesting, filtrando por fuente |

## Hallazgo principal (léanlo antes que nada)

- **El único canal oficial de alertas del SMN que es accesible por máquina y estable es el feed CAP** (`/CAP/AR.php`). Es la fuente que el SMN registró ante la OMM (`capAlertFeedStatus: operating`) y está bajo **CC BY 4.0**.
- **Por esta vía pública el SMN no publica observaciones de lluvia en tiempo real (mm) de las estaciones del AMBA.** `tiepre` y `datohorario` no tienen precipitación, los METAR solo informan fenómeno (`-RA`, `TSRA`) y el SYNOP trae mm cada 6 h. Para lluvia observada sub-horaria hace falta otra fuente: pluviómetros de CABA/provincia/INA (la verifica el área de hidrología), satélite o un convenio con el SMN.
- **Radar SMN (Ezeiza y otros): no accesible.** `radar.inta.gob.ar` redirige a `www.smn.gob.ar/radar`, que está detrás del desafío Cloudflare. `ws1.smn.gob.ar/v1/images/radar` devuelve 401. **No intenté saltear el desafío Cloudflare** (las herramientas lo bloquearon como evasión de bot y además no corresponde). Para radar hace falta pedir acceso formal al SMN.
- **Open-Meteo Flood (GloFAS) no sirve para Luján, Reconquista ni Matanza** (detalles abajo).

---

## 1. SMN Argentina

### 1.1 Feed CAP de alertas: ✅

- **URL probada:** `https://ssl.smn.gob.ar/CAP/AR.php` → `200 application/rss+xml; charset=UTF-8`, 74.557 bytes, 104 ítems, entre 0,09 y 0,11 s por request (3 requests seguidos sin problema). También responde 200 con `User-Agent: python-requests`.
- **Contenido:** RSS cuyos `<item><link>` apuntan a XML **CAP 1.2** individuales, por ejemplo `https://ssl.smn.gob.ar/feeds/CAP/xml_generados/CAP_20261103130902_Tormenta_Llanura_alertas_alertas_60.xml`. Descargué los 74 de "Tormenta_Llanura" (352 KB en total).
- **Títulos en la muestra:** Tormentas (88), Viento Zonda (9), Viento (5), Lluvias (2).
- **Campos CAP:** `identifier` (OID 2.49.0.1.32...), `sent`, `msgType` (Alert/Update), `references` (encadena con la emisión anterior), `event`, `urgency`, `severity`, `certainty`, `onset`, `expires`, `description` (incluye la lluvia acumulada esperada, por ejemplo "entre 20 y 40 mm"), `instruction` y **`<polygon>` lat,lon**.
- **Niveles:** en la muestra hubo `severity` Moderate (69) y Severe (5). Que amarillo = Moderate, naranja = Severe y rojo = Extreme es la convención CAP habitual y lo que sugiere la XSL de SMN (`estilo_cap_interno_2026.xsl` colorea Moderate en amarillo `#f1c40f` y Severe en rojo `#e74c3c`). **No pude confirmar con un evento naranja o rojo real para el AMBA.**
- **Autenticación:** ninguna. **CORS:** el header que llega es `control-allow-origin: *`, que no es el estándar `Access-Control-Allow-Origin`. Da igual porque lo vamos a consumir desde el backend.
- **Caché:** `cache-control: max-age=60` y `max-age=180` (los dos headers a la vez). Sin `ETag` ni `Last-Modified`, así que no se puede hacer request condicional: hay que deduplicar por `identifier`/`guid`.
- **Licencia:** "Licencia CC BY 4.0" en `<copyright>`.
- **Frecuencia:** el RSS se regenera en cada request. Las alertas de la muestra tienen `sent` 2026-11-03T13:08:46-03:00 y referencian una emisión de las 09:18:34. La periodicidad exacta de emisión no está verificada (parecen ser varias por día más actualizaciones).
- **Gotchas:**
  1. **`areaDesc` viene vacío**: no hay nombre de zona ni de partido, solo el polígono. Hay que hacer point-in-polygon contra los partidos del AMBA (probado con un script liviano: funciona).
  2. **El feed sigue mostrando alertas vencidas**: a las 23:14 seguían las de `expires` 20:59. Hay que filtrar por `expires`.
  3. **El `pubDate` del RSS se reescribe en cada build** (todos dicen 02:00:0x GMT): no sirve como hora de emisión. Usen `<sent>` del CAP.
  4. En la muestra, **ningún polígono contenía CABA, La Plata, Luján ni Morón** (el más cercano quedaba a ~0,58°), aunque a esa hora llovía débil en el AMBA. Es coherente: ya había vencido y no era un evento fuerte.
  5. `https://ssl.smn.gob.ar/feeds/` y `.../xml_generados/` (listados de directorio) dan 403 o desafío Cloudflare. Hay que entrar siempre por el RSS.
  6. El host está detrás de Cloudflare. Hoy no desafía estos paths, pero **es un riesgo**: si SMN endurece el WAF, se corta. Conviene monitorear la respuesta y tener plan B (convenio con SMN).

### 1.2 Avisos a muy corto plazo (ACP): ⚠️

- **URL probada:** `https://ssl.smn.gob.ar/feeds/avisocorto_GeoRSS.xml` → 200 `text/xml`, 972 bytes. En el momento de la prueba decía: "No se han emitido Avisos Meteorológicos a corto plazo en la REPUBLICA ARGENTINA". Licencia CC BY 4.0.
- **No verificado:** cómo se ve un ACP activo (si trae polígono georss y qué campos). Hay que re-muestrear durante un evento convectivo con ACP. Tampoco verifiqué si los ACP aparecen además en `CAP/AR.php` (en la muestra no había ninguno).
- `https://ssl.smn.gob.ar/feeds/avisocorto.xml` → 200, pero es **legado/obsoleto**: el último ítem es del 2018-11-10. Igual muestra el formato viejo (lista de partidos en texto). No usar.

### 1.3 Observaciones de estaciones (open data): ⚠️

- `https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=tiepre` → 200, un ZIP de 3,2 KB con `estado_tiempo{YYYYMMDD}.txt` (separado por `;`, latin-1). Trae **Aeroparque, Buenos Aires (Observatorio Central), Ezeiza, San Fernando, La Plata, El Palomar, Morón, Campo de Mayo**, etc. Los campos son estación, fecha, hora, estado del cielo en texto ("Nublado con lluvia", "...lluvia en la hora anterior"), visibilidad, temperatura, humedad, viento y presión. **No tiene milímetros.**
  - Latencia observada: a las 23:13 tenía datos de las 22:00 (y de las 21:00 en Aeroparque). Unas 1-2 h.
- `.../descarga_opendata.php?file=observaciones/datohorario{YYYYMMDD}.txt`: el del 20261102 dio 200 con 1.860 líneas (FECHA, HORA, TEMP, HUM, PNM, DD, FF, NOMBRE). **Sin precipitación.** El ZIP del día en curso (`dato=datohorario`) vino **vacío**: el archivo se publica cuando termina el día.
- `dato=pron5d` y `dato=observaciones` también traían el TXT del día en 0 bytes a esa hora.
- No encontré ningún dataset de precipitación horaria ni sub-horaria. El catálogo de open data está en `www.smn.gob.ar`, que tiene desafío Cloudflare, así que **no pude listar el catálogo completo**: puede haber datasets que no probé.
- Gotcha: cuando un archivo no existe, la respuesta es HTTP 200 con el texto `"...El archivo no existe."`. Hay que validar el contenido, no el código.

### 1.4 API de la web (`ws1.smn.gob.ar`): ❌ sin token

- `https://ws1.smn.gob.ar/v1/georef/location/search?name=Buenos` → **200 sin auth** (geocodificador: id 4864 = CABA, estación asociada "BUENOS AIRES OBSERVATORIO"). También funcionó con "La Plata" (id 4856, LA PLATA AERO).
- `.../v1/weather/location/4864`, `.../v1/warning/alert/area/4864`, `.../v1/images/radar`, `.../v1/georef/location/coord` → **401 Unauthorized** (JSON de Spring).
- Por lo que se sabe (no verificado), la web del SMN inyecta un JWT en el HTML. El HTML está detrás del desafío Cloudflare (`cf-mitigated: challenge`), así que **no lo pude obtener**. No intenté evadirlo.
- `ws.smn.gob.ar/alerts/type/AL` (y AC, SR, `map_items/weather`) → 503 "No server is available to handle this request". Parece un backend dado de baja.

### 1.5 Radar: ❌

- `estaticos.smn.gob.ar/vmsr/radar/` → 403, desafío Cloudflare. `radar.inta.gob.ar` → 301 a `https://www.smn.gob.ar/radar` (desafío). `ws1.../v1/images/radar` → 401.
- **Conclusión:** no hay acceso público por máquina al radar de Ezeiza ni a los demás radares del SMN/SINARAME/INTA. Hay que pedirlo por convenio.

## 2. Open-Meteo

### 2.1 Forecast: ✅

- **URL probada:** `https://api.open-meteo.com/v1/forecast?latitude=-34.6&longitude=-58.45&minutely_15=precipitation,rain,precipitation_probability&hourly=precipitation,precipitation_probability&current=precipitation,rain&past_minutely_15=8&forecast_minutely_15=24&timezone=America%2FArgentina%2FBuenos_Aires&forecast_days=2` → 200, 3 KB, 1,07 s.
- Headers de rate limit: `X-RateLimit-Limit: 600`, `X-RateLimit-Window: 60`, `X-RateLimit-Cost: 1.0`.
- La celda queda en -34.62, -58.41 (elevación 15 m).
- **Gotcha importante:** en el AMBA los valores de `minutely_15` son **constantes dentro de cada hora** (0,80, 0,80, 0,80, 0,80, luego 0,20 ×4). O sea, es la hora repartida en cuartos, no un modelo de 15 min de verdad (eso existe para Europa y Norteamérica, no acá). No sirve como nowcasting de 15 min. Lo que aporta es pronóstico horario de modelos globales.
- `current.precipitation` es del modelo, no observado (daba 0,00 mientras los METAR de una hora antes informaban `-RA`).
- **Términos (texto leído de `open-meteo.com/en/terms` y `/en/pricing`):** la API gratis es **solo para uso no comercial**, con límites de menos de 10.000 llamadas/día, 5.000/hora, 600/minuto y 300.000/mes (la página dice que el límite mensual todavía no se aplica). Datos bajo **CC BY 4.0**, sin SLA. El uso comercial requiere plan pago (`customer-api.open-meteo.com`). "No comercial" se define según Creative Commons: el sitio pone como ejemplo webs o apps sin fines de lucro y sin suscripción ni publicidad. Un sistema público de alerta sin fines de lucro *parece* entrar, pero lo debería confirmar quien lleve lo legal o un mail a info@open-meteo.com.
- **Presupuesto:** 20 puntos cada 5 min son 5.760 llamadas/día, dentro del límite. Ojo: el sitio indica que muchas coordenadas en una sola llamada aumentan el costo (no medí cuánto).

### 2.2 Flood API (GloFAS): ⚠️ accesible, ❌ para este uso

- **URL:** `https://flood-api.open-meteo.com/v1/flood?latitude=..&longitude=..&daily=river_discharge,river_discharge_mean,river_discharge_max&past_days=10&forecast_days=10&cell_selection=nearest` → 200 en los tres puntos, unos 1,07 s.
- Celdas devueltas (grilla de 0,05°, unos 5 km), caudal diario en m³/s, desde el 25/10 hasta el 13/11:
  - Luján (-34.575, -59.125): 0,14 a 0,79 m³/s.
  - Reconquista (-34.525, -58.625): 0,8 a 2,5 m³/s.
  - Matanza (-34.725, -58.525): 16 a 31 m³/s.
- **Prueba con un evento conocido:** la inundación de Luján de agosto de 2015 (`start_date=2015-07-25&end_date=2015-08-25`) da un **máximo de 2,17 m³/s** el 10/08. Fue una inundación que anegó la ciudad de Luján, así que ese valor está órdenes de magnitud por debajo de lo esperable (no busqué el caudal observado en esta fase). Parece que la celda no cae sobre el cauce principal de la red de GloFAS, o que el modelo no resuelve la cuenca.
- **Conclusión:** la resolución (≈5 km, paso diario, red fluvial global) **no sirve** para cuencas urbanas y periurbanas de respuesta horaria. Como mucho sirve como contexto regional (Paraná/Plata). También existe `ensemble=true` (200 OK, miembros 01..50).

### 2.3 Archive / histórico: ⚠️

- **URL:** `https://archive-api.open-meteo.com/v1/archive?latitude=-34.92&longitude=-57.95&start_date=2013-04-02&end_date=2013-04-03&hourly=precipitation&models={era5|era5_land|era5_seamless|best_match}&timezone=America/Argentina/Buenos_Aires` → 200 en los cuatro, unos 1,05 s.
- Resultado para el **2 de abril de 2013** en La Plata:
  - `era5`, `era5_seamless` y `best_match`: **13,4 mm en el día** (17,3 mm en 48 h), con un máximo horario de 3,0 mm a las 22:00.
  - `era5_land`: **todos los valores `null`** (48 nulls). Parece que la celda cae sobre el agua o el borde del dominio.
  - Los registros que se suelen citar para ese día están en el orden de varios cientos de mm (más de 300 mm en pocas horas). No los verifiqué en esta fase.
- **Conclusión:** ERA5 (≈25-30 km) **no sirve para backtesting de lluvia convectiva extrema**. Subestima en más de un orden de magnitud. Para backtesting hacen falta pluviómetros (SMN histórico por convenio, INA, CABA, redes provinciales) o satélite (IMERG Final, sin verificar).

## 3. GDACS: ⚠️ (solo contexto)

- **RSS:** `https://www.gdacs.org/xml/rss.xml` → 200, 701 KB, 229 ítems (13 FL). Guardé solo la cabecera (`rss_sample_head.xml`).
- **API:** `https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=FL&country=ARG&fromDate=..&toDate=..` → 200 GeoJSON.
  - **Gotcha:** sin `alertlevel=green;orange;red` devuelve solo naranja/rojo (1 evento FL en Argentina, del 2003). Con ese parámetro devuelve 59 eventos FL en Argentina entre 2012-11 y 2026-10.
  - Varios tienen centroide en el AMBA, entre ellos el `eventid 4046` (2013-04-01, -34.48/-58.68) y otros de 2022 a 2026. **Todos son Green.**
  - `source = GLOFAS`, con `severity 0` / "Magnitude 0". `datemodified` cae entre 1 y 15 días después de `fromdate`.
- **Conclusión:** detecta eventos de forma tardía y gruesa, sin valor para alerta de corto plazo en el AMBA. Puede servir como etiqueta histórica débil para validar.

## 4. Otras fuentes

### 4.1 METAR (aviationweather.gov, NOAA): ✅

- `https://aviationweather.gov/api/data/metar?ids=SABE,SAEZ,SADF,SADP,SADM,SADL&format=json&hours=3` → 200, 0,32 s, 9,3 KB. Cubre **Aeroparque (SABE), Ezeiza (SAEZ), San Fernando (SADF), El Palomar (SADP), Morón (SADM) y La Plata (SADL)**.
- A las 02:17Z ya estaban los de las 02:00Z (**menos de 20 min de latencia**). Se vio `-RA` en SABE/SADP y `-DZ` en SAEZ a la 01Z.
- Sin auth. Datos públicos de NOAA. No revisé la política de rate limit de AWC: usar con moderación (1 llamada cada 5-10 min para todas las estaciones).
- Limitación: los METAR argentinos **no informan milímetros**. Solo dan fenómeno e intensidad (`-RA`, `+TSRA`), útil como indicador binario o de intensidad. No hay METAR del Observatorio Central (no es aeródromo).

### 4.2 SYNOP vía Ogimet: ⚠️

- `https://www.ogimet.com/cgi-bin/getsynop?block=87585&begin=202611031200&end=202611040300` → 200, SYNOP crudo horario del Observatorio Central (87585). A las 02:17Z llegaba hasta la 01Z (~1 h).
- La precipitación solo viene en los mensajes de 18Z/00Z/06Z/12Z (grupo `6RRRt`). Por ejemplo `60121` a las 00Z: 12 mm en 6 h (decodificación manual, a revalidar con un parser).
- Ogimet es un servicio privado y gratuito. **No verifiqué sus términos ni sus límites**: no conviene depender de él para producción.

### 4.3 GOES-19 en AWS Open Data: ✅ GLM / ⚠️ ABI

- `https://noaa-goes19.s3.amazonaws.com/?list-type=2&prefix=GLM-L2-LCFA/2026/308/02/` → 200. Hay un archivo cada 20 s, de unos 370-390 KB, con `LastModified` unos 27 s después del inicio del período. Sin auth, datos NOAA de dominio público. Sirve para **detectar actividad eléctrica convectiva** sobre el AMBA casi en tiempo real.
- `ABI-L2-RRQPEF` (tasa de lluvia estimada, full disk cada 10 min, ~2 MB): **el último archivo disponible era del 2026-11-02 16:50Z**, con los días 307 y 308 vacíos. El producto existe, pero hay huecos. No verifiqué la calidad de la estimación sobre el AMBA.
- Gotcha: es NetCDF4 y hay que procesarlo (xarray/netCDF4) dentro del wrapper de RAM. Los archivos son chicos, así que no es problema.

### 4.4 WMO Alert Hub / registro de fuentes CAP: ✅ (confirmación)

- `https://severeweather.wmo.int/json/sources.json` → 200. La entrada `ar-smn-es` lista `capAlertFeed: https://ssl.smn.gob.ar/CAP/AR.php`, `capAlertFeedStatus: operating`, `sourceIsOfficial: true`. Así que el agregador de la OMM consume la misma fuente: no aporta datos nuevos, pero valida que es el canal oficial.
- **No verifiqué** Google Public Alerts (por lo que sé fue discontinuado como producto independiente) ni un endpoint del Alert Hub de la OMM/IFRC que re-sirva los CAP de Argentina.

### 4.5 Meteostat: ⚠️

- `https://data.meteostat.net/hourly/2026/87582.csv.gz` (Aeroparque) → 200, 70 KB, `last-modified` del mismo día. El viejo `bulk.meteostat.net/v2/...` sigue respondiendo, pero con fecha de 2025.
- **Gotcha:** la columna `prcp_source` muestra `metno_forecast`, es decir, la lluvia **viene rellenada con pronóstico**, no observada. Además el archivo trae filas futuras (hasta el 13/11). Solo sirve para backtesting si se filtra por fuente observada, y no aporta lluvia observada para estas estaciones.
- Licencia: no pude extraer el texto de la página de términos (vino sin contenido legible). Según lo que sé, es **CC BY-NC 4.0** (no verificado).

### 4.6 No verificadas (pendientes, requieren registro)

- **GPM IMERG Early/Late** (NASA, 30 min, unas 4 h de latencia en Early): requiere cuenta Earthdata. No probado.
- **GSMaP NRT** (JAXA, horario): requiere registro. No probado.
- **Weather Underground / estaciones ciudadanas (PWS):** la API requiere clave (y en general ser dueño de una estación). No probado.
- **Pluviómetros de CABA (BA Data) y de la provincia, INA:** corresponden al área de hidrología.

## Recomendación para la arquitectura

1. **Alertas oficiales:** consultar `ssl.smn.gob.ar/CAP/AR.php` cada 5 min, descargar los CAP nuevos (deduplicar por `identifier`), filtrar por `expires` y cruzar los polígonos con los partidos del AMBA. Consultar en paralelo `avisocorto_GeoRSS.xml` cada 5 min.
2. **Estado observado:** METAR de las 6 estaciones cada 5-10 min (fenómeno), `tiepre` cada hora y GLM (rayos) cada 1-5 min.
3. **Pronóstico:** Open-Meteo hourly en una grilla chica (≤20 puntos), sin tomar `minutely_15` como nowcast real. Confirmar si el proyecto califica como no comercial.
4. **Huecos críticos que hay que resolver por otra vía:** lluvia observada sub-horaria (pluviómetros), radar (convenio con SMN) y caudales y niveles de ríos (hidrología, no GloFAS).

## Muestras guardadas (`data/samples/meteo/`)

- `smn/`: `cap_AR_rss.xml`, `cap_rss_headers.txt`, `cap_xml/*.xml` (74 CAP), `avisocorto_GeoRSS.xml`, `avisocorto.xml` (legado), `estado_tiempo_sample.txt`, `datohorario_20261102.txt`, `zip_*.bin`, `estilo_cap.xsl`
- `openmeteo/`: `forecast_caba_minutely15.json`, `fc_headers.txt`, `flood_{lujan,reconquista,matanza}.json`, `flood_lujan_2015.json`, `flood_lujan_ensemble_head.json`, `archive_laplata_20130402_*.json`, `om_terms.html`, `om_pricing.html`
- `gdacs/`: `events_fl_arg.json`, `events_fl_arg_alllevels.json`, `events_all_arg.json`, `events_fl_recent.json`, `rss_sample_head.xml`
- `otros/`: `metar_amba.{json,txt}`, `ogimet_synop.txt`, `goes19_glm_list.xml`, `meteostat_87582_2026.csv.gz`, `wmo_alerthub_source_ar-smn.json`, `ms_terms.html`
