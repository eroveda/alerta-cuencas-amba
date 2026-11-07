# Diseño Fase 1 — motor de reglas, estados por cuenca y envíos

## 0. Reorientación (2026-11-07) — leer primero

Una auditoría de producto mostró que el plan original construía demasiado y apuntaba mal.
Esta sección **manda sobre el resto del documento** cuando se contradicen.

**Diagnóstico**

- En lluvia intensa (Medrano, arroyos CABA) no aportamos nada que el SMN no dé: no hay lluvia
  medida en tiempo real, `hidro-arroyo` está desactivado y METAR a 10 km es grueso para celdas convectivas.
  Las señales que quedan son la CAP del SMN más METAR, o sea la alerta del SMN con otro formato.
- Donde sí hay ventaja es en la **sudestada de Costa/Delta**: datos reales (SHN + INA), horas de anticipación,
  aviso oficial técnico y disperso, y no encontramos ningún competidor.
- La lección de Valencia es de **última milla** (traducir y llegar), no de detección.
- Existe **AlertAR** (sistema nacional de alertas al celular, anunciado en dic. 2025): hay que verificar qué cubre en el AMBA.
- Telegram, Instagram y web push no llegan a la población más expuesta (ribereños, isleños), que usa WhatsApp.
- Usar la escala amarillo/naranja/rojo del SMN de cara al público genera confusión y riesgo cuando no coincidimos con lo oficial.
- Una PC local que se cuelga no sirve para avisar durante tormentas, que traen cortes de luz e internet.

**Nuevo foco**

1. **Producto de avisos = solo sudestada en Costa/Delta.** Es el único piloto de avisos.
2. **Medrano y la lluvia en CABA pasan a tablero abierto**, sin avisos: "qué dicen todas las fuentes ahora, por cuenca",
   para periodistas, municipios y ONGs.
3. **Distribución por referentes** (delegados isleños, parroquias, comedores, Cruz Roja/TECHO): un aviso
   corto que ellos reenvían por WhatsApp, más el mapa público. Pocos destinatarios, que llegan a quien lo necesita.
4. **Vocabulario público de observación, no de alerta.** Por ejemplo "el río está 1,10 m sobre la marea en San Fernando y sigue subiendo".
   Los niveles de colores quedan internos (mapa admin y Telegram interno). Los niveles de alerta los emiten los organismos oficiales.
5. **Incidencia:** publicar el relevamiento de fuentes y sus huecos (radar SMN, SAT CABA, Riachuelo, Reconquista)
   como argumento para que abran esos datos.

**Qué se deja de construir (por ahora)**

| Se saca | Motivo |
|---|---|
| Avisos para Medrano y demás cuencas pluviales | No hay ventaja sobre el SMN sin lluvia medida |
| Canales Meshtastic y radio TTS (paso 6) | No llegan a pesar esta temporada |
| Instagram API y web push | No notifican de verdad o no llegan al público objetivo |
| Expansión cuenca por cuenca (Fase 3) | Primero demostrar valor en una sola |
| Grupo `oficial-meteo` como disparador de avisos públicos | Duplica al SMN y suma confusión |

**Qué se adelanta**

- Hosting externo y heartbeat desde afuera **antes** de cualquier aviso público (antes estaba en la Fase 4).
- Definir **antes** del modo sombra qué cuenta como acierto, falsa alarma y aviso perdido para sudestada,
  usando los avisos del SHN y las crecidas reportadas como referencia. Asumir que esta temporada no da validez estadística.

**Próximas acciones, en orden**

1. Mandar el mail al SHN (datum y permiso de uso). **Bloquea todo**: sin datum, `hidro-rio` no se activa.
2. Averiguar si AlertAR está operativo en el AMBA y qué riesgos cubre.
3. Hablar con 2 o 3 referentes del Delta o de la costa sur (Quilmes/Avellaneda) **antes de escribir más código**:
   ¿cómo se enteran hoy de una sudestada?, ¿qué les sirvió la última vez?, ¿qué umbral les importa?
4. Recién después: implementar (orden reducido en la sección 10) y cerrar las decisiones de la sección 11.

---

> Estado: **borrador para revisión**. No hay código todavía.
> Objetivo de la Fase 1: el sistema decide niveles y "envía" avisos **solo a un Telegram interno**
> (modo sombra), durante semanas, para medir aciertos y falsas alarmas antes de abrirlo al público.

## 1. Vista general

```
poll (cada 5 min)                                   despachador (loop aparte)
─────────────────                                   ─────────────────────────
fuentes ─► lecturas/CAPs ─► SEÑALES ─► REGLAS ─► MÁQUINA DE ESTADOS ─► transición + envíos
                             (puro)     (puro)        (puro)              │  (misma transacción SQLite)
                                                                          ▼
                                                   tabla envios (outbox) ─► Canal.enviar()
                                                                            telegram / push / radio / meshtastic
```

