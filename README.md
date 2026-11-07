# Alerta Cuencas AMBA

Sistema cívico, abierto y sin fines de lucro de **alertas tempranas de inundación** para el AMBA, motivado por El Niño fuerte 2026-27.

> ⚠️ No es un sistema oficial. Ante emergencias seguí a SMN, Hidrografía Naval y Defensa Civil.

## Estado: Fase 0 — monitoreo (no se envían avisos)

| Fase | Qué | Estado |
|---|---|---|
| 0 | Monitoreo de todas las cuencas, sin avisos → pasa a ser el **tablero abierto** | **en curso** |
| 1 | Piloto en modo sombra **solo sudestada Costa/Delta**, avisos a Telegram interno (bloqueado: datum SHN) | pendiente |
| 2 | Piloto público vía **referentes barriales/isleños**, con hosting externo | pendiente |
| ~~3~~ | ~~Expansión cuenca por cuenca~~ — postergada | — |
| 4 | Sostenibilidad (alianzas, incidencia por apertura de datos) | pendiente |

> **Reorientación 2026-11-07:** menos construcción y foco donde hay ventaja real (sudestada). Las cuencas pluviales
> (Medrano, CABA) quedan solo en el tablero, sin avisos. Detalle y próximas acciones en
> [docs/diseno-fase1.md §0](docs/diseno-fase1.md).

## Uso

```bash
uv sync                               # instala dependencias (shapely, pytest)
.venv/bin/python -m alertas.cli zonas # arma web/data/zonas.geojson desde data/samples/geo
scripts/monitor.sh                    # consulta fuentes cada 5 min y sirve el mapa
```

Mapa: <http://127.0.0.1:8790> (otro puerto: `PUERTO=8791 scripts/monitor.sh`).

Tests: `.venv/bin/pytest --cov --cov-report=term-missing`

## Fuentes que consulta hoy

| Fuente | Dato | Archivo |
|---|---|---|
| SMN (CAP) | Alertas oficiales con polígono → se cruzan con las cuencas | `alertas/fuentes/smn_cap.py` |
| Hidrografía Naval | Altura del Río de la Plata (San Fernando, Buenos Aires, La Plata) y **sudestada** (medido − marea astronómica) | `alertas/fuentes/shn.py` |
| SNIH | A° Medrano en Reservorio Tecnópolis (reservorio: solo reacciona a tormentas grandes) | `alertas/fuentes/snih.py` |
| METAR (NOAA AWC) | Lluvia débil/moderada/fuerte y tormenta en 6 aeropuertos; se asigna a las cuencas a ≤10 km | `alertas/fuentes/metar.py` |
| INA a5 | Pronóstico probabilístico San Fernando (+48 h) | `alertas/fuentes/ina.py` |

Detalle de todas las fuentes evaluadas: [docs/fuentes/README.md](docs/fuentes/README.md).

## Cómo se agrega algo

- **Una estación** de un tipo que ya existe (SHN, SNIH, METAR): una línea en `alertas/estaciones.py`.
- **Una fuente nueva:** un módulo en `alertas/fuentes/` con `parse` (pura, probada con un archivo de ejemplo) y `obtener`, registrado en `alertas/fuentes/registro.py`. El CLI no se toca.
- **Un campo en el mapa:** respetar el contrato [docs/contrato-estado.md](docs/contrato-estado.md).



## Pendientes conocidos (antes de la Fase 1)

- **Datum:** confirmar con SHN la conversión entre el plano de reducción (lecturas) y el cero del Riachuelo (umbrales). Hasta entonces el mapa muestra alturas **sin clasificarlas** contra umbrales.
- **Zona horaria de SNIH:** validar con un evento conocido.
- **Costa/Delta** es una geometría provisoria (incluye Sarandí y La Plata).
- Falta lluvia medida en tiempo real (pedir acceso a la red de la Ciudad / SMN).

## Protección de memoria

`scripts/monitor.sh` corre cada consulta con tope de 512 MB. Para procesos pesados usar
`/home/rove/proyectos/AdrianSaenz/scripts/heavy.sh -- <comando>`.
