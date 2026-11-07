"""SMN: alertas oficiales en formato CAP 1.2 (feed registrado ante la OMM).

Particularidades verificadas: areaDesc vacío (hay que cruzar polígonos), el feed
incluye alertas vencidas, y las actualizaciones referencian a la emisión previa.
La equivalencia de colores es la convención CAP; no se vio aún un rojo real en el AMBA.
"""

import re
import xml.etree.ElementTree as ET  # noqa: S405 (solo para tipos; el parseo usa defusedxml)
from dataclasses import dataclass, field
from datetime import datetime

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring as xml_seguro
from shapely.errors import ShapelyError
from shapely.geometry import Polygon
from shapely.validation import make_valid

from alertas.http import pedir
from alertas.tiempo import a_utc

URL_RSS = "https://ssl.smn.gob.ar/CAP/AR.php"
NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}
_LINK_OK = re.compile(r"^https://ssl\.smn\.gob\.ar/[\w/.\-]+\.xml$")
NIVELES = {"Extreme": "rojo", "Severe": "naranja"}
MAX_BYTES_CAP = 256 * 1024
MAX_POLIGONOS = 20
MAX_PUNTOS = 5000  # por CAP, sumando polígonos


@dataclass(frozen=True)
class AlertaCap:
    identifier: str
    sent: datetime
    expires: datetime
    msg_type: str
    event: str
    severity: str
    headline: str
    description: str
    instruction: str
    references: list[str] = field(default_factory=list)
    poligonos: list[Polygon] = field(default_factory=list)

    @property
    def nivel(self) -> str:
        return nivel_por_severidad(self.severity)


def nivel_por_severidad(severity: str) -> str:
    return NIVELES.get(severity, "amarillo")


def _parsear_xml(texto: str) -> ET.Element:
    try:
        return xml_seguro(texto.encode("utf-8"), forbid_dtd=True)
    except (DefusedXmlException, ET.ParseError) as exc:
        raise ValueError(f"XML rechazado: {exc}") from exc


def parse_rss(texto: str) -> list[str]:
    raiz = _parsear_xml(texto)
    links = [(item.findtext("link") or "").strip() for item in raiz.iter("item")]
    return [l for l in links if _LINK_OK.match(l)]


def _poligonos(textos: list[str]) -> list[Polygon]:
    if len(textos) > MAX_POLIGONOS:
        raise ValueError(f"CAP con demasiados polígonos ({len(textos)})")
    if sum(len(t.split()) for t in textos) > MAX_PUNTOS:
        raise ValueError("CAP con demasiados puntos")
    salida = []
    for texto in textos:
        try:
            # CAP usa "lat,lon"; shapely necesita (lon, lat)
            puntos = [(float(lon), float(lat)) for lat, lon in (par.split(",") for par in texto.split())]
            geom = Polygon(puntos)
            salida.append(geom if geom.is_valid else make_valid(geom))
        except (ValueError, TypeError, ShapelyError) as exc:
            raise ValueError(f"polígono CAP inválido: {exc}") from exc
    return salida


def _referencias(texto: str) -> list[str]:
    # formato CAP: "sender,identifier,sent" separados por espacios
    return [r.split(",")[1] for r in texto.split() if r.count(",") >= 2]


def parse_cap(texto: str) -> AlertaCap:
    raiz = _parsear_xml(texto)
    info = raiz.find("cap:info", NS)
    if info is None:
        raise ValueError("CAP sin <info>")

    def campo(nodo: ET.Element, nombre: str) -> str:
        return (nodo.findtext(f"cap:{nombre}", default="", namespaces=NS) or "").strip()

    return AlertaCap(
        identifier=campo(raiz, "identifier"),
        sent=a_utc(datetime.fromisoformat(campo(raiz, "sent"))),
        expires=a_utc(datetime.fromisoformat(campo(info, "expires"))),
        msg_type=campo(raiz, "msgType"),
        event=campo(info, "event"),
        severity=campo(info, "severity"),
        headline=campo(info, "headline"),
        description=campo(info, "description"),
        instruction=campo(info, "instruction"),
        references=_referencias(campo(raiz, "references")),
        poligonos=_poligonos([p.text for p in info.iterfind("cap:area/cap:polygon", NS) if p.text]),
    )


def vigentes(alertas: list[AlertaCap], ahora: datetime) -> list[AlertaCap]:
    reemplazadas = {ref for a in alertas for ref in a.references}
    unicas = {a.identifier: a for a in alertas}  # el mismo CAP puede llegar por dos links
    return [
        a
        for a in unicas.values()
        if a.expires > ahora and a.msg_type != "Cancel" and a.identifier not in reemplazadas
    ]


def obtener_links() -> list[str]:
    return parse_rss(pedir(URL_RSS))


def obtener_cap(link: str) -> str:
    if not _LINK_OK.match(link):
        raise ValueError(f"link CAP no permitido: {link}")
    return pedir(link, max_bytes=MAX_BYTES_CAP)
