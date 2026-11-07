"""METAR (NOAA Aviation Weather Center): fenómeno presente en aeropuertos del AMBA.

No da milímetros, pero distingue intensidad: '-' débil, sin signo moderada,
'+' fuerte; 'TS' tormenta en la estación, 'VCTS' tormenta en las cercanías.
"""

import json
import re
from datetime import datetime, timezone

from alertas.http import pedir
from alertas.modelos import Lectura

ESTACIONES_METAR = ("SABE", "SADF", "SADP", "SADM", "SAEZ", "SADL")
URL = "https://aviationweather.gov/api/data/metar?ids={ids}&hours={horas}&format=json"

NIVEL_LLUVIA = {"sin": 0, "debil": 1, "moderada": 2, "fuerte": 3}
NIVEL_TORMENTA = {"no": 0, "cercana": 1, "si": 2}
_PRECIP = re.compile(r"^(?P<int>[+-]?)(?P<desc>(?:SH|TS)?)(?P<fen>(?:RA|DZ|GR|GS|PL|SN|UP)+)$")


def clasificar(wx: str | None) -> tuple[str, str]:
    """Devuelve (intensidad de lluvia, tormenta) a partir del campo wxString."""
    lluvia, tormenta = "sin", "no"
    for token in (wx or "").split():
        if token.startswith("VC"):
            if "TS" in token:
                tormenta = max(tormenta, "cercana", key=NIVEL_TORMENTA.get)
            continue
        if token.lstrip("+-") == "TS":
            tormenta = "si"
            continue
        m = _PRECIP.match(token)
        if not m:
            continue  # BR, FG, HZ, etc.: no es precipitación
        if m["desc"] == "TS":
            tormenta = "si"
        intensidad = {"-": "debil", "+": "fuerte"}.get(m["int"], "moderada")
        if m["fen"] == "DZ" and intensidad == "moderada":
            intensidad = "debil"  # llovizna moderada sigue siendo poca agua
        lluvia = max(lluvia, intensidad, key=NIVEL_LLUVIA.get)
    return lluvia, tormenta


def etiqueta_lluvia(valor: float | None) -> str | None:
    return None if valor is None else {v: k for k, v in NIVEL_LLUVIA.items()}.get(int(valor))


def etiqueta_tormenta(valor: float | None) -> str | None:
    return None if valor is None else {v: k for k, v in NIVEL_TORMENTA.items()}.get(int(valor))


def parse(texto: str) -> list[Lectura]:
    lecturas: list[Lectura] = []
    for r in json.loads(texto):
        icao, obs = r.get("icaoId"), r.get("obsTime")
        if icao not in ESTACIONES_METAR or not isinstance(obs, int):
            continue
        ts = datetime.fromtimestamp(obs, tz=timezone.utc)
        lluvia, tormenta = clasificar(r.get("wxString"))
        lecturas.append(Lectura("metar", icao, "lluvia", ts, NIVEL_LLUVIA[lluvia]))
        lecturas.append(Lectura("metar", icao, "tormenta", ts, NIVEL_TORMENTA[tormenta]))
    return lecturas


def obtener(horas: int = 3) -> list[Lectura]:
    return parse(pedir(URL.format(ids=",".join(ESTACIONES_METAR), horas=horas)))
