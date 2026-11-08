"use strict";

// Todo el texto que viene de fuentes externas (CAP del SMN) se inserta con
// textContent, nunca como HTML.

const REFRESCO_MS = 60_000;
const ESTADO_VIEJO_MS = 45 * 60_000; // el poll corre cada ~10 min
// Debe coincidir con VERSION_ESQUEMA en alertas/estado.py (docs/contrato-estado.md).
const VERSION_ESQUEMA = 1;
const COLOR = {
  verde: "var(--verde)", amarillo: "var(--amarillo)", naranja: "var(--naranja)",
  rojo: "var(--rojo)", sin: "var(--sin-dato)",
};
const HEX = { verde: "#2f7d4f", amarillo: "#e3b417", naranja: "#e0661b", rojo: "#c4221b" };
const fmtHora = new Intl.DateTimeFormat("es-AR", {
  hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit",
  timeZone: "America/Argentina/Buenos_Aires",
});

const mapa = L.map("mapa", { zoomControl: true }).setView([-34.6, -58.5], 10);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 16,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · Cuencas: COHIFE, BA Data',
}).addTo(mapa);

let capaZonas = null;
const capaEstaciones = L.layerGroup().addTo(mapa);
const capasPorZona = new Map();

function el(tag, props = {}, ...hijos) {
  const nodo = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "dataset") Object.assign(nodo.dataset, v);
    else if (k === "style") for (const [p, val] of Object.entries(v)) nodo.style.setProperty(p, val);
    else nodo[k] = v;
  }
  for (const h of hijos) if (h != null) nodo.append(h);
  return nodo;
}

// Una fecha inválida del feed no debe romper todo el panel.
function hora(valor) {
  const d = new Date(valor);
  return Number.isNaN(d.getTime()) ? "—" : fmtHora.format(d);
}

const metros = (v) => (v == null ? "—" : `${v.toFixed(2)} m`);
const conSigno = (v) => (v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(2)} m`);

async function cargarJSON(url) {
  const r = await fetch(`${url}?t=${Date.now()}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.json();
}

function popupZona(z) {
  const cont = el("div", {}, el("strong", { textContent: z.nombre }));
  if (!z.alertas.length) cont.append(el("p", { className: "popup-desc", textContent: "Sin alertas vigentes del SMN." }));
  for (const a of z.alertas) {
    cont.append(
      el("p", { className: "popup-desc", textContent: `${a.evento} · ${a.nivel.toUpperCase()} · hasta ${hora(a.expira)}` }),
      el("p", { className: "popup-desc", textContent: a.descripcion }),
    );
  }
  return cont;
}

function pintarZonas(geo, estado) {
  if (capaZonas) capaZonas.remove();
  capasPorZona.clear();
  capaZonas = L.geoJSON(geo, {
    style: (f) => {
      const z = estado.zonas[f.properties.id];
      const nivel = z ? z.nivel_smn : "verde";
      return {
        color: HEX[nivel], weight: f.properties.piloto ? 2.5 : 1.2,
        fillColor: HEX[nivel], fillOpacity: nivel === "verde" ? 0.08 : 0.35,
        dashArray: f.properties.piloto ? null : "4 4",
      };
    },
    onEachFeature: (f, capa) => {
      capasPorZona.set(f.properties.id, capa);
      const z = estado.zonas[f.properties.id];
      if (z) capa.bindPopup(() => popupZona(z));
    },
  }).addTo(mapa);
  capaZonas.bringToBack();
}

function listaZonas(estado) {
  const orden = { rojo: 0, naranja: 1, amarillo: 2, verde: 3 };
  const zonas = Object.entries(estado.zonas).sort(
    ([, a], [, b]) => orden[a.nivel_smn] - orden[b.nivel_smn] || b.piloto - a.piloto,
  );
  const lista = document.getElementById("zonas");
  lista.replaceChildren(...zonas.map(([id, z]) => {
    const partes = [z.alertas.length
      ? `${z.alertas.length} alerta(s) SMN · ${z.alertas[0].evento}`
      : "Sin alertas del SMN"];
    if (z.lluvia_obs && z.lluvia_obs !== "sin") partes.push(`lluvia ${LLUVIA_TXT[z.lluvia_obs].toLowerCase()}`);
    if (z.tormenta_obs && z.tormenta_obs !== "no") partes.push(TORMENTA_TXT[z.tormenta_obs]);
    const detalle = partes.join(" · ");
    const item = el("li", { className: "zona", tabIndex: 0, style: { "--c": COLOR[z.nivel_smn] } },
      el("span", { className: "zona-barra" }),
      el("span", {},
        el("span", { className: "zona-nombre", textContent: z.nombre }),
        z.piloto ? el("span", { className: "zona-piloto", textContent: "piloto" }) : null,
        el("span", { className: "zona-detalle", textContent: detalle })),
      el("span", { className: "nivel", textContent: z.nivel_smn, dataset: { nivel: z.nivel_smn } }),
    );
    const enfocar = () => {
      const capa = capasPorZona.get(id);
      if (capa) { mapa.fitBounds(capa.getBounds(), { maxZoom: 13 }); capa.openPopup(); }
    };
    item.addEventListener("click", enfocar);
    item.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); enfocar(); } });
    return item;
  }));
}

