import { REGION_SHAPES } from "/static/js/constants.js";
import { normalizeRegionName, regionNameFromRecord, scoreClass, scoreToColor } from "/static/js/utils.js";

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

  const svgNs = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("viewBox", "0 0 1000 560");
  svg.setAttribute("class", "kz-map-svg");
  mapEl.appendChild(svg);

  Object.entries(REGION_SHAPES).forEach(([norm, shape]) => {
    const s = statsByRegion.get(norm);
    const path = document.createElementNS(svgNs, "polygon");
    path.setAttribute("points", shape.points);
    path.setAttribute("fill", s ? scoreToColor(s.mean) : "#334155");
    path.setAttribute("opacity", s ? "1" : "0.6");
    path.setAttribute("class", "kz-area" + (selectedRegionNorm === norm ? " active" : "") + (s ? "" : " muted"));
    path.setAttribute("title", s ? `${s.region}: ${s.mean.toFixed(1)} (n=${s.count})` : `${shape.label}: нет данных`);
    if (s) {
      path.addEventListener("click", () => onRegionClick(s));
    }
    svg.appendChild(path);

    const label = document.createElementNS(svgNs, "text");
    label.setAttribute("x", String(shape.lx));
    label.setAttribute("y", String(shape.ly));
    label.setAttribute("class", "kz-label");
    label.textContent = shape.label;
    svg.appendChild(label);
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
