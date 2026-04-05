import { riskClass, scoreClass } from "/static/js/utils.js";
import { riskLabel, t } from "/static/js/i18n.js";

export function renderShortlist({ el, shortlist, onSelect, onDownloadPdf, lang = "ru" }) {
  el.innerHTML = "";
  if (!shortlist.length) {
    el.textContent = t("no_shortlist", lang);
    return;
  }

  shortlist.forEach(item => {
    const attrs = item.attributes || {};
    const pos = (item.explanation?.positive || []).slice(0, 2).join(" · ");
    const neg = (item.explanation?.negative || []).slice(0, 1).join(" · ");
    const failedCount = (item.compliance_flags || []).filter(f => !f.passed).length;
    const card = document.createElement("div");
    card.className = "short-item";
    card.style.cursor = "pointer";
    card.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        <strong>${t("rank", lang)} #${item.rank} | ID: ${item.id}</strong>
        <span class="score-badge ${scoreClass(item.score)}">${item.score.toFixed(1)}</span>
        <span class="risk-badge ${riskClass(item.risk_level)}">${riskLabel(item.risk_level, lang)}</span>
        ${item.recommended ? `<span class="score-badge score-high">✓ ${t("recommended", lang)}</span>` : ""}
        ${failedCount > 0 ? `<span class="score-badge score-low">⚠ ${failedCount} ${t("flags_count", lang)}</span>` : ""}
        <button class="ghost short-pdf-btn" type="button" data-pdf-id="${item.id}" style="padding:4px 10px;font-size:11px;">PDF</button>
      </div>
      <span><b>${t("region_label", lang)}:</b> ${attrs["Область"] || "—"} | <b>${t("amount", lang)}:</b> ${attrs["Причитающая сумма"] || "—"}</span>
      ${pos ? `<span style="color:var(--green)">▲ ${pos}</span>` : ""}
      ${neg ? `<span style="color:var(--red)">▼ ${neg}</span>` : ""}
    `;
    card.querySelector(".short-pdf-btn")?.addEventListener("click", evt => {
      evt.stopPropagation();
      onDownloadPdf(item.id);
    });
    card.addEventListener("click", () => onSelect(item));
    el.appendChild(card);
  });
}
