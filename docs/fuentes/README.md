# Fuentes de datos — resumen Fase 0 (verificado 2026-11-03)

Detalle en: [meteorologia.md](meteorologia.md) · [hidrologia.md](hidrologia.md) · [ciudad-y-cuencas.md](ciudad-y-cuencas.md)

## Usables (✅)

| Señal | Fuente | Frecuencia / atraso |
|---|---|---|
| Alertas oficiales | SMN CAP `ssl.smn.gob.ar/CAP/AR.php` | por evento |
| "Está lloviendo / tormenta" en aeropuertos | METAR (aviationweather.gov) | ~30 min / <20 min |
| Rayos | GOES-19 GLM (AWS) | 20 s / ~27 s |
| Pronóstico de lluvia | Open-Meteo (no comercial, 10k llamadas/día) | horario |
| Altura Río de la Plata + marea astronómica → sudestada | SHN API `hidro.gob.ar/api/v1/AlturasHorarias/...` | horaria / <30 min |
| Delta, Luján, arroyos + umbrales alerta/evacuación + pronóstico San Fernando | INA a5 `alerta.ina.gob.ar/a5` | variable |
| Luján y A° Medrano (Tecnópolis) | SNIH (JSON interno) | horaria / ~20 min |
| Cuencas CABA (Maldonado, Medrano, Vega, Cildáñez, White…) | BA Data vía CDN | estático |
| Cuencas Matanza-Riachuelo, Reconquista, Luján, Delta | COHIFE (CC-BY-4.0) | estático |

## Con limitaciones (⚠️)
Avisos a corto plazo SMN (sin ejemplo activo) · alertas SHN (texto libre) · UNLu Luján (cookie de invitado) · Prefectura (2 lecturas/día, sirve por umbrales) · riesgo hídrico CABA (CRS GKBA sin declarar).

## No accesibles (❌)
Radar y API del SMN (requiere convenio) · SAT/pluviómetros de CABA en tiempo real · ACUMAR · ADA PBA · COMIREC · sensores municipales · RENABAP (en mantenimiento).

## Huecos críticos
1. **Lluvia medida minuto a minuto** en CABA y conurbano (no hay fuente pública).
2. **Riachuelo y Reconquista** sin datos hidrométricos públicos.
3. **Histórico real para backtesting** (ERA5/Open-Meteo subestima eventos extremos).

## Riesgos técnicos
- Ceros de escala distintos entre SHN, INA y Prefectura → confirmar conversión antes de comparar con umbrales.
- Husos horarios mezclados (local sin aclarar vs UTC).
- Estaciones caídas → detectar datos viejos por estación.
- Ninguna fuente hidrológica publica licencia → pedir autorización.

## Pedidos a organismos (convenios)
SMN (radar, API) · Ciudad de Buenos Aires (SAT) · ACUMAR · ADA PBA · COMIREC · SHN (conversión de ceros y permiso de uso).
