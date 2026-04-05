import { REGION_LABELS } from "/static/js/constants.js";
import { normalizeRegionName, regionNameFromRecord, scoreClass } from "/static/js/utils.js";
import { t } from "/static/js/i18n.js";

// GeoJSON source: Simplemaps admin-1 boundaries (CC BY 4.0).
const GEOJSON_URL = "/static/data/kz_admin1.geojson";
const VIEWBOX = { width: 1000, height: 560, padding: 20 };
const EXCLUDED_FEATURE_IDS = new Set(["KZ71", "KZ75", "KZ79"]);

let cachedGeo = null;
let geoPromise = null;
let geoError = null;

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function createMapControls() {
  const controls = document.createElement("div");
  controls.className = "map-controls";
  controls.innerHTML = `
    <button type="button" class="map-control-btn" data-action="zoom-in" aria-label="Zoom in">+</button>
    <button type="button" class="map-control-btn" data-action="zoom-out" aria-label="Zoom out">-</button>
    <button type="button" class="map-control-btn" data-action="reset" aria-label="Reset zoom">Reset</button>
  `;
  return controls;
}

function attachPanZoom({ mapEl, svg, viewport }) {
  let scale = 1;
  let tx = 0;
  let ty = 0;
  let dragging = false;
  let startX = 0;
  let startY = 0;
  let startTx = 0;
  let startTy = 0;

  const applyTransform = () => {
    viewport.setAttribute("transform", `translate(${tx.toFixed(1)} ${ty.toFixed(1)}) scale(${scale.toFixed(3)})`);
  };

  const zoomAt = (nextScale, clientX, clientY) => {
    const rect = svg.getBoundingClientRect();
    const pointerX = ((clientX - rect.left) / rect.width) * VIEWBOX.width;
    const pointerY = ((clientY - rect.top) / rect.height) * VIEWBOX.height;
    const prevScale = scale;
    scale = clamp(nextScale, 1, 6);
    if (scale === prevScale) return;
    tx = pointerX - ((pointerX - tx) / prevScale) * scale;
    ty = pointerY - ((pointerY - ty) / prevScale) * scale;
    applyTransform();
  };

  const reset = () => {
    scale = 1;
    tx = 0;
    ty = 0;
    applyTransform();
  };

  svg.addEventListener("wheel", event => {
    event.preventDefault();
    const factor = event.deltaY < 0 ? 1.14 : 0.88;
    zoomAt(scale * factor, event.clientX, event.clientY);
  }, { passive: false });

  svg.addEventListener("pointerdown", event => {
    if (scale <= 1) return;
    dragging = true;
    startX = event.clientX;
    startY = event.clientY;
    startTx = tx;
    startTy = ty;
    svg.setPointerCapture(event.pointerId);
    mapEl.classList.add("dragging");
  });

  svg.addEventListener("pointermove", event => {
    if (!dragging) return;
    tx = startTx + ((event.clientX - startX) / svg.clientWidth) * VIEWBOX.width;
    ty = startTy + ((event.clientY - startY) / svg.clientHeight) * VIEWBOX.height;
    applyTransform();
  });

  const stopDrag = event => {
    if (!dragging) return;
    dragging = false;
    mapEl.classList.remove("dragging");
    try {
      svg.releasePointerCapture(event.pointerId);
    } catch (_) {
      // ignore capture release errors
    }
  };

  svg.addEventListener("pointerup", stopDrag);
  svg.addEventListener("pointerleave", stopDrag);
  svg.addEventListener("dblclick", () => reset());

  return { reset, zoomIn: () => zoomAt(scale * 1.2, svg.getBoundingClientRect().left + svg.clientWidth / 2, svg.getBoundingClientRect().top + svg.clientHeight / 2), zoomOut: () => zoomAt(scale * 0.84, svg.getBoundingClientRect().left + svg.clientWidth / 2, svg.getBoundingClientRect().top + svg.clientHeight / 2) };
}

