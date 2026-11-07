# Fuentes de datos: ríos, arroyos y mareas (sudestada), AMBA

**Fase 0: verificación de accesibilidad por máquina**
Fecha de las pruebas: 2026-11-03, entre 23:10 y 23:25 ART (2026-11-04 02:10–02:25 UTC).
Método: `curl` desde la PC del proyecto, sin navegador headless. Muestras crudas en `data/samples/hidro/`. Son datos no confiables, solo para inspección.

Todo lo que aparece abajo se probó de verdad. Lo que no pude verificar se dice explícitamente.

---

## Tabla resumen

| # | Fuente / endpoint | Clasif. | Formato | Auth | Frecuencia | Latencia observada | Cobertura AMBA |
|---|---|---|---|---|---|---|---|
| 1a | SHN – API JSON alturas horarias `hidro.gob.ar/api/v1/AlturasHorarias/{COD}/{yyyymmddHHMM}` | ✅ | JSON | No | Horaria (hh:45) | ≤ 30 min | Martín García, San Fernando, Buenos Aires (Palermo), Pilote Norden, La Plata, Atalaya, Oyarvide (+ costa) |
| 1b | SHN – CSV alturas horarias `AlturasHorarias.asp?export=csv` | ✅ | CSV `;` (windows-1252) | No | Horaria | ≤ 30 min | Las mismas 13 estaciones, 10 días hacia atrás |
| 1c | SHN – Pronóstico mareológico RdP (`pronostico.asp` + RSS `PMrss.asp`) | ⚠️ | HTML / RSS con HTML dentro | No | 3 por día (07, 15, 23 h) | Se publica en hora | La Plata, Buenos Aires, San Fernando, Oyarvide |
| 1d | SHN – Avisos/Alertas/Ceses de crecida (RSS `AACrioplarss.asp`) | ⚠️ | RSS con texto libre | No | Por evento | No observable (no había evento vigente) | Río de la Plata interior y exterior |
| 1e | SHN – Modelo de altura total (PNG `api.shn.gob.ar/imagenes-modelo/...`) | ⚠️ | PNG (mapas) | No | ~diaria | Last-Modified 22:58 UTC | Solo imágenes |
| 2a | INA – API a5 `alerta.ina.gob.ar/a5/obs/...` (observaciones) | ✅ | JSON / CSV / GeoJSON / WaterML2 | No (series `public`) | Depende de la red: 15 min a 12 h | 18–75 min | ~280 estaciones en el AMBA (muchas de prueba o inactivas) |
| 2b | INA – API a5 pronósticos `a5/sim/calibrados/432/corridas/last` | ✅ | JSON | No | Diaria (corrida 12 UTC) | — | **San Fernando**: horario hasta +4 días con cuantiles p05–p95 |
| 2c | INA – Archivos de productos `alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/` | ⚠️ | JSON / CSV / PNG (listado de directorio) | No | Varía; muchos archivos viejos | Prono_SanFernando.json: 00:13 UTC | San Fernando, Campana, Escobar(viejo), Zárate, Delta |
| 3 | ACUMAR (web, CKAN `datos.acumar.gob.ar`, red_acumar en INA) | ❌ | — | — | — | Sin datos recientes | Ninguna fuente pública en tiempo real |
| 4a | ADA (Autoridad del Agua PBA) – `gis.ada.gba.gov.ar/data/niveles_escalas` | ❌ | SPA (Vue) + JWT | **Sí (login)** | — | — | No accesible |
| 4b | COMIREC (Reconquista) – `gba.gob.ar/comirec` | ❌ | Institucional | — | — | — | No publica datos |
| 5 | Prefectura Naval – `contenidosweb.prefecturanaval.gob.ar/alturas/` | ⚠️ | HTML (tabla) | No | 2 por día (00 y 12 h) | ~11 h | Zárate, Campana, Escobar, Tigre, Dique Luján, San Fernando, San Isidro, Olivos, Buenos Aires, La Plata, Martín García, Guazucito, Chaná Miní |
| 6a | SNIH (SSRH) – `snih.hidricosargentina.gob.ar/MuestraDatos.aspx/*` | ✅ (no documentada) | JSON (ASP.NET PageMethods, POST) | No | Horaria | ~20 min | Río Luján (Luján), Reservorio Tecnópolis (A° Medrano), Zárate, Areco, Delta |
| 6b | UNLu – Red Hidrométrica Cuenca Luján `redhidro.unlu.edu.ar/api/getmediciones/...` | ⚠️ | JSON | Cookie de sesión "invitado" | 15 min | ~20 min | 6 puentes sobre el río Luján (Manuel J. García → Ruta 9) |
| 6c | Sensores municipales (Tigre, San Fernando, Tres de Febrero, etc.) | ❌ (no verificado) | — | — | — | — | No encontré ninguno público |

