from datetime import datetime, timezone

import pytest

from alertas.fuentes import metar


@pytest.mark.parametrize("wx,lluvia,tormenta", [
    (None, "sin", "no"),
    ("", "sin", "no"),
    ("BR", "sin", "no"),
    ("MIFG BR", "sin", "no"),
    ("-DZ", "debil", "no"),
    ("-DZ BR", "debil", "no"),
    ("-RA", "debil", "no"),
    ("RA BR", "moderada", "no"),
    ("SHRA", "moderada", "no"),
    ("+RA", "fuerte", "no"),
    ("+SHRA", "fuerte", "no"),
    ("-TSRA", "debil", "si"),
    ("+TSRA", "fuerte", "si"),
    ("TS", "sin", "si"),
    ("VCTS", "sin", "cercana"),
    ("VCSH", "sin", "no"),
    ("-RA VCTS", "debil", "cercana"),
])
def test_clasificar(wx, lluvia, tormenta):
    assert metar.clasificar(wx) == (lluvia, tormenta)


def test_parse_reportes_de_ayer(fixture_text):
    lecturas = metar.parse(fixture_text("metar_3nov.json"))
    assert {l.estacion for l in lecturas} == {"SABE", "SADF", "SADP", "SADM", "SAEZ", "SADL"}
    assert {l.variable for l in lecturas} == {"lluvia", "tormenta"}
    # Morón, 3/11 20:00 ART (23:00Z): -TSRA
    moron = {l.variable: l.valor for l in lecturas
             if l.estacion == "SADM" and l.ts == datetime(2026, 11, 3, 23, 0, tzinfo=timezone.utc)}
    assert moron == {"lluvia": metar.NIVEL_LLUVIA["debil"], "tormenta": metar.NIVEL_TORMENTA["si"]}


def test_parse_ignora_estaciones_ajenas_y_registros_rotos():
    texto = '[{"icaoId": "KJFK", "obsTime": 1793840400, "wxString": "+RA"}, {"icaoId": "SABE"}]'
    assert metar.parse(texto) == []


def test_etiquetas_inversas():
    assert metar.etiqueta_lluvia(metar.NIVEL_LLUVIA["fuerte"]) == "fuerte"
    assert metar.etiqueta_tormenta(metar.NIVEL_TORMENTA["cercana"]) == "cercana"
    assert metar.etiqueta_lluvia(None) is None