const LLUVIA_TXT = { sin: "Sin lluvia", debil: "Débil", moderada: "Moderada", fuerte: "Fuerte" };
const LLUVIA_HEX = { sin: "#9a9184", debil: "#7fb3d5", moderada: "#2e86c1", fuerte: "#1b2f8f" };
const TORMENTA_TXT = { no: "", cercana: "tormenta cerca", si: "TORMENTA" };

function estaciones(estado) {
  capaEstaciones.clearLayers();
  const hidro = estado.estaciones.filter((s) => s.tipo !== "meteo");
  const meteo = estado.estaciones.filter((s) => s.tipo === "meteo");
  document.getElementById("estaciones").replaceChildren(...hidro.map(estacionHidro));
  document.getElementById("aeropuertos").replaceChildren(...meteo.map(estacionMeteo));
}

function estacionMeteo(s) {
  const lluvia = s.lluvia ?? "sin";
  const tormenta = TORMENTA_TXT[s.tormenta] || "";
  L.circleMarker([s.lat, s.lon], {
    radius: 6, weight: tormenta ? 3 : 1.5, color: tormenta ? "#c4221b" : "#16130f",
    fillColor: s.viejo ? "#9a9184" : LLUVIA_HEX[lluvia], fillOpacity: 0.95,
  }).bindTooltip(el("span", { textContent: `${s.nombre}: ${LLUVIA_TXT[lluvia]}${tormenta ? " · " + tormenta : ""}` }))
    .addTo(capaEstaciones);
  return el("li", { className: "aeropuerto", dataset: { viejo: String(s.viejo), lluvia } },
    el("span", { className: "aeropuerto-nombre", textContent: s.nombre }),
    el("span", { className: "aeropuerto-lluvia", textContent: s.viejo ? "sin dato" : LLUVIA_TXT[lluvia] }),
    tormenta && !s.viejo ? el("span", { className: "aeropuerto-tormenta", textContent: tormenta }) : null);
}

function estacionHidro(s) {
  {
    const datos = el("div", { className: "estacion-datos" },
      el("span", { className: "dato" }, el("b", { textContent: metros(s.altura) }), el("small", { textContent: "altura" })));
    if (s.id.startsWith("shn:")) {
      const clase = s.residuo == null ? "" : s.residuo > 0 ? "sube" : "baja";
      datos.append(el("span", { className: "dato" },
        el("b", { className: clase, textContent: conSigno(s.residuo) }), el("small", { textContent: "sudestada" })));
    }
    datos.append(el("span", { className: "dato" },
      el("b", { textContent: s.ts ? hora(s.ts).split(", ").pop() : "—" }),
      el("small", { textContent: "hora" })));

    L.circleMarker([s.lat, s.lon], {
      radius: 7, weight: 2, color: "#16130f",
      fillColor: s.viejo ? "#9a9184" : "#1f5f8b", fillOpacity: 0.95,
    }).bindTooltip(el("span", { textContent: `${s.nombre}: ${metros(s.altura)}` })).addTo(capaEstaciones);

    return el("li", { className: "estacion", dataset: { viejo: String(s.viejo) } },
      el("div", { className: "estacion-nombre", textContent: s.nombre }), datos);
  }
}

function pronostico(estado) {
  const p = estado.pronostico_san_fernando;
  const caja = document.getElementById("pronostico");
  if (!p) { caja.textContent = "Sin pronóstico del INA disponible."; return; }
  caja.replaceChildren(
    el("div", {}, "Pico esperado ", el("b", { textContent: metros(p.max_main) })),
    el("div", { textContent: `el ${hora(p.ts_max)} · peor escenario (p95): ${metros(p.max_p95)}` }),
    el("p", { className: "nota", textContent: "Modelo INA. Referencia Prefectura: alerta 3,00 m · evacuación 3,50 m (equivalencia de escalas a confirmar)." }),
  );
}

function pie(estado) {
  document.getElementById("aviso-legal").textContent = estado.aviso_legal;
  const atraso = Date.now() - new Date(estado.generado).getTime();
  document.getElementById("actualizado").textContent = atraso > ESTADO_VIEJO_MS
    ? `⚠ Datos sin actualizar desde ${hora(estado.generado)}`
    : `Actualizado ${hora(estado.generado)}`;
  document.getElementById("fuentes").replaceChildren(...Object.entries(estado.fuentes).map(([n, f]) =>
    el("li", { textContent: `${f.ok ? "●" : "✕"} ${n}`, title: f.error || "ok", dataset: { ok: String(f.ok) } })));
}

