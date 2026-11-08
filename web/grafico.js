"use strict";

// Gráfico SVG de altura del río: medida, marea astronómica y pronóstico INA.
// Sin librerías: es una sola serie temporal y así la página pesa poco.

const Grafico = (() => {
  const NS = "http://www.w3.org/2000/svg";
  const W = 800, H = 300, M = { izq: 44, der: 12, arr: 14, aba: 30 };
  const fmtEje = new Intl.DateTimeFormat("es-AR", {
    weekday: "short", hour: "2-digit", timeZone: "America/Argentina/Buenos_Aires",
  });
  const horaAR = new Intl.DateTimeFormat("es-AR", {
    hour: "numeric", hour12: false, timeZone: "America/Argentina/Buenos_Aires",
  });

  function nodo(tag, attrs = {}, texto) {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (texto != null) n.textContent = texto;
    return n;
  }

  const puntos = (serie) => serie.map(([ts, v]) => [new Date(ts).getTime(), v]).filter(([t, v]) => !Number.isNaN(t) && v != null);

  function camino(pts, x, y) {
    return pts.map(([t, v], i) => `${i ? "L" : "M"}${x(t).toFixed(1)},${y(v).toFixed(1)}`).join("");
  }

  function escalas(series, ahora) {
    const todos = series.flat();
    const ts = todos.map(([t]) => t);
    const vs = todos.map(([, v]) => v);
    const t0 = Math.min(...ts, ahora), t1 = Math.max(...ts, ahora);
    const v0 = Math.floor(Math.min(...vs, 0) * 2) / 2, v1 = Math.ceil(Math.max(...vs) * 2) / 2 + 0.25;
    const x = (t) => M.izq + ((t - t0) / (t1 - t0 || 1)) * (W - M.izq - M.der);
    const y = (v) => H - M.aba - ((v - v0) / (v1 - v0 || 1)) * (H - M.arr - M.aba);
    return { x, y, t0, t1, v0, v1 };
  }

  function ejes(svg, e) {
    for (let v = e.v0; v <= e.v1 + 1e-9; v += 0.5) {
      svg.append(nodo("line", { x1: M.izq, x2: W - M.der, y1: e.y(v), y2: e.y(v), class: "g-grilla" }));
      svg.append(nodo("text", { x: M.izq - 6, y: e.y(v) + 4, class: "g-eje", "text-anchor": "end" }, `${v.toFixed(1)} m`));
    }
    const hora = 3_600_000;
    for (let t = Math.ceil(e.t0 / hora) * hora; t <= e.t1; t += hora) {
      if (Number(horaAR.format(t)) % 12 !== 0) continue; // marcas a las 0 y 12 h de Argentina
      svg.append(nodo("line", { x1: e.x(t), x2: e.x(t), y1: M.arr, y2: H - M.aba, class: "g-grilla" }));
      svg.append(nodo("text", { x: e.x(t), y: H - 10, class: "g-eje", "text-anchor": "middle" }, fmtEje.format(t)));
    }
  }

  function dibujar(svg, est, prono, ahora) {
    svg.replaceChildren();
    const obs = puntos(est?.altura ?? []);
    const astro = puntos(est?.astronomica ?? []);
    const main = puntos((prono ?? []).map(([ts, m]) => [ts, m]));
    const banda = (prono ?? []).filter(([, , p05, p95]) => p05 != null && p95 != null)
      .map(([ts, , p05, p95]) => [new Date(ts).getTime(), p05, p95]);
    if (!obs.length) {
      svg.append(nodo("text", { x: W / 2, y: H / 2, class: "g-vacio", "text-anchor": "middle" }, "Sin datos del mareógrafo"));
      return;
    }
    const e = escalas([obs, astro, main, banda.map(([t, a]) => [t, a]), banda.map(([t, , b]) => [t, b])], ahora);
    ejes(svg, e);
    if (banda.length) {
      const ida = banda.map(([t, , p95]) => [t, p95]);
      const vuelta = banda.map(([t, p05]) => [t, p05]).reverse();
      svg.append(nodo("path", { d: `${camino(ida, e.x, e.y)}${camino(vuelta, e.x, e.y).replace("M", "L")}Z`, class: "g-banda" }));
    }
    if (astro.length) svg.append(nodo("path", { d: camino(astro, e.x, e.y), class: "g-astro" }));
    if (main.length) svg.append(nodo("path", { d: camino(main, e.x, e.y), class: "g-prono" }));
    svg.append(nodo("path", { d: camino(obs, e.x, e.y), class: "g-obs" }));

    const [tu, vu] = obs.at(-1);
    svg.append(nodo("line", { x1: e.x(ahora), x2: e.x(ahora), y1: M.arr, y2: H - M.aba, class: "g-ahora" }));
    svg.append(nodo("text", { x: e.x(ahora) + 4, y: M.arr + 10, class: "g-eje" }, "ahora"));
    svg.append(nodo("circle", { cx: e.x(tu), cy: e.y(vu), r: 5, class: "g-punto" }));
    svg.append(nodo("text", { x: e.x(tu) - 8, y: e.y(vu) - 10, class: "g-valor", "text-anchor": "end" }, `${vu.toFixed(2)} m`));
  }

  return { dibujar };
})();
