export function renderSummary({ el, meta, sourceRecords }) {
  el.innerHTML = "";
  if (!meta) return;
  const recommended = sourceRecords.filter(r => r.recommended).length;
  const highRisk = sourceRecords.filter(r => r.risk_level === "high").length;
  const ndcg = meta.ranking_metrics?.ndcg_at_20_model;
  const lift = meta.ranking_metrics?.topk_gain_lift_pct_vs_fcfs;

  const items = [
    { label: "Заявителей", value: meta.rows },
    { label: "Скор среднее", value: meta.score_mean?.toFixed(1) },
    { label: "Рекомендованы", value: recommended },
    { label: "Высокий риск", value: highRisk },
    { label: "NDCG@20", value: ndcg != null ? ndcg : "—" },
    { label: "Lift vs FCFS%", value: lift != null ? `+${lift}%` : "—" },
  ];

  items.forEach(item => {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<span>${item.label}</span><strong>${item.value}</strong>`;
    el.appendChild(card);
  });
}

export function renderRankingMetrics({ el, metrics }) {
  if (!el) return;
  el.innerHTML = "";
  if (!metrics) return;
  const items = [
    { label: "NDCG@20 (наша модель)", value: metrics.ndcg_at_20_model },
    { label: "NDCG@20 (FCFS baseline)", value: metrics.ndcg_at_20_baseline_fcfs },
    { label: "Precision@20 (модель)", value: metrics.precision_at_20_model },
    { label: "Precision@20 (FCFS)", value: metrics.precision_at_20_baseline_fcfs },
    { label: "Lift vs FCFS, %", value: metrics.topk_gain_lift_pct_vs_fcfs != null ? `+${metrics.topk_gain_lift_pct_vs_fcfs}` : "—" },
  ];
  items.forEach(item => {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<span>${item.label}</span><strong>${item.value ?? "—"}</strong>`;
    el.appendChild(card);
  });
}
