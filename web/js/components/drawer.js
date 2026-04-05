import { buildNarrativeText, riskClass, scoreClass } from "/static/js/utils.js";
import { riskLabel, t } from "/static/js/i18n.js";

export function renderRecordExplanation({ explanationEl, record, currentLang }) {
  const bd = record.breakdown || {};
  const top = record.explanation?.top_features || [];
  const failed = (record.compliance_flags || []).filter(f => !f.passed);
  const pos = record.explanation?.positive || [];
  const neg = record.explanation?.negative || [];
  const narrative = buildNarrativeText(record, currentLang);

  const components = [
    { label: "ML Score (×0.60)", value: bd.ml_score, color: "var(--teal)" },
    { label: "Compliance (×0.20)", value: bd.compliance_score, color: "var(--blue)" },
    { label: "Growth (×0.12)", value: bd.growth_score, color: "var(--green)" },
    { label: "Fraud Safety (×0.08)", value: bd.fraud_safety_score, color: "var(--amber)" },
  ];
  const breakdownHtml = components.map(c => {
    const val = Number(c.value || 0);
    return `
      <div style="margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:3px;font-size:11px;color:var(--text-secondary);">
          <span>${c.label}</span><span style="color:${c.color};font-weight:700;">${val.toFixed(1)}</span>
        </div>
        <div style="height:5px;background:var(--border);border-radius:3px;">
          <div style="height:100%;width:${val}%;background:${c.color};border-radius:3px;transition:width 0.6s;"></div>
        </div>
      </div>`;
  }).join("");

  const shapHtml = top.slice(0, 6).map(f => {
    const v = f.contribution;
    const color = v > 0 ? "var(--green)" : "var(--red)";
    const pct = Math.min(100, Math.abs(v) * 2);
    return `
      <div style="margin-bottom:6px;">
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-secondary);margin-bottom:2px;">
          <span>${f.feature}</span>
          <span style="color:${color};font-weight:700;">${v > 0 ? "+" : ""}${v.toFixed(3)}</span>
        </div>
        <div style="height:4px;background:var(--border);border-radius:2px;">
          <div style="height:100%;width:${pct}%;background:${color};border-radius:2px;margin-left:${v < 0 ? "auto" : "0"};"></div>
        </div>
      </div>`;
  }).join("");

  explanationEl.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px;">
      <strong style="font-size:15px;">ID: ${record.id}</strong>
      <span class="score-badge ${scoreClass(record.score)}" style="font-size:14px;">${record.score.toFixed(1)}</span>
      <span class="risk-badge ${riskClass(record.risk_level)}">${riskLabel(record.risk_level, currentLang)}</span>
      ${record.recommended ? `<span class="score-badge score-high">✓ ${t("recommended", currentLang)}</span>` : `<span class="score-badge score-mid">${t("recommended_review", currentLang)}</span>`}
    </div>
    <span style="font-size:11px;color:var(--text-muted);">Ранг #${record.rank} | ${record.decision || "—"}</span>

    <div style="margin-top:12px;">
      <div style="font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">${t("breakdown_title", currentLang)}</div>
      ${breakdownHtml}
    </div>

    <div style="margin-top:4px;">
      <div style="font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">${t("shap_title", currentLang)}</div>
      ${shapHtml || '<span style="color:var(--text-muted);font-size:12px;">SHAP данные не доступны</span>'}
    </div>

    <div style="margin-top:10px;padding:10px 12px;background:var(--bg-elevated);border-radius:var(--radius-sm);border:1px solid var(--border);">
      <div style="font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px;">${t("text_explanation", currentLang, { lang: currentLang.toUpperCase() })}</div>
      <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;white-space:pre-line;">${narrative}</div>
    </div>

    ${pos.length ? `<div style="margin-top:8px;"><div style="font-size:11px;color:var(--green);font-weight:700;margin-bottom:4px;">${t("positive_factors", currentLang)}</div>${pos.map(p => `<div style="font-size:12px;color:var(--text-secondary);margin-bottom:3px;">${p}</div>`).join("")}</div>` : ""}
    ${neg.length ? `<div style="margin-top:8px;"><div style="font-size:11px;color:var(--red);font-weight:700;margin-bottom:4px;">${t("negative_factors", currentLang)}</div>${neg.map(n => `<div style="font-size:12px;color:var(--text-secondary);margin-bottom:3px;">${n}</div>`).join("")}</div>` : ""}

    ${failed.length ? `
    <div style="margin-top:12px;padding:10px 12px;background:var(--red-dim);border:1px solid rgba(248,113,113,0.25);border-radius:var(--radius-sm);">
      <div style="font-size:11px;font-weight:700;color:var(--red);margin-bottom:6px;">${t("compliance_violations", currentLang, { count: failed.length })}</div>
      ${failed.map(f => `<div style="font-size:11px;color:var(--text-secondary);margin-bottom:3px;">[${f.severity.toUpperCase()}] <b>${f.code}</b>: ${f.message}</div>`).join("")}
    </div>` : `<div style="padding:8px 12px;background:var(--green-dim);border-radius:var(--radius-sm);font-size:11px;color:var(--green);">${t("no_violations", currentLang)}</div>`}
  `;
}
