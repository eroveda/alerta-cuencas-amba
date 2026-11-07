import json
from datetime import datetime, timezone

from shapely.geometry import box, mapping

from alertas import cli
from alertas.db import Base
from alertas.fuentes import ina, metar, shn, smn_cap, snih


def _zonas_fc():
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"id": "medrano", "nombre": "Arroyo Medrano", "piloto": True},
         "geometry": mapping(box(-58.56, -34.61, -58.44, -34.53))},
    ]}


def test_poll_junta_fuentes_y_aisla_errores(tmp_path, fixture_text, monkeypatch):
    ahora = datetime(2026, 11, 3, 20, 0, tzinfo=timezone.utc)

    def snih_roto(estacion):
        raise TimeoutError("SNIH no responde")

    monkeypatch.setattr(shn, "obtener", lambda cod, _: shn.parse(fixture_text("shn_api_SFER.json"), cod))
    monkeypatch.setattr(snih, "obtener", snih_roto)
    monkeypatch.setattr(ina, "obtener", lambda: ina.parse_pronostico(fixture_text("ina_prono_sfer_432.json")))
    monkeypatch.setattr(metar, "obtener", lambda: [])
    monkeypatch.setattr(smn_cap, "obtener_links", lambda: ["https://ssl.smn.gob.ar/feeds/CAP/x.xml"])
    monkeypatch.setattr(smn_cap, "obtener_cap", lambda link: fixture_text("cap_amba_sintetico.xml"))

    zonas_path = tmp_path / "zonas.geojson"
    zonas_path.write_text(json.dumps(_zonas_fc()))
    salida = tmp_path / "estado.json"
    db = Base(tmp_path / "x.sqlite")

    cli.poll(db, zonas_path, salida, ahora)

    estado = json.loads(salida.read_text())
    assert estado["fuentes"]["snih:14011"]["ok"] is False
    assert "SNIH no responde" in estado["fuentes"]["snih:14011"]["error"]
    assert estado["fuentes"]["shn:SFER"]["ok"] is True
    assert estado["fuentes"]["smn_cap"]["ok"] is True
    assert estado["zonas"]["medrano"]["nivel_smn"] == "naranja"
    assert estado["pronostico_san_fernando"]["max_main"] > 0
    # el CAP ya visto no se vuelve a descargar
    assert db.links_cap_nuevos(["https://ssl.smn.gob.ar/feeds/CAP/x.xml"]) == []


def test_poll_cap_malformado_no_rompe(tmp_path, fixture_text, monkeypatch):
    ahora = datetime(2026, 11, 3, 20, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(shn, "obtener", lambda cod, _: [])
    monkeypatch.setattr(snih, "obtener", lambda e: [])
    monkeypatch.setattr(ina, "obtener", lambda: [])
    monkeypatch.setattr(metar, "obtener", lambda: [])
    monkeypatch.setattr(smn_cap, "obtener_links", lambda: ["https://ssl.smn.gob.ar/feeds/CAP/malo.xml"])
    monkeypatch.setattr(smn_cap, "obtener_cap", lambda link: "<no-es-cap")
    zonas_path = tmp_path / "zonas.geojson"
    zonas_path.write_text(json.dumps(_zonas_fc()))
    salida = tmp_path / "estado.json"

    cli.poll(Base(tmp_path / "x.sqlite"), zonas_path, salida, ahora)

    estado = json.loads(salida.read_text())
    assert estado["zonas"]["medrano"]["nivel_smn"] == "verde"
    assert estado["fuentes"]["smn_cap"]["caps_invalidos"] == 1
