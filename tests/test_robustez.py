"""Regresiones de la revisión de código: datos externos raros no deben tumbar el poll."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from alertas import cli, http
from alertas.db import Base
from alertas.fuentes import ina, metar, shn, smn_cap, snih
from alertas.modelos import Lectura
from alertas.tiempo import a_utc, local_a_utc

AHORA = datetime(2026, 11, 3, 20, 0, tzinfo=timezone.utc)


def test_local_a_utc_respeta_zona_si_viene():
    assert local_a_utc("2026-11-03T22:45:00Z") == datetime(2026, 11, 3, 22, 45, tzinfo=timezone.utc)


def test_a_utc_asume_art_si_es_naive():
    assert a_utc(datetime(2026, 11, 3, 12, 0)) == datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)


def test_shn_descarta_nan_y_valores_absurdos():
    texto = json.dumps({"astronomica": [], "lecturas": [
        {"fecha": "2026-11-03T10:45:00", "altura": None},
        {"fecha": "2026-11-03T11:45:00", "altura": 999.0},
        {"fecha": "2026-11-03T12:45:00", "altura": 1.2},
    ]}).replace("null", "NaN")
    lecturas = shn.parse(texto, "SFER")
    assert [l.valor for l in lecturas if l.variable == "altura"] == [1.2]


def test_snih_descarta_nan():
    texto = '{"d": {"RespuestaOK": true, "Mediciones": [{"Codigo": 1, "FechaHora": "/Date(1793756700000)/", "Valor": NaN}]}}'
    assert snih.parse_actuales(texto, "14011") == []


def test_ina_fechas_sin_zona_se_normalizan(fixture_text):
    texto = '{"series": [{"pronosticos": [{"timestart": "2026-11-04T12:00:00", "valor": 1.5, "qualifier": "main"}]}]}'
    (p,) = ina.parse_pronostico(texto)
    assert p.ts.tzinfo is not None
    assert ina.resumen([p], AHORA, horas=48)["max_main"] == 1.5


def test_cap_con_fechas_sin_zona_queda_en_utc(fixture_text):
    xml = fixture_text("cap_amba_sintetico.xml").replace("2026-11-03T20:59:59-03:00", "2026-11-03T20:59:59")
    a = smn_cap.parse_cap(xml)
    assert a.expires == datetime(2026, 11, 3, 23, 59, 59, tzinfo=timezone.utc)
    assert a.sent.utcoffset() == timedelta(0)


def test_cap_con_demasiados_puntos_se_rechaza(fixture_text):
    puntos = " ".join(f"-34.{i:04d},-58.5" for i in range(smn_cap.MAX_PUNTOS + 10))
    xml = fixture_text("cap_amba_sintetico.xml").replace(
        "-34.40,-58.60 -34.40,-58.30 -34.70,-58.30 -34.70,-58.60 -34.40,-58.60", puntos)
    with pytest.raises(ValueError):
        smn_cap.parse_cap(xml)


def test_cap_con_poligono_basura_se_rechaza(fixture_text):
    xml = fixture_text("cap_amba_sintetico.xml").replace("-34.40,-58.60 -34.40", "hola,mundo -34.40")
    with pytest.raises(ValueError):
        smn_cap.parse_cap(xml)


def test_vigentes_deduplica_por_identifier(fixture_text):
    a = smn_cap.parse_cap(fixture_text("cap_amba_sintetico.xml"))
    assert len(smn_cap.vigentes([a, a], AHORA)) == 1


def test_http_rechaza_hosts_fuera_de_la_lista():
    with pytest.raises(ValueError):
        http.pedir("https://evil.example.com/x")
    with pytest.raises(ValueError):
        http.pedir("http://ssl.smn.gob.ar/x")


def test_http_redirect_a_host_ajeno_se_bloquea():
    handler = http._RedirectSeguro()
    with pytest.raises(ValueError):
        handler.redirect_request(None, None, 302, "Found", {}, "https://evil.example.com/")


def test_db_poda_caps_y_lecturas_viejas(tmp_path):
    db = Base(tmp_path / "x.sqlite")
    db.guardar_cap("viejo", "<a/>", AHORA - timedelta(days=10))
    db.guardar_cap("vigente", "<b/>", AHORA + timedelta(hours=1))
    db.guardar_lecturas([Lectura("shn", "SFER", "altura", AHORA - timedelta(days=40), 1.0),
                         Lectura("shn", "SFER", "altura", AHORA, 1.1)])
    db.podar(AHORA)
    assert db.links_cap_nuevos(["viejo", "vigente"]) == ["viejo"]
    assert db.caps_vigentes(AHORA) == ["<b/>"]
    assert [l.valor for l in db.lecturas_desde(AHORA - timedelta(days=60))] == [1.1]


def _preparar(tmp_path, monkeypatch, fixture_text, shn_fn, cap_xml):
    monkeypatch.setattr(shn, "obtener", shn_fn)
    monkeypatch.setattr(snih, "obtener", lambda e: [])
    monkeypatch.setattr(ina, "obtener", lambda: [])
    monkeypatch.setattr(metar, "obtener", lambda: [])
    monkeypatch.setattr(smn_cap, "obtener_links", lambda: ["https://ssl.smn.gob.ar/feeds/CAP/a.xml"])
    monkeypatch.setattr(smn_cap, "obtener_cap", lambda link: cap_xml)
    zonas = tmp_path / "zonas.geojson"
    zonas.write_text(json.dumps({"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"id": "medrano", "nombre": "Medrano", "piloto": True},
        "geometry": {"type": "Polygon", "coordinates": [[[-58.56, -34.61], [-58.44, -34.61], [-58.44, -34.53], [-58.56, -34.61]]]}}]}))
    return zonas, tmp_path / "estado.json"


def test_falla_de_una_estacion_no_borra_las_otras(tmp_path, monkeypatch, fixture_text):
    def shn_fn(cod, _):
        if cod == "SFER":
            raise TimeoutError("SFER caído")
        return shn.parse(fixture_text("shn_api_SFER.json"), cod)

    zonas, salida = _preparar(tmp_path, monkeypatch, fixture_text, shn_fn, fixture_text("cap_amba_sintetico.xml"))
    estado = cli.poll(Base(tmp_path / "x.sqlite"), zonas, salida, AHORA)
    assert estado["fuentes"]["shn:SFER"]["ok"] is False
    assert estado["fuentes"]["shn:BSAS"]["ok"] is True


def test_cap_que_rompe_shapely_no_tumba_el_poll(tmp_path, monkeypatch, fixture_text):
    xml = fixture_text("cap_amba_sintetico.xml").replace(
        "-34.40,-58.60 -34.40,-58.30 -34.70,-58.30 -34.70,-58.60 -34.40,-58.60", "-34.40,-58.60 -34.70,-58.30")
    zonas, salida = _preparar(tmp_path, monkeypatch, fixture_text, lambda c, _: [], xml)
    estado = cli.poll(Base(tmp_path / "x.sqlite"), zonas, salida, AHORA)
    assert estado["fuentes"]["smn_cap"]["caps_invalidos"] == 1
    json.loads(salida.read_text())  # JSON válido
