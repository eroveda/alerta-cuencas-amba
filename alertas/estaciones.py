"""Estaciones del piloto. Coordenadas de SHN, SNIH y NOAA AWC."""

from alertas.modelos import Estacion

ESTACIONES: tuple[Estacion, ...] = (
    Estacion("shn", "SFER", "San Fernando (SHN)", -34.4339, -58.5403, "costa-delta", 120),
    Estacion("shn", "BSAS", "Buenos Aires – Club de Pescadores (SHN)", -34.5608, -58.3989, "costa-delta", 120),
    Estacion("shn", "LPLA", "La Plata – Monte Santiago (SHN)", -34.8339, -57.8803, "costa-delta", 120),
    Estacion("snih", "14011", "A° Medrano – Reservorio Tecnópolis (SNIH)", -34.5611, -58.5078, "medrano", 120),
    # Aeropuertos (METAR): fenómeno presente, sin milímetros. Zona por cercanía.
    Estacion("metar", "SABE", "Aeroparque", -34.559, -58.416, "", 90, "meteo"),
    Estacion("metar", "SADF", "San Fernando (aeropuerto)", -34.457, -58.593, "", 90, "meteo"),
    Estacion("metar", "SADP", "El Palomar", -34.610, -58.613, "", 90, "meteo"),
    Estacion("metar", "SADM", "Morón", -34.676, -58.643, "", 90, "meteo"),
    Estacion("metar", "SAEZ", "Ezeiza", -34.822, -58.536, "", 90, "meteo"),
    Estacion("metar", "SADL", "La Plata (aeropuerto)", -34.972, -57.895, "", 90, "meteo"),
)
