"""Arma el estado.json que consume el mapa. Fase 0: solo monitoreo, sin avisos."""

from datetime import datetime, timedelta

from alertas.estaciones import ESTACIONES
from alertas.fuentes import metar
from alertas.fuentes.smn_cap import AlertaCap
from alertas.modelos import Estacion, Lectura
from alertas.zonas import Zonas

ORDEN_NIVEL = {"verde": 0, "amarillo": 1, "naranja": 2, "rojo": 3}
RADIO_AEROPUERTO_GRADOS = 0.1  # ~10 km: un METAR representa la lluvia alrededor

# Contrato con web/app.js (ver docs/contrato-estado.md). Subir la versión ante
# cualquier cambio incompatible: quitar o renombrar claves, cambiar tipos o valores.
VERSION_ESQUEMA = 1
CLAVES_ESTADO = frozenset({"version", "generado", "fase", "aviso_legal", "zonas", "estaciones",
                           "pronostico_san_fernando", "fuentes"})


def _ultima(lecturas: list[Lectura], e: Estacion, variable: str, ahora: datetime) -> Lectura | None:
    candidatas = [l for l in lecturas if (l.fuente, l.estacion, l.variable) == (e.fuente, e.codigo, variable)
                  and l.ts <= ahora]
    return max(candidatas, key=lambda l: l.ts, default=None)


def _es_vieja(lectura: Lectura | None, e: Estacion, ahora: datetime) -> bool:
    return lectura is None or ahora - lectura.ts > timedelta(minutes=e.max_atraso_min)


def _estacion(e: Estacion, lecturas: list[Lectura], ahora: datetime) -> dict:
    base = {"id": e.id, "nombre": e.nombre, "lat": e.lat, "lon": e.lon, "zona": e.zona, "tipo": e.tipo}
    if e.tipo == "meteo":
        lluvia = _ultima(lecturas, e, "lluvia", ahora)
        tormenta = _ultima(lecturas, e, "tormenta", ahora)
        return {**base,
                "lluvia": metar.etiqueta_lluvia(lluvia.valor if lluvia else None),
                "tormenta": metar.etiqueta_tormenta(tormenta.valor if tormenta else None),
                "ts": lluvia.ts.isoformat() if lluvia else None,
                "viejo": _es_vieja(lluvia, e, ahora)}
    altura = _ultima(lecturas, e, "altura", ahora)
    residuo = _ultima(lecturas, e, "residuo", ahora)
    return {**base,
            "altura": altura.valor if altura else None,
            "residuo": residuo.valor if residuo else None,
            "ts": altura.ts.isoformat() if altura else None,
            "viejo": _es_vieja(altura, e, ahora)}


def _zonas_base(zonas: Zonas) -> dict[str, dict]:
    return {zid: {"nombre": zonas.props[zid]["nombre"], "piloto": zonas.props[zid]["piloto"],
                  "nivel_smn": "verde", "alertas": [], "lluvia_obs": None, "tormenta_obs": None}
            for zid in zonas.ids}


def _aplicar_alertas(salida: dict[str, dict], zonas: Zonas, alertas: list[AlertaCap]) -> None:
    for a in alertas:
        for zid in zonas.afectadas(a.poligonos):
            z = salida[zid]
            z["alertas"].append({"evento": a.event, "nivel": a.nivel, "expira": a.expires.isoformat(),
                                 "descripcion": a.description, "id": a.identifier})
            if ORDEN_NIVEL[a.nivel] > ORDEN_NIVEL[z["nivel_smn"]]:
                z["nivel_smn"] = a.nivel


def _maximo(actual: str | None, nuevo: str | None, orden: dict[str, int]) -> str | None:
    if nuevo is None:
        return actual
    return nuevo if actual is None or orden[nuevo] > orden[actual] else actual


def _aplicar_lluvia(salida: dict[str, dict], zonas: Zonas, estaciones: list[dict]) -> None:
    for s in estaciones:
        if s["tipo"] != "meteo" or s["viejo"]:
            continue
        for zid in zonas.cercanas(s["lon"], s["lat"], RADIO_AEROPUERTO_GRADOS):
            z = salida[zid]
            z["lluvia_obs"] = _maximo(z["lluvia_obs"], s["lluvia"], metar.NIVEL_LLUVIA)
            z["tormenta_obs"] = _maximo(z["tormenta_obs"], s["tormenta"], metar.NIVEL_TORMENTA)


def armar_estado(zonas: Zonas, alertas: list[AlertaCap], lecturas: list[Lectura],
                 pronostico_sfer: dict | None, fuentes: dict[str, dict], ahora: datetime) -> dict:
    estaciones = [_estacion(e, lecturas, ahora) for e in ESTACIONES]
    salida = _zonas_base(zonas)
    _aplicar_alertas(salida, zonas, alertas)
    _aplicar_lluvia(salida, zonas, estaciones)
    return {
        "version": VERSION_ESQUEMA,
        "generado": ahora.isoformat(),
        "fase": "0 – monitoreo (no se envían avisos)",
        "aviso_legal": "Sistema cívico NO oficial. Ante emergencias seguí a SMN, SHN y Defensa Civil.",
        "zonas": salida,
        "estaciones": estaciones,
        "pronostico_san_fernando": pronostico_sfer,
        "fuentes": fuentes,
    }
