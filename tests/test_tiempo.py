from datetime import datetime, timezone

from alertas.tiempo import local_a_utc, ms_date_a_utc


def test_local_a_utc_suma_tres_horas():
    assert local_a_utc("2026-11-03T22:45:00") == datetime(2026, 11, 4, 1, 45, tzinfo=timezone.utc)


def test_ms_date_a_utc_parsea_formato_aspnet():
    assert ms_date_a_utc("/Date(1793756700000)/") == datetime(2026, 11, 4, 1, 45, tzinfo=timezone.utc)