async function loadGeo() {
  if (cachedGeo) return cachedGeo;
  if (geoPromise) return geoPromise;
  geoPromise = fetch(GEOJSON_URL)
    .then(res => {
      if (!res.ok) throw new Error(`GeoJSON load failed: ${res.status}`);
      return res.json();
    })
    .then(data => {
      cachedGeo = data;
      geoError = null;
      return data;
    })
    .catch(err => {
      geoError = err;
      geoPromise = null;
      throw err;
    });
  return geoPromise;
}

function forEachCoord(geometry, cb) {
  if (!geometry) return;
  if (geometry.type === "Polygon") {
    geometry.coordinates.forEach(ring => ring.forEach(([lon, lat]) => cb(lon, lat)));
  } else if (geometry.type === "MultiPolygon") {
    geometry.coordinates.forEach(poly => poly.forEach(ring => ring.forEach(([lon, lat]) => cb(lon, lat))));
  }
}

function computeBbox(features) {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;
  features.forEach(f => {
    forEachCoord(f.geometry, (lon, lat) => {
      if (lon < minLon) minLon = lon;
      if (lat < minLat) minLat = lat;
      if (lon > maxLon) maxLon = lon;
      if (lat > maxLat) maxLat = lat;
    });
  });
  return { minLon, minLat, maxLon, maxLat };
}

function makeProjector(bbox) {
  const { width, height, padding } = VIEWBOX;
  const w = Math.max(1, bbox.maxLon - bbox.minLon);
  const h = Math.max(1, bbox.maxLat - bbox.minLat);
  const scale = Math.min((width - padding * 2) / w, (height - padding * 2) / h);
  const xOffset = padding + (width - padding * 2 - w * scale) / 2;
  const yOffset = padding + (height - padding * 2 - h * scale) / 2;
  return (lon, lat) => {
    const x = (lon - bbox.minLon) * scale + xOffset;
    const y = (bbox.maxLat - lat) * scale + yOffset;
    return [x, y];
  };
}

function buildPath(geometry, project) {
  const parts = [];
  const addRing = ring => {
    if (!ring || !ring.length) return;
    const [x0, y0] = project(ring[0][0], ring[0][1]);
    let d = `M${x0.toFixed(1)},${y0.toFixed(1)}`;
    for (let i = 1; i < ring.length; i += 1) {
      const [x, y] = project(ring[i][0], ring[i][1]);
      d += `L${x.toFixed(1)},${y.toFixed(1)}`;
    }
    d += "Z";
    parts.push(d);
  };
  if (!geometry) return "";
  if (geometry.type === "Polygon") {
    geometry.coordinates.forEach(addRing);
  } else if (geometry.type === "MultiPolygon") {
    geometry.coordinates.forEach(poly => poly.forEach(addRing));
  }
  return parts.join(" ");
}

function polygonArea(points) {
  let area = 0;
  for (let i = 0; i < points.length; i += 1) {
    const [x1, y1] = points[i];
    const [x2, y2] = points[(i + 1) % points.length];
    area += x1 * y2 - x2 * y1;
  }
  return area / 2;
}

function polygonCentroid(points) {
  const area = polygonArea(points);
  if (!area) {
    const avg = points.reduce((acc, [x, y]) => [acc[0] + x, acc[1] + y], [0, 0]);
    return [avg[0] / points.length, avg[1] / points.length];
  }
  let cx = 0;
  let cy = 0;
  for (let i = 0; i < points.length; i += 1) {
    const [x1, y1] = points[i];
    const [x2, y2] = points[(i + 1) % points.length];
    const f = x1 * y2 - x2 * y1;
    cx += (x1 + x2) * f;
    cy += (y1 + y2) * f;
  }
  return [cx / (6 * area), cy / (6 * area)];
}

