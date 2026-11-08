from datetime import datetime, timedelta, timezone

from alertas.fuentes.ina import PuntoPronostico
from alertas.modelos import Lectura
from alertas.serie import VERSION_SERIE, armar_serie

AHORA = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)


def _l(var, horas, valor, est="SFER"):
    return Lectura("shn", est, var, AHORA + timedelta(hours=horas), valor)


def test_serie_agrupa_por_estacion_y_variable_en_orden():
    lecturas = [_l("altura", -1, 1.2), _l("altura", -2, 1.0), _l("residuo", -1, 0.4),
                _l("astronomica", 3, 0.9), Lectura("metar", "SABE", "lluvia", AHORA, 1.0)]
    serie = armar_serie(lecturas, [], AHORA)
    assert serie["version"] == VERSION_SERIE
    sfer = serie["estaciones"]["SFER"]
    assert sfer["altura"] == [[(AHORA - timedelta(hours=2)).isoformat(), 1.0],
                              [(AHORA - timedelta(hours=1)).isoformat(), 1.2]]
    assert sfer["astronomica"][0][1] == 0.9
    assert "SABE" not in serie["estaciones"]


def test_serie_recorta_ventana_pasada_y_futura():
    lecturas = [_l("altura", -100, 9.0), _l("altura", -10, 1.0), _l("astronomica", 60, 9.0)]
    sfer = armar_serie(lecturas, [], AHORA)["estaciones"]["SFER"]
    assert [v for _, v in sfer["altura"]] == [1.0]
    assert sfer["astronomica"] == []


def test_serie_incluye_pronostico_ina_solo_hacia_adelante():
    puntos = [PuntoPronostico(AHORA - timedelta(hours=5), 1.0, 0.8, 1.2),
              PuntoPronostico(AHORA + timedelta(hours=5), 2.0, 1.7, None)]
    prono = armar_serie([], puntos, AHORA)["pronostico_sfer"]
    assert prono == [[(AHORA + timedelta(hours=5)).isoformat(), 2.0, 1.7, None]]


def test_serie_vacia_no_rompe():
    serie = armar_serie([], [], AHORA)
    assert serie["estaciones"] == {}
    assert serie["pronostico_sfer"] == []
