from datetime import datetime, timezone

import pytest

from alertas.fuentes import smn_cap


def test_rss_devuelve_links_a_cap(fixture_text):
    links = smn_cap.parse_rss(fixture_text("cap_AR_rss.xml"))
    assert len(links) > 50
    assert all(l.startswith("https://ssl.smn.gob.ar/") and l.endswith(".xml") for l in links)


def test_parsea_cap(fixture_text):
    a = smn_cap.parse_cap(fixture_text("cap_lejos.xml"))
    assert a.identifier == "urn:oid:2.49.0.1.32.0.2026.11.03.13.08.46.10"
    assert a.severity == "Moderate"
    assert a.nivel == "amarillo"
    assert a.event == "Tormentas"
    assert a.expires == datetime(2026, 11, 3, 23, 59, 59, tzinfo=timezone.utc)
    assert a.references == ["urn:oid:2.49.0.1.32.0.2026.11.03.09.18.34"]
    assert "20 y 40 mm" in a.description
    assert len(a.poligonos) == 1
    # el CAP usa lat,lon: el polígono debe quedar en (lon, lat)
    minx, miny, *_ = a.poligonos[0].bounds
    assert -59 < minx < -57 and -31 < miny < -29


@pytest.mark.parametrize("sev,nivel", [("Minor", "amarillo"), ("Moderate", "amarillo"), ("Severe", "naranja"), ("Extreme", "rojo"), ("Unknown", "amarillo")])
def test_nivel_por_severidad(sev, nivel):
    assert smn_cap.nivel_por_severidad(sev) == nivel


def test_rechaza_xml_con_entidades():
    with pytest.raises(ValueError):
        smn_cap.parse_cap('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><alert/>')


def test_vigentes_filtra_vencidas_y_reemplazadas(fixture_text):
    nueva = smn_cap.parse_cap(fixture_text("cap_amba_sintetico.xml"))
    vieja = smn_cap.parse_cap(
        fixture_text("cap_amba_sintetico.xml").replace("TEST.AMBA.1", "TEST.AMBA.0", 1)
    )
    durante = datetime(2026, 11, 3, 20, 0, tzinfo=timezone.utc)
    despues = datetime(2026, 11, 4, 1, 0, tzinfo=timezone.utc)
    assert [a.identifier for a in smn_cap.vigentes([vieja, nueva], durante)] == [nueva.identifier]
    assert smn_cap.vigentes([vieja, nueva], despues) == []