function labelPoint(geometry, project) {
  let best = null;
  let bestArea = 0;
  const consider = ring => {
    if (!ring || ring.length < 3) return;
    const pts = ring.map(([lon, lat]) => project(lon, lat));
    const area = Math.abs(polygonArea(pts));
    if (area > bestArea) {
      bestArea = area;
      best = pts;
    }
  };
  if (!geometry) return null;
  if (geometry.type === "Polygon") {
    geometry.coordinates.forEach(consider);
  } else if (geometry.type === "MultiPolygon") {
    geometry.coordinates.forEach(poly => poly.forEach(consider));
  }
  if (!best) return null;
  return polygonCentroid(best);
}

function regionStats(records) {
  const map = new Map();
  records.forEach(r => {
    const raw = regionNameFromRecord(r);
    const norm = normalizeRegionName(raw);
    if (!norm) return;
    if (!map.has(norm)) map.set(norm, { raw: String(raw), scores: [] });
    map.get(norm).scores.push(Number(r.score || 0));
  });
  return Array.from(map.entries()).map(([norm, v]) => {
    const count = v.scores.length;
    const mean = count ? v.scores.reduce((a, b) => a + b, 0) / count : 0;
    return { norm, region: v.raw, count, mean };
  });
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function rgbToHex(r, g, b) {
  return `#${[r, g, b].map(v => Math.round(v).toString(16).padStart(2, "0")).join("")}`;
}

function gradientColor(score, min, max) {
  const safeMin = Number.isFinite(min) ? min : 0;
  const safeMax = Number.isFinite(max) ? max : 100;
  const span = Math.max(1e-6, safeMax - safeMin);
  const t = Math.max(0, Math.min(1, (Number(score || 0) - safeMin) / span));
  const stops = [
    { t: 0, color: [239, 68, 68] },
    { t: 0.5, color: [245, 158, 11] },
    { t: 1, color: [16, 185, 129] },
  ];
  let left = stops[0];
  let right = stops[stops.length - 1];
  for (let i = 1; i < stops.length; i += 1) {
    if (t <= stops[i].t) {
      left = stops[i - 1];
      right = stops[i];
      break;
    }
  }
  const localT = (t - left.t) / Math.max(1e-6, right.t - left.t);
  return rgbToHex(
    lerp(left.color[0], right.color[0], localT),
    lerp(left.color[1], right.color[1], localT),
    lerp(left.color[2], right.color[2], localT),
  );
}

export function renderKazakhstanMap({
  mapEl,
  legendEl,
  statsEl,
  activeRegionEl,
  records,
  regionStats: explicitStats,
  fairness,
  selectedRegionNorm,
  selectedRegionLabel,
  onRegionClick,
  lang = "ru",
}) {
  if (!mapEl || !legendEl || !statsEl) return;
  mapEl.innerHTML = "";
  statsEl.innerHTML = "";

  const stats = (explicitStats && explicitStats.length)
    ? explicitStats.map(g => ({
      norm: normalizeRegionName(g.region),
      region: g.region,
      count: g.count,
      mean: g.mean,
      median: g.median,
    }))
    : (records && records.length)
      ? regionStats(records)
      : (fairness?.groups || []).map(g => ({
        norm: normalizeRegionName(g.group),
        region: g.group,
        count: g.count,
        mean: g.mean_score,
      }));
  stats.sort((a, b) => b.mean - a.mean);
  const statsByRegion = new Map(stats.map(s => [s.norm, s]));

  if (!stats.length) {
    mapEl.textContent = t("map_no_data", lang);
    legendEl.textContent = "";
    return;
  }

  if (geoError) {
    mapEl.textContent = t("map_load_error", lang);
    legendEl.textContent = "";
    return;
  }

  if (!cachedGeo) {
    mapEl.textContent = t("map_loading", lang);
    legendEl.textContent = "";
    loadGeo()
      .then(() => renderKazakhstanMap({
        mapEl,
        legendEl,
        statsEl,
        activeRegionEl,
        records,
        fairness,
        selectedRegionNorm,
        selectedRegionLabel,
        onRegionClick,
        lang,
      }))
      .catch(() => {
        mapEl.textContent = t("map_load_error", lang);
      });
    return;
  }

  const svgNs = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("viewBox", `0 0 ${VIEWBOX.width} ${VIEWBOX.height}`);
  svg.setAttribute("class", "kz-map-svg");
  mapEl.appendChild(svg);
  const viewport = document.createElementNS(svgNs, "g");
  viewport.setAttribute("class", "kz-map-viewport");
  svg.appendChild(viewport);

  const features = (cachedGeo.features || []).filter(f => {
    const id = f?.properties?.id;
    const name = f?.properties?.name || "";
    if (!f?.geometry) return false;
    if (EXCLUDED_FEATURE_IDS.has(id)) return false;
    if (name.toLowerCase().includes("(city)")) return false;
    return true;
  });

  const bbox = computeBbox(features);
  const project = makeProjector(bbox);

  const meanValues = stats.map(s => Number(s.mean)).filter(Number.isFinite);
  const meanMin = meanValues.length ? Math.min(...meanValues) : 0;
  const meanMax = meanValues.length ? Math.max(...meanValues) : 100;
  let missingRegions = 0;

  features.forEach(feature => {
    const rawName = feature.properties?.name || "";
    const norm = normalizeRegionName(rawName);
    const s = statsByRegion.get(norm);
    const labelText = REGION_LABELS[norm] || rawName;
    const path = document.createElementNS(svgNs, "path");
    path.setAttribute("d", buildPath(feature.geometry, project));
    path.setAttribute("fill", s ? gradientColor(s.mean, meanMin, meanMax) : "#334155");
    path.setAttribute("opacity", s ? "1" : "0.6");
    path.setAttribute("fill-rule", "evenodd");
    path.setAttribute("class", "kz-area" + (selectedRegionNorm === norm ? " active" : "") + (s ? "" : " muted"));
    path.setAttribute("title", s ? `${s.region}: ${s.mean.toFixed(1)} (n=${s.count})` : `${labelText}: нет данных`);
    if (s) {
      path.addEventListener("click", () => onRegionClick(s));
    } else {
      missingRegions += 1;
    }
    viewport.appendChild(path);

    const labelPos = labelPoint(feature.geometry, project);
    if (labelPos) {
      const label = document.createElementNS(svgNs, "text");
      label.setAttribute("x", labelPos[0].toFixed(1));
      label.setAttribute("y", labelPos[1].toFixed(1));
      label.setAttribute("class", "kz-label");
      label.textContent = labelText;
      viewport.appendChild(label);
    }
  });

  const controls = createMapControls();
  mapEl.appendChild(controls);
  controls.querySelector("[data-action='reset']").textContent = t("zoom_reset", lang);
  const interactions = attachPanZoom({ mapEl, svg, viewport });
  controls.querySelector("[data-action='zoom-in']")?.addEventListener("click", interactions.zoomIn);
  controls.querySelector("[data-action='zoom-out']")?.addEventListener("click", interactions.zoomOut);
  controls.querySelector("[data-action='reset']")?.addEventListener("click", interactions.reset);

  stats.forEach(s => {
    const row = document.createElement("div");
    row.className = "short-item";
    row.style.cursor = "pointer";
    row.innerHTML = `
      <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;">
        <strong>${s.region}</strong>
        <span class="score-badge ${scoreClass(s.mean)}">${s.mean.toFixed(1)}</span>
      </div>
      <span>${t("map_requests", lang)}: ${s.count}</span>
    `;
    row.addEventListener("click", () => onRegionClick(s));
    statsEl.appendChild(row);
  });

  activeRegionEl.textContent = selectedRegionLabel ? t("map_selected_region", lang, { region: selectedRegionLabel }) : t("all_regions", lang);
  const missingLabel = missingRegions > 0
    ? `<span style="color:var(--text-muted)">${t("map_grey", lang, { count: missingRegions })}</span>`
    : "";
  legendEl.innerHTML = `<span>${t("map_low", lang)}</span><div class="legend-bar"></div><span>${t("map_high", lang)}</span>${missingLabel}`;
}