**Recomendación base:** usar **SHN API/CSV** para el estuario (sudestada) y como residuo meteorológico (observado − astronómico). Sumar **INA a5** para el Delta, los arroyos del sur (Las Piedras, San Francisco), el pronóstico probabilístico de San Fernando y los umbrales de alerta/evacuación. Usar **SNIH + UNLu** para el río Luján. Los avisos y alertas oficiales salen del **RSS de SHN**.

---

## 1. Servicio de Hidrografía Naval (SHN)

Dominios: `www.hidro.gov.ar` y `www.hidro.gob.ar` (los dos responden igual). Servidor IIS/ASP clásico, sin bloqueos y sin problemas de SSL. `robots.txt` → 404, o sea que no hay restricciones declaradas.

### 1a. API JSON de alturas horarias ✅ (no documentada, la usa la propia web)

- La encontré inspeccionando `oceanografia/js/grafico-alturas.js`.
- **URL probada:** `https://www.hidro.gob.ar/api/v1/AlturasHorarias/BSAS/202611032245` → **HTTP 200**, `application/json`, 0,11–0,27 s.
- Sin la fecha (`/api/v1/AlturasHorarias/SFER`) → 404. La fecha es obligatoria (`yyyymmddHHMM`, hora local).
- **Respuesta:** `{"mareografo","observaciones","astronomica":[{fecha,altura}],"lecturas":[{fecha,altura}]}`
  - `lecturas`: alturas observadas desde ~12 h antes de la fecha pedida. Se probó BSAS: 13 lecturas, de 10:45 a 22:45.
  - `astronomica`: marea astronómica horaria, de −12 h a **+8 h** de la fecha pedida. Sirve para calcular **residuo meteorológico = lectura − astronómica**, que es el indicador directo de sudestada.
  - Las fechas vienen en hora local (ART, UTC−3) y sin zona horaria. Se verificó cruzando con INA, que guarda los mismos valores en UTC.
