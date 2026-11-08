"""Genera web/og.png (1200x630), la imagen que muestran las redes al compartir el link.

Uso: uv run --with pillow python scripts/og.py
Dibuja la forma de la última serie de San Fernando (sin cifras, para que no envejezca).
"""

import json
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
SERIE = RAIZ / "web" / "data" / "serie.json"
SALIDA = RAIZ / "web" / "og.png"
FUENTES = Path("/usr/share/fonts/truetype/dejavu")
W, H = 1200, 630
PAPEL, TINTA, SUAVE, AGUA, ROJO, LINEA = "#f3efe6", "#16130f", "#5b544a", "#1f5f8b", "#c4221b", "#d6cfc1"


def fuente(nombre: str, tam: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FUENTES / nombre), tam)


def curvas(draw: ImageDraw.ImageDraw, series: list[tuple[list, str, int]], caja: tuple[int, int, int, int]) -> None:
    """Dibuja varias series con la misma escala de tiempo y altura, para que sean comparables."""
    x0, y0, x1, y1 = caja
    todos = [(datetime.fromisoformat(ts).timestamp(), v) for serie, _, _ in series for ts, v in serie]
    t_lo, t_hi = min(t for t, _ in todos), max(t for t, _ in todos)
    v_lo, v_hi = min(v for _, v in todos), max(v for _, v in todos)
    for serie, color, ancho in series:
        pts = [(x0 + (datetime.fromisoformat(ts).timestamp() - t_lo) / ((t_hi - t_lo) or 1) * (x1 - x0),
                y1 - (v - v_lo) / ((v_hi - v_lo) or 1) * (y1 - y0)) for ts, v in serie]
        draw.line(pts, fill=color, width=ancho, joint="curve")


def main() -> None:
    img = Image.new("RGB", (W, H), PAPEL)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=TINTA)
    d.ellipse([70, 78, 96, 104], fill=ROJO)
    d.text((112, 70), "Alerta Cuencas AMBA", font=fuente("DejaVuSans-Bold.ttf", 34), fill=TINTA)
    d.text((70, 150), "¿Cuánto está subiendo\nel Río de la Plata?", font=fuente("DejaVuSans-Bold.ttf", 68),
           fill=TINTA, spacing=10)
    d.text((70, 345), "Sudestada en vivo · pronóstico 48 h · alertas del SMN",
           font=fuente("DejaVuSansMono.ttf", 26), fill=SUAVE)

    caja = (70, 420, 1130, 560)
    for y in range(caja[1], caja[3] + 1, 35):
        d.line([(caja[0], y), (caja[2], y)], fill=LINEA, width=1)
    serie = json.loads(SERIE.read_text(encoding="utf-8")) if SERIE.exists() else {}
    sfer = serie.get("estaciones", {}).get("SFER", {})
    altura = sfer.get("altura", [])
    if len(altura) > 2:
        hasta = altura[-1][0]
        astro = [p for p in sfer.get("astronomica", []) if p[0] <= hasta]
        curvas(d, [(astro, SUAVE, 3), (altura, AGUA, 7)], caja)

    d.text((70, 582), "Proyecto cívico y abierto · datos de SHN, INA y SMN · no oficial",
           font=fuente("DejaVuSansMono.ttf", 20), fill=SUAVE)
    img.save(SALIDA, optimize=True)
    print(f"escrito {SALIDA}")  # noqa: T201 - script de una sola vez


if __name__ == "__main__":
    main()
