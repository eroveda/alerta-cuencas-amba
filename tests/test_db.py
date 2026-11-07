from datetime import datetime, timedelta, timezone

from alertas.db import Base
from alertas.modelos import Lectura


def test_guarda_sin_duplicar_y_devuelve_ultimas(tmp_path):
    db = Base(tmp_path / "x.sqlite")
    t0 = datetime(2026, 11, 4, 1, 0, tzinfo=timezone.utc)
    l1 = Lectura("shn", "SFER", "altura", t0, 1.0)
    l2 = Lectura("shn", "SFER", "altura", t0 + timedelta(hours=1), 1.1)
    db.guardar_lecturas([l1, l2])
    db.guardar_lecturas([l2])
    ultimas = db.ultimas_lecturas()
    assert ultimas == [l2]


def test_registra_cap_vistos(tmp_path):
    db = Base(tmp_path / "x.sqlite")
    ahora = datetime(2026, 11, 4, 1, 0, tzinfo=timezone.utc)
    assert db.links_cap_nuevos(["a", "b"]) == ["a", "b"]
    db.guardar_cap("a", "<alert/>", ahora + timedelta(hours=2))
    assert db.links_cap_nuevos(["a", "b"]) == ["b"]
    assert db.caps_vigentes(ahora) == ["<alert/>"]
    assert db.caps_vigentes(ahora + timedelta(hours=3)) == []
