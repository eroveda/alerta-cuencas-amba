"""SNIH (Sistema Nacional de Información Hídrica): endpoints internos ASP.NET.

La zona horaria de los datos NO está validada (ver docs/fuentes/hidrologia.md).
"""

import json

from alertas.http import pedir
from alertas.modelos import Lectura
from alertas.tiempo import ms_date_a_utc
from alertas.validacion import altura_valida

URL_ACTUALES = "https://snih.hidricosargentina.gob.ar/MuestraDatos.aspx/LeerDatosActuales"
CODIGO_ALTURA = 1


def parse_actuales(texto: str, estacion: str) -> list[Lectura]:
    d = json.loads(texto).get("d") or {}
    if not d.get("RespuestaOK", False):
        raise ValueError(f"SNIH {estacion}: {d.get('MsgErr') or 'respuesta no OK'}")
    return [
        Lectura("snih", estacion, "altura", ms_date_a_utc(m["FechaHora"]), v)
        for m in d.get("Mediciones") or []
        if m.get("Codigo") == CODIGO_ALTURA and (v := altura_valida(m.get("Valor"))) is not None
    ]


def obtener(estacion: str) -> list[Lectura]:
    if not estacion.isdigit():
        raise ValueError(f"código SNIH inválido: {estacion}")
    cuerpo = json.dumps({"estacion": estacion}).encode()
    texto = pedir(URL_ACTUALES, cuerpo, {"Content-Type": "application/json; charset=utf-8"})
    return parse_actuales(texto, estacion)