- **Códigos de estación** (salen del HTML): `MAGA` Martín García, `SFER` San Fernando, `BSAS` Buenos Aires, `PNOR` Pilote Norden, `LPLA` La Plata, `ATAL` Atalaya, `OYAR` Oyarvide (Torre Oyarvide, canal Punta Indio km 133), `SCLE` San Clemente, `MDPL`, `PTBL`, `SAES`, `PLYA`, `USHU`.
- **Gotcha:** si se pide una fecha vieja (`SFER/202501151245`), devuelve `astronomica` pero `lecturas: []`. **No sirve para descargar historia.**
- Ubicaciones (de `oceanografia/mareografos.asp`): San Fernando = espigón del Yacht Club Argentino, río Luján y canal de Vinculación (34°26'02"S 58°32'25"W). Buenos Aires = muelle Club de Pescadores, frente a Aeroparque (34°33'39"S 58°23'56"W). La Plata = muelle PNA I. Monte Santiago. Atalaya = muelle del A° Atalaya (Magdalena). Torre Oyarvide = canal Punta Indio, pares 26–27.
- Muestras: `shn_api_BSAS.json`, `shn_api_SFER.json`, `shn_api_OYAR.json`.

### 1b. CSV de alturas horarias ✅

- **URL:** `https://www.hidro.gov.ar/oceanografia/AlturasHorarias.asp?export=csv` → **HTTP 200**, `text/csv; Charset=windows-1252`, 20 KB.
- Formato: separador `;` y decimal `.`. Cabecera: `Fecha y hora;Martín García;San Fernando;Buenos Aires;Pilote Norden;La Plata;Atalaya;Oyarvide;San Clemente;Mar del Plata;Puerto Belgrano;San Antonio Este;Punta Loyola;Ushuaia`.
- Trae **240 filas = 10 días horarios**, de la más nueva a la más vieja. Fechas `dd/mm/yyyy HH:MM` en hora local.
- Los faltantes aparecen como `S/D` (se vieron en Oyarvide y Pilote Norden).
- **Latencia:** a las 23:13 ART ya estaba la lectura de las 22:45, o sea ≤ 28 min.
- La misma tabla está en HTML en `AlturasHorarias.asp` y en RSS en `/rss/AHrss.asp`.
- Gotcha: la codificación es windows-1252, no UTF-8.
- Muestra: `shn_alturas.csv`.

### 1c. Pronóstico mareológico del Río de la Plata ⚠️ (scraping)

- **URLs:** `https://www.hidro.gov.ar/oceanografia/pronostico.asp` (HTML) y `https://www.hidro.gob.ar/RSS/PMrss.asp` (RSS 2.0, ISO-8859-1, con HTML dentro de CDATA). Las dos → **200**.
- Contenido: fecha de emisión, validez (ej. "desde 23:00 del 03/11 hasta 11:00 del 04/11") y una corrección en texto libre para RdP interior y exterior. Ejemplo: "CINCUENTA CENTÍMETROS SOBRE LOS VALORES INDICADOS EN LAS TABLAS DE MAREA…". Además trae una tabla de *valores corregidos* (pleamar/bajamar, hora, altura) para Puerto La Plata, Puerto Buenos Aires (Muelle de Pescadores), San Fernando y Canal Punta Indio (Oyarvide).
- Frecuencia, según los metadatos de Datos Abiertos (`DA/MProno.asp`): **3 emisiones por día, a las 07, 15 y 23 h, con 12 h de validez**. Puede haber rectificativos.
- Gotcha: la corrección viene en texto y en mayúsculas ("CINCUENTA CENTÍMETROS"), así que hay que parsear números escritos en palabras. La tabla de valores corregidos es más fácil de parsear.
- Muestras: `shn_pronostico.html`, `shn_rss_PMrss.xml`.

### 1d. Avisos, alertas y ceses de crecida/bajante ⚠️

- **RSS:** `https://www.hidro.gov.ar/rss/AACrioplarss.asp` (Río de la Plata) → **200** `text/xml`. Para la costa bonaerense: `AACcostarss.asp`. HTML: `http://www.hidro.gov.ar/Oceanografia/AACriopla.asp`.
- Al momento de la prueba decía: "NO HAY NINGUN AVISO / ALERTA o CESE VIGENTE". **No pude ver el formato de un aviso real.** Hay que capturar uno durante un evento antes de escribir el parser. Sugerencia: detectar cuando cambia el texto y alertar por cualquier contenido distinto de "NO HAY NINGUN".
- También publican en X/Twitter como `@SHN_ALERTAS` (no lo probé).

**Umbrales oficiales SHN** (de `oceanografia/ServiciosAACB.asp`, textual; "Todos los niveles referidos al cero del Riachuelo"):

| Nivel | Zona costera Norte + CABA | Zona costera Sur del conurbano |
|---|---|---|
| **Aviso de crecida** | > 2,00 m | > 2,10 m |
| **Alerta de crecida** (extraordinaria) | > 2,60 m | > 2,70 m |
| Aviso de bajante | < −0,50 m | < −0,50 m |
| Alerta de bajante | < −0,80 m | < −0,80 m |

> ⚠️ **Datum:** los umbrales están referidos al **cero del Riachuelo**. Las alturas de los mareógrafos se publican referidas al "Plano Único de Reducción de Sondajes del Río de la Plata" (aclaración en `AlturasHorarias.asp`). **No verifiqué si los dos ceros coinciden ni cuál es la diferencia.** Hay que confirmarlo con SHN (pronomarea@hidro.gov.ar) antes de comparar lecturas contra umbrales.

### 1e. Modelo numérico de altura total ⚠️

- `https://www.hidro.gov.ar/smara/MAlturaTotal.asp` es un carrusel de PNG en `https://api.shn.gob.ar/imagenes-modelo/surges-marea/alturatotal_{N}.png` (200; `alturatotal_0.png` pesa 148 KB, Last-Modified 2026-11-03 22:58 UTC).
- `api.shn.gob.ar` expone un *directory listing* (`imagenes-modelo/`: SANDRA, surges, surges-marea, olas, etc.).
- **Solo hay imágenes (mapas). No encontré series numéricas.** El SHN aclara que el modelo "NO reemplaza al Pronóstico Mareológico".
- Además, el "Modelo Empírico" (`hidro.gob.ar/prediccion-marea/`, Angular, API `/prediccion-marea/calc/...`) es **solo marea astronómica** (13 armónicos). No aporta pronóstico meteorológico.

### Términos / licencia SHN
El pie dice "© Copyright – Todos los Derechos Reservados – Servicio de Hidrografía Naval". La sección "Datos Abiertos" (`/DA/DatosAbiertos.asp`) lista "Datos Horarios de Marea" y "Pronósticos de Marea" (frecuencia "Horaria") **sin licencia explícita**. **No encontré términos de uso de la API.** Conviene pedir autorización o confirmación por escrito.

---

## 2. INA – Instituto Nacional del Agua

### 2a. API a5 (alerta5DBIO) – observaciones ✅

- Base `https://alerta.ina.gob.ar/a5/`. Código fuente: https://github.com/cerobpm/a5. El README (`a5/html/README.html`) dice que la UI requiere usuario, pero **los endpoints REST de series públicas responden sin autenticación**.
- **Endpoints probados (todos HTTP 200):**
  - `a5/obs/puntual/estaciones?format=json` → 4.695 estaciones, 2,8 MB, 1,1 s. ⚠️ El parámetro `limit` se ignora.
  - `a5/obs/puntual/series?format=json&estacion_id=52` → series de una estación (metadatos, `date_range`, pronósticos asociados).
  - `a5/obs/puntual/series?format=geojson&var_id=2` → 577 KB.
  - `a5/obs/puntual/series/{series_id}/observaciones?timestart=2026-11-02T00:00:00-03:00&timeend=2026-11-04T06:00:00-03:00&format=json` (también `format=csv`).
    - Respuesta: `[{id,series_id,timestart,timeend,timeupdate,valor,...}]`, con tiempos en **UTC (`Z`)**.
- No funcionaron: `a5/obs/puntual/redes` → 404; `res/mapa` → 401; `tablero-de-monitoreo` → redirige a login.
- **Los metadatos de estación traen `nivel_alerta`, `nivel_evacuacion`, `nivel_aguas_bajas` y `cero_ign`.** Están en la tabla de umbrales de abajo.

**Series clave verificadas (última observación al 2026-11-04 ~02:15 UTC):**

| Estación (id) | Serie H | Red / origen | Último dato (UTC) | `timeupdate` | Observación |
|---|---|---|---|---|---|
| San Fernando (52) | 52 | `alturas_prefe` | 00:45 | 01:32 | Valor 0,96 = **SHN SFER 21:45**: INA espeja SHN. Tiene pronóstico (serie 26202). |
| Buenos Aires (85) | 85 | `alturas_prefe` | 00:45 | 01:32 | Valor 1,15 = SHN BSAS 21:45 |
| La Plata (1708) | 3314 | PVNyMM | 00:45 | 02:00 | |
| Atalaya (1739), Pilote Norden (1740) | 3344, 3345 | Mareógrafos SHN | 2026-11-03 20:45 (fin de date_range) | — | |
| Canal Seoane (149) | 149 | INA Delta y AMBA | 01:45 | 02:03 | ~18 min de latencia |
| A° San Francisco (1744) | 3349 | INA Delta y AMBA (Sarandí–Sto. Domingo) | 01:45 | 02:03 | Arroyo urbano del sur |
| A° Las Piedras – Rep. del Líbano (1743) | 3348 | INA Delta y AMBA | 2026-11-01 20:25 | — | **Hace 2 días que no transmite** |
| Luján – Luján (2128) | 6936 | RHN-SAT | 00:00 | 02:00 | Mismo valor que SNIH 14008 (ver 6a) |
| Paraná de las Palmas – Zárate (5907) | 29437 | RHN-SAT | 00:00 | 02:01 | Tiene pronóstico |
| Tigre (49), Dique Luján (50), San Isidro (53), Olivos (54), La Plata PNA (86) | 49, 50, 53, 54, 86 | `alturas_prefe` | 2026-11-03 00:00 | — | Solo lecturas diarias o semidiarias de Prefectura (sin dato de las 12 h al momento) |
| Buenos Aires PVNyMM (1709), Braga (1702), Paraná Miní (1877) | — | — | 2021 / 2023 | — | **Inactivas** |
| red ACUMAR (872–896, 5954) | Ph/P | red ACUMAR | — | — | **Sin observaciones desde 2023-01-01** (serie 769 vacía) |
| Red UNLu Luján (933–938) | — | `lujan_api` | — | — | `public: false` |

Gotchas de INA:
- Hay más de 100 estaciones "ZPrueba_*" en la red RHN-SAT que hay que filtrar.
- Muchas series tienen `date_range` nulo.
- Las estaciones `alturas_prefe` mezclan datos de SHN (San Fernando, Buenos Aires, horarios) con lecturas manuales de Prefectura (Tigre y otras, diarias).
- Zonas horarias: los tiempos de la serie Luján 6936 (00:00Z) y de SNIH 14008 (02:00Z) tienen el mismo valor (0,46). Uno de los dos interpreta mal la zona horaria. **Hay que validar con un evento conocido.**

**Licencia / términos INA a5:** no encontré términos publicados. `robots.txt` → 404. **No verificado.**

### 2b. Pronóstico San Fernando (API a5) ✅

- `https://alerta.ina.gob.ar/a5/sim/calibrados/432` → modelo `marea_rdp_regre` ("regre_sfer"), paso 1 h, salida en la estación 52.
- `https://alerta.ina.gob.ar/a5/sim/calibrados/432/corridas/last?series_id=26202&includeProno=true&format=json` → **200**, 190 KB, 0,15 s.
  - `forecast_date` 2026-11-03T12:00Z. Cuantiles `main`, `p05`, `p25`, `p75`, `p95`.
  - Horizonte: hasta **2026-11-07 12:00Z (+4 días)**. 337 pasos `main`, incluido el *hindcast* desde el 24/10. Máximo `main` pronosticado: 2,49 m.
- Sin `includeProno=true` devuelve la corrida sin valores.
- Otros calibrados (288 HIDRODELTA, 308 marea_rdp_0, 454, 543 Delft3D) → `corridas/last` responde **404 "Corrida not found"**. Puede ser que no sean públicos o que se consulten de otra forma. **No verificado.**
- `sim/calibrados?grupo_id=1` lista todos los modelos (362 KB).

### 2c. Productos en archivos (directory listing) ⚠️

- `https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/` → listado de JSON, CSV y PNG.
  - `Prono_SanFernando.json`: 519 KB, Last-Modified 2026-11-04 00:13 UTC, corrida 1002350.
  - `Prono_Campana.json`: 2026-11-04 00:25 UTC.
  - `Prono_Escobar.csv`: **2021, viejo**.
  - Además: Zárate, Lima, Brazo Largo, Carabelas, Nueva Palmira, y PNG de 15 días para Buenos Aires.
- `.../plots/hidrodelta/` → PNG del modelo HIDRODELTA (INTA Delta, Carapachay, etc.). Son solo imágenes.
- `ina/06-INFORMES/TablaAlerta.md`: reporte operativo de la Cuenca del Plata (último de 2023). No es del AMBA.
- `ina/08-PRONOSTICOS/graficos/`: CSV obs/prono del Paraná medio (Corrientes, Goya, etc.) y Nueva Palmira.
- Gotcha: no hay contrato estable. Los nombres de archivo tienen mayúsculas y minúsculas inconsistentes y conviven duplicados de distintas fechas. Siempre conviene preferir la API 2b.
- **Río Reconquista / Matanza:** no encontré estaciones H de INA en tiempo real. Para Luján: SAT 2128 (Luján) en INA, más SNIH y UNLu (ver 6).

---

## 3. ACUMAR ❌

- `https://www.acumar.gob.ar/` → 200. El sitio WordPress tiene solo 66 páginas en el sitemap y **ninguna de monitoreo hidrometeorológico**. `/monitoreo-hidrometeorologico/` → 404. `monitoreo.acumar.gob.ar` no resuelve (curl 000).
- CKAN `https://datos.acumar.gob.ar/api/3/action/package_list` → 200, 27 datasets. El único de agua es `redes-de-monitoreo-de-agua`: CSV de **calidad** de agua superficial, subterránea y humedales (campañas, último 2026-02-26), con **licencia ODbL**. No es hidrometría en tiempo real.
- La "red ACUMAR" de 25 pluviómetros que figura en INA a5 **no tiene observaciones desde 2023-01-01** (probado con las series 769, 2985 y 3281).
- `monitorpisa.acumar.gob.ar` → 200, pero es seguimiento del plan (PISA), no datos.
- **Conclusión: no hay datos públicos de alturas en la cuenca Matanza-Riachuelo accesibles por máquina.**

## 4. Autoridad del Agua PBA (ADA) y COMIREC ❌

- `https://www.ada.gba.gov.ar/` → 200. La página "Red Hidrométrica" enlaza a:
  - `https://gis.ada.gba.gov.ar/gis/?l=red_hidrometrica` (visor con la capa de estaciones).
  - `https://gis.ada.gba.gov.ar/data/niveles_escalas` y `.../monitoreo-participativo-precipitaciones`: SPA Vue con reCAPTCHA. El bundle muestra rutas protegidas (`auth:"niveles_escalas"`, JWT + CSRF + x_token). **Requiere login.**
  - `/geoserver/wfs` → 404. No encontré un WMS/WFS público.
  - Los niveles son de "monitoreo participativo" con escalas leídas a mano. No es telemetría.
- COMIREC: `https://www.gba.gob.ar/comirec` → 200. Es institucional (obras, noticias, mapas). **No publica datos ni alertas.** `comirec.gba.gob.ar` y `www.comirec.gba.gov.ar` no resuelven.
- COMILU (`gba.gob.ar/comilu/estado_del_rio`) remite al sistema de UNLu (ver 6b).

## 5. Prefectura Naval Argentina ⚠️

- `https://www.prefecturanaval.gob.ar/` → **timeout** (25 s, dos intentos).
- La página útil es **`https://contenidosweb.prefecturanaval.gob.ar/alturas/`** → **200**, HTML UTF-8, 113 KB, 0,17 s.
  - Columnas: Puerto, Río, Últ. registro, Variación, Periodo (h), Fecha Hora, Estado (CRECE/BAJA/ESTAC./ALERTA), Registro anterior, Fecha anterior, **Alerta, Evacuación**.
  - Historial de 7 días: `?page=historico&tiempo=7&id={id}` → 200 (HTML, 288 KB).
- Frecuencia: **cada 12 h (lecturas de 00 y 12 h)**. A las 23:10 seguía mostrando la de las 12:00, o sea **~11 h de atraso**. Escobar mostraba la de las 00:00, con más de 23 h de atraso.
- Sirve como fuente de **umbrales** y como respaldo. No sirve para alerta temprana de 5–10 min.
- Gotcha: no hay robots.txt (404). La tabla tiene `<td>` con mucho espacio en blanco. Las fechas vienen en formato `03/NOV/26 - 1200`.
- Muestras: `pna_alturas.html` (tabla) y `ina_a5_estaciones_amba_resumen.txt` (umbrales vía INA).

### Umbrales de alerta / evacuación por escala (Prefectura; INA a5 los replica)

| Puerto | Alerta (m) | Evacuación (m) | Aguas bajas (m, INA) | Nota |
|---|---|---|---|---|
| Buenos Aires | 3,30 | 3,90 | 0,21 | |
| La Plata | 2,50 | 2,80 | 0,30 | |
| San Fernando | 3,00 | 3,50 | 0,33 | INA: `cero_ign` = −0,53 |
| San Isidro | 3,00 | 3,50 | 0,30 | |
| Olivos | 3,00 | 3,80 | 0,20 | |
| Tigre | 3,30 | 3,80 | 0,30 | |
| Dique Luján | 2,30 | 2,80 | 0,30 | |
| Escobar | 3,00 | 3,50 | 0,20 | |
| Campana | 2,20 | 2,45 | — | |
| Zárate | **2,20 (PNA) / 2,00 (INA)** | **2,40 (PNA) / 2,20 (INA)** | 0,25 | **Discrepancia entre fuentes** |
| Martín García | 2,50 | 5,00 | 0,20 | |
| Guazucito | 2,20 | 2,40 | 0,30 | |
| Chaná Miní | 3,20 | 3,80 | 1,00 | |
| Río Luján – Luján (SAT 2128 / UNLu 933) | 5,06 / 5,00 | — | — | Solo en INA |
| Club de Pescadores, Areco (113) | 3,40 | 5,00 | — | Solo en INA (no pública) |

> ⚠️ **Estos umbrales están en la escala de Prefectura** y no son los mismos que los de SHN (aviso 2,00 / alerta 2,60 en el cero del Riachuelo). En Buenos Aires, los valores de Prefectura coinciden exactamente con los del mareógrafo SHN (12:00 → 1,09 = SHN 11:45; 00:00 → 1,71 = SHN 23:45). En San Fernando **no coinciden** (PNA 0,90 contra SHN 0,99; PNA 1,50 contra SHN 1,58), así que no sería la misma regla ni el mismo instrumento. Antes de definir umbrales automáticos hay que **confirmar el datum de cada estación**.

## 6. Otras fuentes

### 6a. SNIH – Sistema Nacional de Información Hídrica (SSRH) ✅ (endpoints internos)

- `https://snih.hidricosargentina.gob.ar/` → 200. La descarga "oficial" de historia es por formulario de solicitud. Pero la web usa *PageMethods* ASP.NET abiertos, sin autenticación (todos HTTP 200, JSON):
  - `POST /Filtros.aspx/LeerEstaciones` con body vacío y `Content-Type: application/json; charset=utf-8` → 1.451 estaciones, 1,35 MB. Ojo: lat/lon vienen **positivas**, hay que negarlas.
  - `POST /MuestraDatos.aspx/LeerDatosActuales` con body `{estacion:"14008" }` → último dato.
  - `POST /MuestraDatos.aspx/LeerUltimosRegistros` con body `{fechaDesde:"2026-11-03", fechaHasta:"2026-11-04", estacion:"14008", codigo:"1" }` → serie horaria.
- Estaciones AMBA con datos al momento de la prueba: **14008 Río Luján – Luján** (último 02:00Z, 0,46 m, ~20 min de latencia) y **14011 Reservorio Tecnópolis, A° Medrano** (01:45Z, 0,03 m). Otras listadas: 14001 Zárate, 14051 San Antonio de Areco, 14075 A° Chañaritas, 66831 A° Toro, 68173 Paraná Miní, 66832 Canal Onda.
  - 61743 y 66831 respondieron `Mediciones: []`.
- Fechas en formato `/Date(ms)/`. **La zona horaria no está verificada** (ver gotcha de INA).
- Gotchas: API no documentada, puede cambiar. El JSON usa claves sin comillas en el body, igual que la web. No encontré términos de uso.

### 6b. UNLu – Red Hidrométrica de la Cuenca del Río Luján ⚠️

- `https://redhidro.unlu.edu.ar/` (Django) → 200. Botón "Ingresar como invitado" → `/index`.
- La API **exige cookie de sesión**: sin cookie, `api/equipos/` → **403** "Authentication credentials were not provided". Con la cookie `sessionid` que se obtiene en un GET a `/index` (sin credenciales) → 200.
  - `GET /api/equipos/` → 6 equipos: 1377 Pte. Manuel J. García, 1804 Pte. Olivera, 1375 Pte. Jáuregui, 1803 Pte. Ruta 6, 1806 Pte. Ruta 8, 1805 Pte. Ruta 9.
  - `GET /api/getmediciones/43/2026-11-03/2026-11-04` (sensor 43 = nivel de agua en m; 16 = batería) → `{dates:[...], equipos:{id:[{fechamedicion, valor(string)}]}}`.
- Frecuencia **15 min**. Último dato 23:00 local, consultado a las 23:22 → **~20 min**. Pte. Manuel J. García estaba **desactualizado desde las 08:20**.
- Hay historia disponible: un mes pesa 960 KB, en ~1 s.
- El sitio aclara: "Los datos … están sujetos a verificación posterior". **No hay licencia publicada.** Conviene contactar a cidetic.unlu@gmail.com antes de producción.

### 6c. Sensores municipales ❌ (no verificado)
No encontré endpoints públicos de Tigre, San Fernando, Tres de Febrero ni del Reconquista. Busqué en la web y en los sitios provinciales. La red INA-INTA del Delta (16 estaciones "red INA Delta y AMBA" en a5) es lo más cercano y ya está cubierta en 2a. CONAE: no lo probé (fuera de alcance para alturas en tiempo real).

---

## Gotchas transversales

1. **Datums distintos:** SHN usa el plano de reducción del RdP para las lecturas y el cero del Riachuelo para los umbrales. Prefectura usa escalas locales. INA guarda `cero_ign` solo en algunas estaciones. No hay que mezclar umbrales y lecturas de fuentes distintas sin conversión validada.
2. **Zonas horarias:** SHN publica en hora local sin offset. INA en UTC. SNIH en `/Date(ms)/` con la zona dudosa. Hay que normalizar todo a UTC y validar contra un evento conocido.
3. **INA espeja a SHN** para San Fernando y Buenos Aires, con 45–75 min más de atraso. Para el estuario conviene ir directo a SHN.
4. **Estaciones muertas:** A° Las Piedras (2 días sin dato), Pte. M. J. García (UNLu, desde la mañana), red ACUMAR (desde 2023), BsAs PVNyMM (2021). El sistema necesita detección de *staleness* por estación.
5. **Sin licencias explícitas** en SHN, INA, SNIH y UNLu. Solo ACUMAR CKAN es ODbL, y no es útil para esto. Recomiendo pedir autorización formal o, al menos, avisar a los organismos, sobre todo si se consulta cada 5–10 min.
6. **Carga:** todos los endpoints responden en menos de 1 s. Una consulta cada 5–10 min es razonable. En INA, `obs/puntual/estaciones` (2,8 MB) conviene cachearlo una vez por día.
7. No vi bloqueos por User-Agent, rate limit ni problemas de SSL en ninguna fuente. El dominio principal de Prefectura hizo timeout.

## Muestras guardadas (`data/samples/hidro/`)
`shn_alturas.csv`, `shn_api_*.json`, `shn_pronostico.html`, `shn_rss_*.xml`, `shn_ServiciosAACB.html` (umbrales), `shn_mareografos.html`, `ina_a5_estaciones_todas.json`, `ina_a5_estaciones_amba_resumen.txt`, `ina_series/est_*.json`, `ina_obs_*.json`, `ina_prono_sfer_432.json`, `ina_rdp_*`, `pna_alturas.html`, `snih_*.json`, `unlu_api_equipos.json`, `unlu_getmediciones_43.json`, `acumar_ckan_*.json`, más los JS de las SPA en `shn_spa/`, `ada_spa/` y `snih_js/`.
