"""Servicio de Hidrografía Naval: alturas horarias del Río de la Plata.

API no documentada que usa la propia web del SHN. Las fechas vienen en hora
local sin zona. El residuo (observado - astronómico) es el indicador de sudestada.
Ojo: las alturas están en el plano de reducción del RdP; los umbrales oficiales
del SHN están en el cero del Riachuelo (conversión NO confirmada todavía).
"""

import json
from datetime import datetime

from alertas.http import pedir
from alertas.modelos import Lectura
from alertas.tiempo import ART, local_a_utc
from alertas.validacion import altura_valida

BASE = "https://www.hidro.gob.ar/api/v1/AlturasHorarias"
CODIGOS = {"SFER", "BSAS", "LPLA", "MAGA", "PNOR", "ATAL", "OYAR"}


def url(codigo: str, ahora: datetime) -> str:
    if codigo not in CODIGOS:
        raise ValueError(f"estación SHN desconocida: {codigo}")
    return f"{BASE}/{codigo}/{ahora.astimezone(ART):%Y%m%d%H%M}"


def parse(texto: str, codigo: str) -> list[Lectura]:
    datos = json.loads(texto)
    astro = {
        local_a_utc(p["fecha"]): v
        for p in datos.get("astronomica") or []
        if (v := altura_valida(p.get("altura"))) is not None
    }
    lecturas: list[Lectura] = []
    for p in datos.get("lecturas") or []:
        altura = altura_valida(p.get("altura"))
        if altura is None:
            continue
        ts = local_a_utc(p["fecha"])
        lecturas.append(Lectura("shn", codigo, "altura", ts, altura))
        if ts in astro:
            lecturas.append(Lectura("shn", codigo, "residuo", ts, round(altura - astro[ts], 4)))
    lecturas.extend(Lectura("shn", codigo, "astronomica", ts, v) for ts, v in astro.items())
    return lecturas


def obtener(codigo: str, ahora: datetime) -> list[Lectura]:
    return parse(pedir(url(codigo, ahora)), codigo)
