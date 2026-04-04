import { REGION_LABELS } from "/static/js/constants.js";
import { normalizeRegionName, regionNameFromRecord, scoreClass, scoreToColor } from "/static/js/utils.js";

// GeoJSON source: Simplemaps admin-1 boundaries (CC BY 4.0).
const GEOJSON_URL = "/static/data/kz_admin1.geojson";
const VIEWBOX = { width: 1000, height: 560, padding: 20 };
const EXCLUDED_FEATURE_IDS = new Set(["KZ71", "KZ75", "KZ79"]);

let cachedGeo = null;
let geoPromise = null;
let geoError = null;

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
  return (lon, lat) => {
    const x = ((lon - bbox.minLon) / w) * (width - padding * 2) + padding;
    const y = ((bbox.maxLat - lat) / h) * (height - padding * 2) + padding;
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

export function renderKazakhstanMap({
  mapEl,
  legendEl,
  statsEl,
  activeRegionEl,
  records,
  fairness,
  selectedRegionNorm,
  selectedRegionLabel,
  onRegionClick,
}) {
  if (!mapEl || !legendEl || !statsEl) return;
  mapEl.innerHTML = "";
  statsEl.innerHTML = "";

  const stats = (records && records.length)
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
    mapEl.textContent = "Нет региональных данных.";
    legendEl.textContent = "";
    return;
  }

  if (geoError) {
    mapEl.textContent = "Не удалось загрузить карту.";
    legendEl.textContent = "";
    return;
  }

  if (!cachedGeo) {
    mapEl.textContent = "Загрузка карты...";
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
      }))
      .catch(() => {
        mapEl.textContent = "Не удалось загрузить карту.";
      });
    return;
  }

  const svgNs = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("viewBox", `0 0 ${VIEWBOX.width} ${VIEWBOX.height}`);
  svg.setAttribute("class", "kz-map-svg");
  mapEl.appendChild(svg);

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

  features.forEach(feature => {
    const rawName = feature.properties?.name || "";
    const norm = normalizeRegionName(rawName);
    const s = statsByRegion.get(norm);
    const labelText = REGION_LABELS[norm] || rawName;
    const path = document.createElementNS(svgNs, "path");
    path.setAttribute("d", buildPath(feature.geometry, project));
    path.setAttribute("fill", s ? scoreToColor(s.mean) : "#334155");
    path.setAttribute("opacity", s ? "1" : "0.6");
    path.setAttribute("fill-rule", "evenodd");
    path.setAttribute("class", "kz-area" + (selectedRegionNorm === norm ? " active" : "") + (s ? "" : " muted"));
    path.setAttribute("title", s ? `${s.region}: ${s.mean.toFixed(1)} (n=${s.count})` : `${labelText}: нет данных`);
    if (s) {
      path.addEventListener("click", () => onRegionClick(s));
    }
    svg.appendChild(path);

    const labelPos = labelPoint(feature.geometry, project);
    if (labelPos) {
      const label = document.createElementNS(svgNs, "text");
      label.setAttribute("x", labelPos[0].toFixed(1));
      label.setAttribute("y", labelPos[1].toFixed(1));
      label.setAttribute("class", "kz-label");
      label.textContent = labelText;
      svg.appendChild(label);
    }
  });

  stats.forEach(s => {
    const row = document.createElement("div");
    row.className = "short-item";
    row.style.cursor = "pointer";
    row.innerHTML = `
      <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;">
        <strong>${s.region}</strong>
        <span class="score-badge ${scoreClass(s.mean)}">${s.mean.toFixed(1)}</span>
      </div>
      <span>Заявок: ${s.count}</span>
    `;
    row.addEventListener("click", () => onRegionClick(s));
    statsEl.appendChild(row);
  });

  activeRegionEl.textContent = selectedRegionLabel ? `Выбран регион: ${selectedRegionLabel}` : "Все регионы";
  legendEl.innerHTML = `<span>Низкий скор</span><div class="legend-bar"></div><span>Высокий скор</span><span style="color:var(--text-muted)">Серый: нет данных</span>`;
}
