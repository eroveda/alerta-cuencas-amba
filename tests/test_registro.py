from datetime import datetime, timezone

import pytest

from alertas.fuentes import metar, registro, shn, snih
from alertas.modelos import Estacion, Lectura

AHORA = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


def test_registro_arma_una_fuente_por_estacion_hidro_y_una_para_metar():
    nombres = [f.nombre for f in registro.fuentes_de_lecturas()]
    assert nombres == ["shn:SFER", "shn:BSAS", "shn:LPLA", "snih:14011", "metar"]


def test_cada_fuente_delega_en_su_modulo(monkeypatch):
    llamadas = []
    monkeypatch.setattr(shn, "obtener", lambda cod, ahora: llamadas.append(("shn", cod, ahora)) or [])
    monkeypatch.setattr(snih, "obtener", lambda cod: llamadas.append(("snih", cod)) or [])
    lectura = Lectura("metar", "SABE", "lluvia", AHORA, 2.0)
    monkeypatch.setattr(metar, "obtener", lambda: [lectura])

    resultados = {f.nombre: f.obtener(AHORA) for f in registro.fuentes_de_lecturas()}

    assert ("shn", "BSAS", AHORA) in llamadas
    assert ("snih", "14011") in llamadas
    assert resultados["metar"] == [lectura]


def test_estacion_de_fuente_desconocida_falla_al_armar_el_registro():
    rara = Estacion("pluvio", "X1", "Pluviómetro", -34.5, -58.5, "medrano", 60)
    with pytest.raises(ValueError, match="pluvio"):
        registro.fuentes_de_lecturas((rara,))


def test_fuente_agrupada_aparece_una_sola_vez():
    ests = tuple(Estacion("metar", c, c, -34.5, -58.5, "", 90, "meteo") for c in ("SABE", "SADF"))
    assert [f.nombre for f in registro.fuentes_de_lecturas(ests)] == ["metar"]
