from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Lectura:
    """Un valor medido o calculado en una estación, con fecha en UTC."""

    fuente: str
    estacion: str
    variable: str  # "altura" | "residuo" | "astronomica"
    ts: datetime
    valor: float


@dataclass(frozen=True)
class Estacion:
    fuente: str
    codigo: str
    nombre: str
    lat: float
    lon: float
    zona: str  # zona principal ("" = se asigna por cercanía)
    max_atraso_min: int  # más atraso que esto = dato viejo
    tipo: str = "hidro"  # "hidro" (altura) | "meteo" (lluvia/tormenta)

    @property
    def id(self) -> str:
        return f"{self.fuente}:{self.codigo}"
