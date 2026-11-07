"""Almacenamiento local en SQLite (liviano, sin servidor). Fechas en formato iso_utc."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from alertas.modelos import Lectura
from alertas.tiempo import iso_utc

RETENCION_LECTURAS = timedelta(days=30)
RETENCION_CAPS = timedelta(days=7)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS lecturas (
    fuente TEXT NOT NULL, estacion TEXT NOT NULL, variable TEXT NOT NULL,
    ts TEXT NOT NULL, valor REAL NOT NULL,
    PRIMARY KEY (fuente, estacion, variable, ts)
);
CREATE TABLE IF NOT EXISTS caps_v2 (
    link TEXT PRIMARY KEY, xml TEXT NOT NULL, expires TEXT NOT NULL
);
DROP TABLE IF EXISTS caps;
"""


def _lectura(fila: tuple) -> Lectura:
    f, e, v, ts, val = fila
    return Lectura(f, e, v, datetime.fromisoformat(ts), val)


class Base:
    def __init__(self, ruta: Path) -> None:
        self.con = sqlite3.connect(ruta)
        self.con.executescript(ESQUEMA)

    def guardar_lecturas(self, lecturas: list[Lectura]) -> None:
        with self.con:
            self.con.executemany(
                "INSERT OR REPLACE INTO lecturas VALUES (?, ?, ?, ?, ?)",
                [(l.fuente, l.estacion, l.variable, iso_utc(l.ts), l.valor) for l in lecturas],
            )

    def ultimas_lecturas(self) -> list[Lectura]:
        """La lectura más reciente por (fuente, estación, variable). En SQLite, con un
        único MAX(), las columnas no agregadas salen de la fila del máximo."""
        filas = self.con.execute(
            "SELECT fuente, estacion, variable, MAX(ts), valor FROM lecturas "
            "GROUP BY fuente, estacion, variable"
        ).fetchall()
        return [_lectura(f) for f in filas]

    def lecturas_desde(self, desde: datetime) -> list[Lectura]:
        filas = self.con.execute(
            "SELECT fuente, estacion, variable, ts, valor FROM lecturas WHERE ts >= ? ORDER BY ts",
            (iso_utc(desde),),
        ).fetchall()
        return [_lectura(f) for f in filas]

    def links_cap_nuevos(self, links: list[str]) -> list[str]:
        vistos = {r[0] for r in self.con.execute("SELECT link FROM caps_v2")}
        return [l for l in links if l not in vistos]

    def guardar_cap(self, link: str, xml: str, expires: datetime) -> None:
        with self.con:
            self.con.execute("INSERT OR IGNORE INTO caps_v2 VALUES (?, ?, ?)", (link, xml, iso_utc(expires)))

    def caps_vigentes(self, ahora: datetime) -> list[str]:
        return [r[0] for r in self.con.execute(
            "SELECT xml FROM caps_v2 WHERE expires > ? ORDER BY expires", (iso_utc(ahora),))]

    def podar(self, ahora: datetime) -> None:
        with self.con:
            self.con.execute("DELETE FROM caps_v2 WHERE expires < ?", (iso_utc(ahora - RETENCION_CAPS),))
            self.con.execute("DELETE FROM lecturas WHERE ts < ?", (iso_utc(ahora - RETENCION_LECTURAS),))
