"""Normalización de fechas: todo se guarda en UTC."""

import re
from datetime import datetime, timedelta, timezone

# Argentina no tiene horario de verano: UTC-3 fijo.
ART = timezone(timedelta(hours=-3), "ART")

_MS_DATE = re.compile(r"/Date\((-?\d+)\)/")


def a_utc(dt: datetime, asumir: timezone = ART) -> datetime:
    """Pasa a UTC; si la fecha no trae zona, asume `asumir` (hora argentina por defecto)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=asumir)
    return dt.astimezone(timezone.utc)


def local_a_utc(fecha: str) -> datetime:
    """Fecha ISO; si no trae zona se interpreta como hora argentina."""
    return a_utc(datetime.fromisoformat(fecha))


def ms_date_a_utc(valor: str) -> datetime:
    """Convierte el formato ASP.NET '/Date(ms)/' a UTC."""
    m = _MS_DATE.search(valor)
    if not m:
        raise ValueError(f"fecha ASP.NET inválida: {valor!r}")
    return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc)


def iso_utc(dt: datetime) -> str:
    """Formato único para guardar y comparar: 2026-11-04T01:45:00Z."""
    return a_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)