// ── El río ahora: cifra principal, frase en lenguaje de observación y gráfico ──
const VERSION_SERIE = 1;
const NOMBRE_EST = { SFER: "San Fernando", BSAS: "Buenos Aires", LPLA: "La Plata" };
const TENDENCIA_HORAS = 3;
const UMBRAL_ESTABLE_M = 0.05;
const DATO_VIEJO_MS = 3 * 3_600_000;
let serieActual = null;
let estActual = "SFER";

const decimal = (v) => Math.abs(v).toFixed(2).replace(".", ",");
const conSignoAR = (v) => `${v >= 0 ? "+" : "−"}${decimal(v)}`;

function valorHace(serie, horas) {
  const [tsUlt] = serie.at(-1);
  const objetivo = new Date(tsUlt).getTime() - horas * 3_600_000;
  return serie.findLast(([ts]) => new Date(ts).getTime() <= objetivo)?.[1] ?? null;
}

function fraseTendencia(residuos) {
  const previo = valorHace(residuos, TENDENCIA_HORAS);
  if (previo == null) return "";
  const delta = residuos.at(-1)[1] - previo;
  if (Math.abs(delta) < UMBRAL_ESTABLE_M) return ` y se mantiene estable en las últimas ${TENDENCIA_HORAS} h`;
  const verbo = delta > 0 ? "viene subiendo" : "viene bajando";
  return ` y ${verbo} (${delta > 0 ? "+" : "−"}${decimal(delta)} m en las últimas ${TENDENCIA_HORAS} h)`;
}

function frasePronostico(prono) {
  if (!prono?.length) return "";
  const pico = prono.reduce((a, b) => (b[1] > a[1] ? b : a));
  return ` El INA pronostica una altura máxima de ${pico[1].toFixed(2).replace(".", ",")} m (escala del mareógrafo) el ${hora(pico[0])}.`;
}

function pintarRio() {
  const est = serieActual?.estaciones?.[estActual];
  const residuos = est?.residuo ?? [];
  document.getElementById("rio-estacion").textContent = NOMBRE_EST[estActual];
  const cifra = document.getElementById("rio-residuo");
  const frase = document.getElementById("rio-frase");
  const prono = estActual === "SFER" ? serieActual?.pronostico_sfer : [];
  if (!serieActual) return; // todavía cargando: se mantiene el texto inicial
  Grafico.dibujar(document.getElementById("grafico"), est, prono, new Date(serieActual.generado).getTime());
  if (!residuos.length) {
    cifra.textContent = "—";
    delete cifra.dataset.signo;
    frase.textContent = "Sin datos recientes del mareógrafo.";
    return;
  }
  const [ts, r] = residuos.at(-1);
  cifra.textContent = `${conSignoAR(r)} m`;
  cifra.dataset.signo = r >= 0 ? "sube" : "baja";
  const posicion = r >= 0 ? "por encima" : "por debajo";
  const viejo = Date.now() - new Date(ts).getTime() > DATO_VIEJO_MS ? ` (último dato: ${hora(ts)})` : "";
  frase.textContent = `En ${NOMBRE_EST[estActual]} el río está ${decimal(r)} m ${posicion} de la marea astronómica`
    + `${fraseTendencia(residuos)}.${viejo}${prono?.length ? frasePronostico(prono) : ""}`;
}

for (const boton of document.querySelectorAll(".rio-tabs button")) {
  boton.addEventListener("click", () => {
    estActual = boton.dataset.est;
    for (const b of document.querySelectorAll(".rio-tabs button")) b.setAttribute("aria-pressed", String(b === boton));
    pintarRio();
  });
}

async function refrescarRio() {
  try {
    const serie = await cargarJSON("data/serie.json");
    if (serie.version !== VERSION_SERIE) throw new Error(`versión de serie ${serie.version}`);
    serieActual = serie;
    pintarRio();
  } catch (err) {
    document.getElementById("rio-residuo").textContent = "—";
    document.getElementById("rio-frase").textContent = `No se pudo cargar la serie del río (${err.message}). Reintentando…`;
  }
}

let geoZonas = null;
async function refrescar() {
  refrescarRio();
  try {
    geoZonas ??= await cargarJSON("data/zonas.geojson");
    const estado = await cargarJSON("data/estado.json");
    if (estado.version !== VERSION_ESQUEMA) {
      throw new Error(`versión de estado ${estado.version ?? "sin versión"}, el mapa espera ${VERSION_ESQUEMA}`);
    }
    pintarZonas(geoZonas, estado);
    listaZonas(estado);
    estaciones(estado);
    pronostico(estado);
    pie(estado);
  } catch (err) {
    document.getElementById("actualizado").textContent = `No se pudo cargar el estado (${err.message}). Reintentando…`;
  }
}

refrescar();
setInterval(refrescar, REFRESCO_MS);
