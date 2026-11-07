"""Comandos: `zonas` (arma el GeoJSON de cuencas) y `poll` (consulta fuentes y arma estado.json).

Uso:
    python -m alertas.cli zonas
    python -m alertas.cli poll
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from alertas.db import Base
from alertas.estado import armar_estado
from alertas.fuentes import ina, registro, smn_cap
from alertas.modelos import Lectura
from alertas.tiempo import ahora_utc
from alertas.zonas import Zonas, construir_zonas

log = logging.getLogger("alertas")
RAIZ = Path(__file__).resolve().parent.parent
MUESTRAS_GEO = RAIZ / "data" / "samples" / "geo"
ZONAS_PATH = RAIZ / "web" / "data" / "zonas.geojson"
ESTADO_PATH = RAIZ / "web" / "data" / "estado.json"
DB_PATH = RAIZ / "data" / "alertas.sqlite"
VENTANA_LECTURAS = timedelta(hours=24)
MAX_DESCARGAS_CAP = 200  # por poll; el resto se baja en los siguientes


def _consultar(nombre: str, fuentes: dict, fn) -> object | None:
    """Ejecuta una consulta y registra el resultado sin propagar errores."""
    try:
        resultado = fn()
        fuentes[nombre] = {"ok": True}
        return resultado
    except Exception as exc:  # una fuente caída no debe frenar a las demás
        log.warning("fuente %s falló: %s", nombre, exc)
        fuentes[nombre] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}
        return None


def _lecturas(ahora: datetime, fuentes: dict) -> list[Lectura]:
    """Consulta cada fuente registrada por separado: si se cae una, las demás siguen."""
    lecturas: list[Lectura] = []
    for f in registro.fuentes_de_lecturas():
        lecturas.extend(_consultar(f.nombre, fuentes, lambda f=f: f.obtener(ahora)) or [])
    return lecturas


def _bajar_caps_nuevos(db: Base, links: list[str], ahora: datetime) -> tuple[int, int]:
    nuevos, invalidos = 0, 0
    for link in db.links_cap_nuevos(links)[:MAX_DESCARGAS_CAP]:
        try:
            xml = smn_cap.obtener_cap(link)
        except Exception as exc:  # se reintenta en el próximo poll
            log.warning("no se pudo bajar CAP %s: %s", link, exc)
            continue
        try:
            expires = smn_cap.parse_cap(xml).expires
            nuevos += 1
        except Exception as exc:  # CAP roto: se marca visto (expira ya) para no reintentarlo
            log.warning("CAP inválido %s: %s", link, exc)
            expires, invalidos = ahora, invalidos + 1
        db.guardar_cap(link, xml, expires)
    return nuevos, invalidos


def _caps(db: Base, fuentes: dict, ahora: datetime) -> list[smn_cap.AlertaCap]:
    links = _consultar("smn_cap", fuentes, smn_cap.obtener_links) or []
    nuevos, invalidos = _bajar_caps_nuevos(db, links, ahora)
    alertas = []
    for xml in db.caps_vigentes(ahora):
        try:
            alertas.append(smn_cap.parse_cap(xml))
        except Exception as exc:
            invalidos += 1
            log.warning("CAP guardado inválido: %s", exc)
    if "smn_cap" in fuentes:
        fuentes["smn_cap"].update({"caps_nuevos": nuevos, "caps_invalidos": invalidos})
    return alertas


def poll(db: Base, zonas_path: Path, salida: Path, ahora: datetime) -> dict:
    fuentes: dict[str, dict] = {}
    db.guardar_lecturas(_lecturas(ahora, fuentes))
    puntos = _consultar("ina", fuentes, ina.obtener) or []
    alertas = smn_cap.vigentes(_caps(db, fuentes, ahora), ahora)
    db.podar(ahora)

    zonas = Zonas(json.loads(zonas_path.read_text(encoding="utf-8")))
    estado = armar_estado(zonas, alertas, db.lecturas_desde(ahora - VENTANA_LECTURAS),
                          ina.resumen(puntos, ahora), fuentes, ahora)
    tmp = salida.with_suffix(".tmp")
    tmp.write_text(json.dumps(estado, ensure_ascii=False, indent=1, allow_nan=False), encoding="utf-8")
    os.replace(tmp, salida)  # escritura atómica: el mapa nunca lee un archivo a medias
    return estado


def zonas(salida: Path) -> None:
    cohife = json.loads((MUESTRAS_GEO / "cohife" / "cohife_amba.geojson").read_text(encoding="utf-8"))
    caba = json.loads((MUESTRAS_GEO / "caba" / "cuencas_caba_valid_4326.geojson").read_text(encoding="utf-8"))
    fc = construir_zonas(cohife, caba)
    salida.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    log.info("zonas: %d escritas en %s", len(fc["features"]), salida)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="alertas")
    parser.add_argument("comando", choices=["zonas", "poll"])
    args = parser.parse_args(argv)
    ZONAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if args.comando == "zonas":
        zonas(ZONAS_PATH)
    else:
        estado = poll(Base(DB_PATH), ZONAS_PATH, ESTADO_PATH, ahora_utc())
        caidas = [n for n, f in estado["fuentes"].items() if not f["ok"]]
        log.info("estado escrito; fuentes caídas: %s", caidas or "ninguna")
    return 0


if __name__ == "__main__":
    sys.exit(main())
