"""Arma serie.json: últimas horas del Río de la Plata (SHN) y pronóstico INA de San Fernando.

Es lo que dibuja el gráfico de sudestada de la web. Función pura: recibe datos y la hora.
INA espeja la escala de SHN en San Fernando (ver docs/fuentes/hidrologia.md), por eso
se pueden superponer en el mismo gráfico.
"""

from datetime import datetime, timedelta

from alertas.fuentes.ina import PuntoPronostico
from alertas.modelos import Lectura

VERSION_SERIE = 1
HORAS_ATRAS = 72
HORAS_ADELANTE = 48
VARIABLES = ("altura", "astronomica", "residuo")


def armar_serie(lecturas: list[Lectura], puntos: list[PuntoPronostico], ahora: datetime) -> dict:
    desde = ahora - timedelta(hours=HORAS_ATRAS)
    hasta = ahora + timedelta(hours=HORAS_ADELANTE)
    estaciones: dict[str, dict[str, list]] = {}
    for l in sorted(lecturas, key=lambda l: l.ts):
        if l.fuente != "shn" or l.variable not in VARIABLES or not desde <= l.ts <= hasta:
            continue
        serie = estaciones.setdefault(l.estacion, {v: [] for v in VARIABLES})
        serie[l.variable].append([l.ts.isoformat(), round(l.valor, 3)])
    pronostico = [[p.ts.isoformat(), p.main, p.p05, p.p95] for p in puntos if ahora <= p.ts <= hasta]
    return {"version": VERSION_SERIE, "generado": ahora.isoformat(),
            "estaciones": estaciones, "pronostico_sfer": pronostico}
