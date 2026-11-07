from datetime import datetime, timezone

import pytest

from alertas.fuentes import ina, shn, snih


class TestShn:
    def test_parsea_lecturas_y_calcula_residuo(self, fixture_text):
        lecturas = shn.parse(fixture_text("shn_api_SFER.json"), "SFER")
        alturas = [l for l in lecturas if l.variable == "altura"]
        residuos = [l for l in lecturas if l.variable == "residuo"]
        assert len(alturas) == 13
        assert len(residuos) == 13
        ultima = max(alturas, key=lambda l: l.ts)
        assert ultima.ts.tzinfo == timezone.utc
        r = next(r for r in residuos if r.ts == ultima.ts)
        astro = next(l for l in lecturas if l.variable == "astronomica" and l.ts == ultima.ts)
        assert r.valor == pytest.approx(ultima.valor - astro.valor, abs=1e-6)

    def test_incluye_marea_astronomica_futura(self, fixture_text):
        lecturas = shn.parse(fixture_text("shn_api_SFER.json"), "SFER")
        ultima_obs = max(l.ts for l in lecturas if l.variable == "altura")
        futuras = [l for l in lecturas if l.variable == "astronomica" and l.ts > ultima_obs]
        assert len(futuras) >= 6

    def test_url_usa_hora_local(self):
        ahora = datetime(2026, 11, 4, 1, 50, tzinfo=timezone.utc)
        assert shn.url("BSAS", ahora).endswith("/AlturasHorarias/BSAS/202611032250")

    def test_estacion_desconocida_falla(self):
        with pytest.raises(ValueError):
            shn.url("XXXX", datetime.now(timezone.utc))

    def test_lecturas_vacias_no_rompe(self):
        assert shn.parse('{"astronomica": [], "lecturas": []}', "SFER") == []


class TestSnih:
    def test_parsea_dato_actual_medrano(self, fixture_text):
        (lectura,) = snih.parse_actuales(fixture_text("snih_actuales_14011.json"), "14011")
        assert lectura.fuente == "snih"
        assert lectura.estacion == "14011"
        assert lectura.variable == "altura"
        assert lectura.valor == pytest.approx(0.03)
        assert lectura.ts == datetime(2026, 11, 4, 1, 45, tzinfo=timezone.utc)

    def test_respuesta_con_error_falla(self):
        with pytest.raises(ValueError):
            snih.parse_actuales('{"d": {"Mediciones": [], "RespuestaOK": false, "MsgErr": "x"}}', "14011")


class TestInaPronostico:
    def test_parsea_cuantiles(self, fixture_text):
        puntos = ina.parse_pronostico(fixture_text("ina_prono_sfer_432.json"))
        assert len(puntos) > 300
        assert all(p.p05 <= p.main <= p.p95 for p in puntos if p.p05 is not None and p.p95 is not None)
        assert puntos == sorted(puntos, key=lambda p: p.ts)

    def test_resumen_maximo_en_ventana(self, fixture_text):
        puntos = ina.parse_pronostico(fixture_text("ina_prono_sfer_432.json"))
        desde = datetime(2026, 11, 4, 2, 0, tzinfo=timezone.utc)
        resumen = ina.resumen(puntos, desde, horas=96)
        assert resumen["max_main"] == pytest.approx(2.49, abs=0.01)
        assert resumen["max_p95"] >= resumen["max_main"]
        assert desde <= datetime.fromisoformat(resumen["ts_max"]) <= datetime(2026, 11, 8, 2, tzinfo=timezone.utc)

    def test_resumen_sin_puntos_en_ventana(self):
        assert ina.resumen([], datetime.now(timezone.utc)) is None
