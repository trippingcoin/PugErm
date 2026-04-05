import { t } from "/static/js/i18n.js";

export function renderSummary({ el, meta, sourceRecords, lang = "ru" }) {
  el.innerHTML = "";
  if (!meta) return;
  const recommended = sourceRecords.filter(r => r.recommended).length;
  const highRisk = sourceRecords.filter(r => r.risk_level === "high").length;
  const ndcg = meta.ranking_metrics?.ndcg_at_20_model;
  const lift = meta.ranking_metrics?.topk_gain_lift_pct_vs_fcfs;

  const items = [
    { label: t("summary_applicants", lang), value: meta.rows },
    { label: t("summary_mean", lang), value: meta.score_mean?.toFixed(1) },
    { label: t("summary_recommended", lang), value: recommended },
    { label: t("summary_high_risk", lang), value: highRisk },
    { label: "NDCG@20", value: ndcg != null ? ndcg : "—" },
    { label: t("summary_lift", lang), value: lift != null ? `+${lift}%` : "—" },
  ];

  items.forEach(item => {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<span>${item.label}</span><strong>${item.value}</strong>`;
    el.appendChild(card);
  });
}

export function renderRankingMetrics({ el, metrics, lang = "ru" }) {
  if (!el) return;
  el.innerHTML = "";
  if (!metrics) return;
  const items = [
    { label: t("metrics_model_ndcg", lang), value: metrics.ndcg_at_20_model },
    { label: t("metrics_base_ndcg", lang), value: metrics.ndcg_at_20_baseline_fcfs },
    { label: t("metrics_model_precision", lang), value: metrics.precision_at_20_model },
    { label: t("metrics_base_precision", lang), value: metrics.precision_at_20_baseline_fcfs },
    { label: t("metrics_lift", lang), value: metrics.topk_gain_lift_pct_vs_fcfs != null ? `+${metrics.topk_gain_lift_pct_vs_fcfs}` : "—" },
  ];
  items.forEach(item => {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<span>${item.label}</span><strong>${item.value ?? "—"}</strong>`;
    el.appendChild(card);
  });
}
