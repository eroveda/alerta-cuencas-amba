# Contrato de `web/data/estado.json` — versión 1

Lo genera `alertas/estado.py` (`armar_estado`) y lo consume `web/app.js`.
Si el mapa recibe una versión distinta de la que espera, **no dibuja nada** y lo avisa,
en lugar de mostrar datos mal interpretados.

**Cuándo subir `VERSION_ESQUEMA`** (en los dos archivos a la vez): al quitar o renombrar
una clave, cambiar un tipo o agregar un valor nuevo a un campo enumerado (por ejemplo, un nivel).
Agregar una clave opcional nueva no rompe al mapa y no requiere subirla.

Todas las fechas son ISO 8601 en UTC.

| Clave | Tipo | Contenido |
|---|---|---|
| `version` | int | Versión del esquema (hoy 1) |
| `generado` | fecha | Momento del poll |
| `fase` | str | Texto de la fase actual |
| `aviso_legal` | str | Leyenda "no oficial" |
| `zonas` | objeto `id → zona` | Una entrada por cuenca (ver abajo) |
| `estaciones` | lista | Estaciones hidro y meteo (ver abajo) |
| `pronostico_san_fernando` | objeto o `null` | `max_main`, `ts_max`, `max_p95`, `horas` (INA) |
| `fuentes` | objeto `nombre → {ok, error?, ...}` | Estado de cada consulta del poll |

**Zona:** `nombre` (str), `piloto` (bool), `nivel_smn` (`verde`/`amarillo`/`naranja`/`rojo`),
`alertas` (lista de `{evento, nivel, expira, descripcion, id}`),
`lluvia_obs` (`sin`/`debil`/`moderada`/`fuerte` o `null`), `tormenta_obs` (`no`/`cercana`/`si` o `null`).

**Estación**, campos comunes: `id`, `nombre`, `lat`, `lon`, `zona`, `tipo` (`hidro`/`meteo`), `ts`, `viejo` (bool).
- `hidro`: `altura` (m o `null`), `residuo` (m o `null`; solo SHN).
- `meteo`: `lluvia`, `tormenta` (mismos valores que en la zona).

## `web/data/serie.json` — versión 1

Lo genera `alertas/serie.py` (`armar_serie`) en cada poll y lo dibuja `web/grafico.js`.

| Clave | Tipo | Contenido |
|---|---|---|
| `version` | int | Versión del esquema (hoy 1; `VERSION_SERIE` en los dos lados) |
| `generado` | fecha | Momento del poll |
| `estaciones` | objeto `código SHN → {altura, astronomica, residuo}` | Cada una es una lista `[ts, valor]` ordenada; últimas 72 h y, para la marea astronómica, hasta +48 h |
| `pronostico_sfer` | lista `[ts, main, p05, p95]` | Pronóstico INA de San Fernando desde ahora hasta +48 h (`p05`/`p95` pueden ser `null`) |
