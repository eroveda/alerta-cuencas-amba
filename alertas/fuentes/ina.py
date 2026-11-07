"""INA a5: pronóstico probabilístico de altura en San Fernando (modelo 432)."""

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from alertas.http import pedir
from alertas.tiempo import a_utc
from alertas.validacion import altura_valida

URL_PRONO_SFER = (
    "https://alerta.ina.gob.ar/a5/sim/calibrados/432/corridas/last"
    "?series_id=26202&includeProno=true&format=json"
)


@dataclass(frozen=True)
class PuntoPronostico:
    ts: datetime
    main: float
    p05: float | None
    p95: float | None


def _ts(valor: str) -> datetime:
    # INA publica en UTC; si falta la zona, asumimos UTC.
    return a_utc(datetime.fromisoformat(valor.replace("Z", "+00:00")), asumir=timezone.utc)


def parse_pronostico(texto: str) -> list[PuntoPronostico]:
    datos = json.loads(texto)
    por_ts: dict[datetime, dict[str, float]] = defaultdict(dict)
    for serie in datos.get("series") or []:
        for p in serie.get("pronosticos") or []:
            v = altura_valida(p.get("valor"))
            if v is not None:
                por_ts[_ts(p["timestart"])][p.get("qualifier", "main")] = v
    return [
        PuntoPronostico(ts, q["main"], q.get("p05"), q.get("p95"))
        for ts, q in sorted(por_ts.items())
        if "main" in q
    ]


def resumen(puntos: list[PuntoPronostico], desde: datetime, horas: int = 48) -> dict | None:
    hasta = desde + timedelta(hours=horas)
    ventana = [p for p in puntos if desde <= p.ts <= hasta]
    if not ventana:
        return None
    pico = max(ventana, key=lambda p: p.main)
    p95s = [p.p95 for p in ventana if p.p95 is not None]
    return {
        "max_main": pico.main,
        "ts_max": pico.ts.isoformat(),
        "max_p95": max(p95s) if p95s else None,
        "horas": horas,
    }


def obtener() -> list[PuntoPronostico]:
    return parse_pronostico(pedir(URL_PRONO_SFER))
