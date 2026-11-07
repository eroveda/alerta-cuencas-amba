"""Validación de valores numéricos que vienen de fuentes externas."""

import math

# Alturas plausibles (m) en escalas del AMBA. Fuera de esto es un error del sensor o del feed.
ALTURA_MIN_M = -5.0
ALTURA_MAX_M = 15.0


def altura_valida(valor: object) -> float | None:
    try:
        v = float(valor)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v) or not ALTURA_MIN_M <= v <= ALTURA_MAX_M:
        return None
    return v
