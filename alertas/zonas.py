"""Zonas de alerta (cuencas) del AMBA.

Geometrías: COHIFE (CC-BY-4.0) para cuencas completas y BA Data para las
subcuencas porteñas. "costa-delta" es PROVISORIA: delta bonaerense + afluentes
al RdP recortados al AMBA (incluye por ahora Sarandí y La Plata).
"""

from dataclasses import dataclass

from shapely.geometry import Point, box, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

SIMPLIFICAR_GRADOS = 0.0005  # ~50 m: liviano para la web, suficiente para cruzar alertas


@dataclass(frozen=True)
class DefZona:
    id: str
    nombre: str
    origen: str  # "cohife" | "caba"
    nombres_fuente: tuple[str, ...]
    piloto: bool = False
    recorte: tuple[float, float, float, float] | None = None
    nota: str = ""


DEFINICIONES: tuple[DefZona, ...] = (
    DefZona("medrano", "Arroyo Medrano", "cohife", ("Arroyo Medrano",), piloto=True),
    DefZona(
        "costa-delta", "Costa y Delta", "cohife",
        ("Delta del río Paraná", "Afluentes al río de la Plata en Buenos Aires"),
        piloto=True, recorte=(-58.95, -35.0, -57.75, -34.15),
        nota="Geometría provisoria: incluye por ahora Sarandí/Santo Domingo y La Plata.",
    ),
    DefZona("maldonado", "Arroyo Maldonado", "cohife", ("Arroyo Maldonado",)),
    DefZona("vega", "Arroyo Vega", "caba", ("Cuenca Vega",)),
    DefZona("white", "Arroyo White", "caba", ("Cuenca White",)),
    DefZona("cildanez", "Arroyo Cildáñez", "caba", ("Cuenca Cildañez",), nota="Solo la parte dentro de CABA."),
    DefZona("matanza-riachuelo", "Matanza-Riachuelo", "cohife", ("Río Matanza-Riachuelo",)),
    DefZona("reconquista", "Río Reconquista", "cohife", ("Río Reconquista",)),
    DefZona("lujan", "Río Luján", "cohife", ("Río Luján",)),
)

_CAMPO_NOMBRE = {"cohife": "CUENCA", "caba": "nombre"}


def _geometria(defn: DefZona, fuentes: dict[str, dict]) -> BaseGeometry | None:
    campo = _CAMPO_NOMBRE[defn.origen]
    partes = [
        shape(f["geometry"])
        for f in fuentes[defn.origen].get("features", [])
        if (f.get("properties") or {}).get(campo) in defn.nombres_fuente
    ]
    if not partes:
        return None
    geom = unary_union([p if p.is_valid else p.buffer(0) for p in partes])
    if defn.recorte:
        geom = geom.intersection(box(*defn.recorte))
    return geom.simplify(SIMPLIFICAR_GRADOS, preserve_topology=True)


def construir_zonas(cohife: dict, caba: dict) -> dict:
    fuentes = {"cohife": cohife, "caba": caba}
    features = []
    for defn in DEFINICIONES:
        geom = _geometria(defn, fuentes)
        if geom is None or geom.is_empty:
            continue
        features.append({
            "type": "Feature",
            "properties": {"id": defn.id, "nombre": defn.nombre, "piloto": defn.piloto,
                           "origen": defn.origen, "nota": defn.nota},
            "geometry": mapping(geom),
        })
    return {"type": "FeatureCollection", "features": features}


class Zonas:
    def __init__(self, fc: dict) -> None:
        self.fc = fc
        self._geoms = {f["properties"]["id"]: shape(f["geometry"]) for f in fc["features"]}
        self.props = {f["properties"]["id"]: f["properties"] for f in fc["features"]}

    @property
    def ids(self) -> list[str]:
        return list(self._geoms)

    def cercanas(self, lon: float, lat: float, radio_grados: float) -> list[str]:
        """Zonas a menos de `radio_grados` del punto (0,1° ≈ 10 km en el AMBA)."""
        return self.afectadas([Point(lon, lat).buffer(radio_grados)])

    def afectadas(self, poligonos: list[BaseGeometry]) -> list[str]:
        return [zid for zid, g in self._geoms.items() if any(g.intersects(p) for p in poligonos)]
