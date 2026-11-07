"""Registro de fuentes de lecturas.

Cada fuente cumple el protocolo `Fuente`: un nombre (el que aparece en
estado.json → fuentes) y `obtener(ahora) -> list[Lectura]`. El registro se arma
a partir de ESTACIONES, así que agregar una estación de un tipo conocido no
requiere tocar el CLI. Un tipo nuevo se suma en POR_ESTACION o AGRUPADAS.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from alertas.estaciones import ESTACIONES
from alertas.fuentes import metar, shn, snih
from alertas.modelos import Estacion, Lectura

Obtener = Callable[[datetime], list[Lectura]]


class Fuente(Protocol):
    nombre: str

    def obtener(self, ahora: datetime) -> list[Lectura]: ...


@dataclass(frozen=True)
class FuenteSimple:
    nombre: str
    _obtener: Obtener

    def obtener(self, ahora: datetime) -> list[Lectura]:
        return self._obtener(ahora)


# Las lambdas resuelven `modulo.obtener` en cada llamada (no al importar),
# así los tests pueden reemplazarlo con monkeypatch.
POR_ESTACION: dict[str, Callable[[Estacion], Obtener]] = {
    "shn": lambda e: lambda ahora: shn.obtener(e.codigo, ahora),
    "snih": lambda e: lambda ahora: snih.obtener(e.codigo),
}
# Fuentes que traen todas sus estaciones en un solo pedido.
AGRUPADAS: dict[str, Obtener] = {
    "metar": lambda ahora: metar.obtener(),
}


def fuentes_de_lecturas(estaciones: Iterable[Estacion] = ESTACIONES) -> tuple[Fuente, ...]:
    fuentes: list[Fuente] = []
    agrupadas_vistas: set[str] = set()
    for e in estaciones:
        if e.fuente in POR_ESTACION:
            fuentes.append(FuenteSimple(e.id, POR_ESTACION[e.fuente](e)))
        elif e.fuente in AGRUPADAS:
            if e.fuente not in agrupadas_vistas:
                agrupadas_vistas.add(e.fuente)
                fuentes.append(FuenteSimple(e.fuente, AGRUPADAS[e.fuente]))
        else:
            raise ValueError(f"estación {e.id}: fuente '{e.fuente}' sin adaptador registrado")
    return tuple(fuentes)