Regla de oro: **todo lo que decide es una función pura**. Señales, reglas y máquina de estados
reciben datos y la hora, y devuelven datos. Así el backtesting es correr las mismas funciones
sobre datos históricos, y un test reproduce exactamente lo que pasó en una tormenta.

## 2. Señales

Una `Senal` es lo que una fuente dice sobre una cuenca en un momento:

```python
@dataclass(frozen=True)
class Senal:
    zona: str          # "medrano"
    grupo: str         # grupo de independencia (ver abajo)
    fuente: str        # "smn_cap", "metar:SABE", "shn:SFER", "ina"
    nivel: Nivel       # verde < amarillo < naranja < rojo
    ts: datetime
    motivo: str        # texto corto legible: "Alerta naranja SMN por tormentas"
```

**Grupos de independencia** (la regla de "dos señales para rojo" exige dos grupos distintos,
no dos fuentes que miran lo mismo):

| Grupo | Fuentes hoy | Mapeo a nivel |
|---|---|---|
| `oficial-meteo` | CAP SMN (luego ACP) | el color de la alerta |
| `observado-lluvia` | METAR ≤10 km | moderada → amarillo · fuerte o tormenta en el lugar → naranja |
| `hidro-rio` | SHN altura/residuo, INA p95 | **desactivado** hasta confirmar el datum con el SHN |
| `hidro-arroyo` | SNIH (futuro: estaciones aguas abajo) | desactivado: Tecnópolis no sirve solo |
| `oficial-hidro` | aviso SHN (cuando tengamos el parser) | el color del aviso |

Un dato viejo (más atrasado que `max_atraso_min`) **no genera señal**. Si falta una fuente
crítica, la cuenca queda marcada `degradada` (se ve en el mapa y en el Telegram interno),
pero **nunca baja de nivel por falta de datos**.

## 3. Reglas (función pura)

`evaluar(senales_de_la_zona, config_zona) -> Propuesta(nivel, motivos)`

| Nivel propuesto | Condición |
|---|---|
| **rojo** | alerta oficial roja, **o** dos grupos distintos en ≥ naranja |
| **naranja** | alerta oficial naranja, **o** un grupo en naranja + otro grupo en ≥ amarillo |
| **amarillo** | cualquier señal en ≥ amarillo |
| **verde** | ninguna señal |

Nota: lluvia fuerte observada **sola** da amarillo, no naranja. Hace falta que otro grupo
la acompañe. Esto es deliberado para la Fase 1 y se ajusta con los datos del modo sombra.

Las reglas tienen versión (`REGLAS_VERSION = 1`) y se guarda en cada transición: si cambian,
se sabe qué versión tomó cada decisión.

## 4. Máquina de estados por cuenca (función pura)

`avanzar(estado_actual, propuesta, ahora, config) -> (estado_nuevo, transicion | None)`

- **Subir es inmediato.** Si la propuesta es mayor que el estado, se transiciona en ese poll.
- **Bajar exige estabilidad (histéresis).** La propuesta menor tiene que sostenerse:
  rojo→naranja 60 min · naranja→amarillo 45 min · amarillo→verde 30 min.
  Nunca baja mientras haya una alerta oficial vigente de ese nivel o mayor.
- **Cierre.** Volver a verde desde amarillo o más emite una transición `cierre`
  ("terminó la alerta en …"), que también se envía.
- **Anti-rebote.** Si una cuenca vuelve a subir al mismo nivel dentro de los 60 min de haber
  bajado, se registra la transición pero el mensaje dice "se renueva" en vez de repetir el aviso completo.

El estado actual se reconstruye leyendo la última transición de cada cuenca. Nueva tabla, solo
se agregan filas:

```sql
CREATE TABLE transiciones (
  id INTEGER PRIMARY KEY, zona TEXT NOT NULL, ts TEXT NOT NULL,
  desde TEXT NOT NULL, hacia TEXT NOT NULL, tipo TEXT NOT NULL,  -- sube | baja | cierre | renueva
  motivos TEXT NOT NULL,          -- JSON con las señales que la justificaron
  reglas_version INTEGER NOT NULL, modo TEXT NOT NULL             -- sombra | publico
);
```

## 5. Envíos (patrón outbox)

La transición y sus mensajes se escriben **en la misma transacción**. Un despachador separado
los envía. Si la PC se reinicia en medio de una tormenta, al volver no se pierde ni se duplica nada.

