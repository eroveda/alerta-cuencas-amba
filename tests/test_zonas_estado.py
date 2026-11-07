from datetime import datetime, timedelta, timezone

from shapely.geometry import Polygon, box, mapping

from alertas.estado import armar_estado
from alertas.fuentes import smn_cap
from alertas.modelos import Lectura
from alertas.zonas import Zonas, construir_zonas


def _fc(features):
    return {"type": "FeatureCollection", "features": features}


def _feat(props, geom):
    return {"type": "Feature", "properties": props, "geometry": mapping(geom)}


COHIFE = _fc([
    _feat({"CUENCA": "Arroyo Medrano"}, box(-58.56, -34.61, -58.44, -34.53)),
    _feat({"CUENCA": "Arroyo Maldonado"}, box(-58.59, -34.69, -58.40, -34.55)),
    _feat({"CUENCA": "Río Luján"}, box(-59.9, -34.8, -58.8, -34.2)),
    _feat({"CUENCA": "Río Matanza-Riachuelo"}, box(-59.0, -35.1, -58.35, -34.62)),
    _feat({"CUENCA": "Río Reconquista"}, box(-59.3, -34.9, -58.5, -34.42)),
    _feat({"CUENCA": "Delta del río Paraná"}, box(-60.7, -34.45, -58.35, -32.1)),
    _feat({"CUENCA": "Afluentes al río de la Plata en Buenos Aires"}, box(-58.58, -35.7, -57.1, -34.41)),
])
CABA = _fc([
    _feat({"nombre": n}, box(-58.5 + i * 0.01, -34.6, -58.49 + i * 0.01, -34.59))
    for i, n in enumerate(["Cuenca Vega", "Cuenca White", "Cuenca Cildañez"])
])


def test_construir_zonas_arma_piloto_y_monitoreo():
    fc = construir_zonas(COHIFE, CABA)
    props = {f["properties"]["id"]: f["properties"] for f in fc["features"]}
    assert {"medrano", "costa-delta", "maldonado", "vega", "lujan"} <= set(props)
    assert props["medrano"]["piloto"] and props["costa-delta"]["piloto"]
    assert not props["lujan"]["piloto"]
    # costa-delta se recorta al AMBA: no incluye el delta entrerriano
    costa = next(f for f in fc["features"] if f["properties"]["id"] == "costa-delta")
    assert Zonas(_fc([costa])).afectadas([box(-60.5, -33.0, -60.0, -32.5)]) == []


def test_construir_zonas_tolera_cuenca_faltante():
    fc = construir_zonas(_fc(COHIFE["features"][:1]), _fc([]))
    assert [f["properties"]["id"] for f in fc["features"]] == ["medrano"]


def test_zonas_afectadas_por_poligono():
    zonas = Zonas(construir_zonas(COHIFE, CABA))
    afectadas = zonas.afectadas([Polygon([(-58.55, -34.6), (-58.5, -34.6), (-58.5, -34.55)])])
    assert "medrano" in afectadas
    assert "lujan" not in afectadas


def test_estado_marca_zonas_con_alerta_y_datos_viejos(fixture_text):
    zonas = Zonas(construir_zonas(COHIFE, CABA))
    alerta = smn_cap.parse_cap(fixture_text("cap_amba_sintetico.xml"))
    ahora = datetime(2026, 11, 3, 20, 0, tzinfo=timezone.utc)
    lecturas = [
        Lectura("shn", "SFER", "altura", ahora - timedelta(minutes=30), 1.2),
        Lectura("shn", "SFER", "residuo", ahora - timedelta(minutes=30), 0.4),
        Lectura("snih", "14011", "altura", ahora - timedelta(hours=5), 0.03),
    ]
    estado = armar_estado(zonas, [alerta], lecturas, None, {"shn": {"ok": True}}, ahora)

    assert estado["fase"].startswith("0")
    assert estado["zonas"]["medrano"]["nivel_smn"] == "naranja"
    assert estado["zonas"]["lujan"]["nivel_smn"] == "verde"
    est = {e["id"]: e for e in estado["estaciones"]}
    assert est["shn:SFER"]["altura"] == 1.2
    assert est["shn:SFER"]["residuo"] == 0.4
    assert est["shn:SFER"]["viejo"] is False
    assert est["snih:14011"]["viejo"] is True
    assert est["shn:BSAS"]["altura"] is None  # estación conocida sin datos


def test_estado_incluye_lluvia_de_aeropuertos_por_zona():
    from alertas.fuentes import metar
    zonas = Zonas(construir_zonas(COHIFE, CABA))
    ahora = datetime(2026, 11, 3, 23, 10, tzinfo=timezone.utc)
    t = datetime(2026, 11, 3, 23, 0, tzinfo=timezone.utc)
    lecturas = [
        Lectura("metar", "SABE", "lluvia", t, metar.NIVEL_LLUVIA["fuerte"]),
        Lectura("metar", "SABE", "tormenta", t, metar.NIVEL_TORMENTA["cercana"]),
        Lectura("metar", "SADF", "lluvia", t - timedelta(hours=5), metar.NIVEL_LLUVIA["fuerte"]),  # viejo
    ]
    estado = armar_estado(zonas, [], lecturas, None, {}, ahora)

    est = {e["id"]: e for e in estado["estaciones"]}
    assert est["metar:SABE"]["tipo"] == "meteo"
    assert est["metar:SABE"]["lluvia"] == "fuerte"
    assert est["metar:SABE"]["tormenta"] == "cercana"
    assert est["metar:SADF"]["viejo"] is True
    assert estado["zonas"]["medrano"]["lluvia_obs"] == "fuerte"
    assert estado["zonas"]["medrano"]["tormenta_obs"] == "cercana"
    # Luján queda a más de 10 km de cualquier aeropuerto con dato
    assert estado["zonas"]["lujan"]["lluvia_obs"] is None


def test_lluvia_vieja_no_cuenta_para_la_zona():
    from alertas.fuentes import metar
    zonas = Zonas(construir_zonas(COHIFE, CABA))
    ahora = datetime(2026, 11, 3, 23, 10, tzinfo=timezone.utc)
    viejo = Lectura("metar", "SABE", "lluvia", ahora - timedelta(hours=5), metar.NIVEL_LLUVIA["fuerte"])
    estado = armar_estado(zonas, [], [viejo], None, {}, ahora)
    assert estado["zonas"]["medrano"]["lluvia_obs"] is None


def test_estado_declara_version_y_cumple_el_contrato():
    from alertas.estado import CLAVES_ESTADO, VERSION_ESQUEMA
    ahora = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    zonas = Zonas(construir_zonas(COHIFE, CABA))
    estado = armar_estado(zonas, [], [], None, {}, ahora)
    assert estado["version"] == VERSION_ESQUEMA == 1
    assert set(estado) == CLAVES_ESTADO
    for z in estado["zonas"].values():
        assert set(z) == {"nombre", "piloto", "nivel_smn", "alertas", "lluvia_obs", "tormenta_obs"}
