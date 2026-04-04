import { scoreClass } from "/static/js/utils.js";

export function renderFairness({ el, fairness }) {
  el.innerHTML = "";
  if (!fairness?.groups?.length) {
    el.textContent = "Недостаточно данных.";
    return;
  }

  const gap = document.createElement("div");
  gap.className = "short-item";
  const gapColor = fairness.mean_score_gap > 15 ? "var(--red)" : fairness.mean_score_gap > 8 ? "var(--amber)" : "var(--green)";
  gap.innerHTML = `
    <strong>Fairness Check — ${fairness.protected_attribute}</strong>
    <span>Mean score gap: <b style="color:${gapColor}">${fairness.mean_score_gap.toFixed(2)}</b>
    ${fairness.mean_score_gap > 15 ? "⚠ Высокий дисбаланс по регионам" : fairness.mean_score_gap > 8 ? "~ Умеренный дисбаланс" : "✓ Дисбаланс в норме"}</span>
  `;
  el.appendChild(gap);

  fairness.groups.slice(0, 6).forEach(g => {
    const item = document.createElement("div");
    item.className = "short-item";
    const pct = Math.min(100, (g.mean_score / 100) * 100);
    item.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <strong>${g.group}</strong>
        <span class="score-badge ${scoreClass(g.mean_score)}">${g.mean_score.toFixed(1)}</span>
      </div>
      <div style="height:4px;background:var(--border);border-radius:2px;overflow:hidden;">
        <div style="height:100%;width:${pct}%;background:var(--teal);border-radius:2px;transition:width 0.5s;"></div>
      </div>
      <span style="font-size:10.5px;">n = ${g.count} | медиана = ${g.median_score.toFixed(1)}</span>
    `;
    el.appendChild(item);
  });
}