```sql
CREATE TABLE envios (
  id INTEGER PRIMARY KEY, transicion_id INTEGER NOT NULL REFERENCES transiciones(id),
  canal TEXT NOT NULL, cuerpo TEXT NOT NULL,
  estado TEXT NOT NULL,           -- pendiente | enviado | fallido | vencido | retenido
  intentos INTEGER NOT NULL DEFAULT 0, proximo_intento TEXT, error TEXT,
  UNIQUE (transicion_id, canal)   -- idempotencia: un mensaje por transición y canal
);
```

- **Reintentos** con espera creciente (1, 2, 4, 8 min), máximo 6.
- **Vencimiento.** Un aviso de subida con más de 30 min sin enviar pasa a `vencido` si ya hay
  una transición más nueva de esa cuenca. No se manda información vieja.
- **Canales** como adaptadores con la misma interfaz:
  `Canal.enviar(mensaje) -> Resultado`. En la Fase 1 hay uno real (`telegram_interno`) y dos simulados:
  - `meshtastic` (simulado): arma el texto de ≤200 bytes y lo escribe en un log. El real usará la
    biblioteca `meshtastic` por serie o TCP cuando haya un nodo.
  - `radio`: genera el texto para leer al aire y un audio TTS en `salida/radio/` para radios comunitarias.
- **Plantillas por canal.** Siempre incluyen: nivel, cuenca, qué se observa, hora, fuente,
  "sistema no oficial — seguí a SMN / SHN / Defensa Civil" y, en el cierre, "terminó la alerta".

## 6. Kill switch y modo

- Tabla `control` con `pausa` (bool) y `modo` (`sombra` | `publico`).
- En `pausa`, las transiciones **se siguen registrando**, pero los envíos se crean como `retenido`.
  Así se puede auditar qué se habría mandado.
- En `sombra` solo existe el canal `telegram_interno`. Pasar a `publico` es la Fase 2 y es un
  cambio manual explícito.
- Comando: `python -m alertas.cli control pausa|reanudar|modo sombra`.

## 7. Vigilancia (heartbeat)

- El poll actualiza `control.ultimo_poll`. El despachador avisa por Telegram interno si pasan
  más de 15 min sin poll, o si una fuente lleva más de 1 h caída.
- Más adelante (hosting en Oracle), un Worker de Cloudflare hace el mismo control desde afuera.

## 8. Backtesting

`python -m alertas.cli replay --desde ... --hasta ...` recorre las lecturas y CAPs guardados,
paso a paso cada 5 min, con las mismas funciones puras, y lista las transiciones que habría hecho.
Primer caso: 03/11/2026 (verdadero negativo esperado en Medrano: amarillo por lluvia moderada,
sin naranja). Hacen falta tormentas reales fuertes para validar; las vamos juntando en modo sombra.

## 9. Pruebas

- Reglas: tabla de casos (señales → nivel), incluyendo "dos fuentes del mismo grupo no hacen rojo".
- Máquina de estados: subida inmediata, histéresis, cierre, anti-rebote, no baja con alerta oficial vigente.
- Outbox: idempotencia (dos veces la misma transición → un envío), reintentos, vencimiento, pausa → retenido.
- Despachador con un canal falso que falla N veces.
- Replay del 03/11 como test de integración.

## 10. Orden de implementación (reducido 2026-11-07)

Se aplica solo a **Costa/Delta y sudestada** (grupo `hidro-rio` + aviso SHN). Arranca cuando el SHN confirme el datum.

1. `Senal`, `Nivel` y la extracción de señales de sudestada (SHN residuo, INA p95) desde `estado.py`.
2. Reglas + tests.
3. Máquina de estados + tabla `transiciones` + tests.
4. Comando `replay` (permite ver resultados antes de enviar nada).
5. Outbox + despachador + canal `telegram_interno` (token por variable de entorno, nunca en el código).
6. Kill switch y heartbeat.
7. Plantilla pública en vocabulario de observación, pensada para que los referentes la reenvíen por WhatsApp.
8. Hosting externo antes de pasar a `publico`.

~~Canales simulados `meshtastic` y `radio`~~: postergados (ver sección 0).
En paralelo, sin avisos: tablero abierto por cuenca (es el mapa actual, mejorado).

## 11. Decisiones abiertas (para el usuario)

1. ~~**¿El amarillo se notifica?**~~ Resuelta por la reorientación: los colores son internos; hacia el público
   (vía referentes) solo salen mensajes de observación al subir a naranja o rojo y en los cierres.
2. **Tiempos de histéresis** (60/45/30 min): ¿razonables para arrancar?
3. **Lluvia fuerte observada sola → amarillo** (no naranja): ¿de acuerdo para la Fase 1?
