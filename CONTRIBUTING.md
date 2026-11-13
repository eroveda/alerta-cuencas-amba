# Cómo sumarse

Gracias por querer aportar. No hace falta programar para ayudar.

## Sin programar

- **Si vivís cerca del agua** (Delta, costa sur, ribera): contanos en un issue qué dato te
  sirve, cuál no entendés y cómo te gustaría recibir un aviso.
- **Si conocés una fuente de datos pública** que no estamos usando: abrí un issue con el link
  y qué mide.
- **Si encontrás un error** en un dato o en la web: abrí un issue con una captura y la hora.

## Programando

1. Hacé un fork y creá una rama.
2. `uv sync` y corré los tests: `.venv/bin/pytest --cov`.
3. Hacé tu cambio **con su test**. Los tests de fuentes usan respuestas reales guardadas en
   `tests/fixtures/`: si sumás una fuente, guardá un ejemplo de su respuesta ahí.
4. Abrí un pull request explicando qué cambia y por qué.

### Reglas del proyecto

- **Cada fuente es un módulo** en `alertas/fuentes/` con dos funciones: `parse` (pura, sin red)
  y `obtener` (la que descarga). Se registra en `alertas/fuentes/registro.py`.
- **La web lee un contrato fijo** ([`docs/contrato-estado.md`](docs/contrato-estado.md)).
  Si cambiás `estado.json`, actualizá el contrato.
- **Lenguaje de observación, no de alerta.** Nunca "alerta roja" ni los colores del SMN: este
  proyecto no es oficial y no debe confundirse con un aviso oficial.
- **Nada de tokens ni claves en el repositorio.**

## Conducta

Trato respetuoso. Es un proyecto cívico: lo que importa es que el dato le llegue a quien lo
necesita.
