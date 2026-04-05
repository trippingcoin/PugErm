import { BUSINESS_COLUMNS } from "/static/js/constants.js";
import { riskClass, scoreClass } from "/static/js/utils.js";
import { riskLabel, t } from "/static/js/i18n.js";

const COL_LABELS = {
  rank: { ru: "Ранг", kz: "Ранг" },
  id: { ru: "ID", kz: "ID" },
  score: { ru: "Скор", kz: "Скор" },
  decision: { ru: "Решение", kz: "Шешім" },
  risk_level: { ru: "Риск", kz: "Тәуекел" },
  actions: { ru: "Действия", kz: "Әрекеттер" },
};

export function renderRecordsTable({ headEl, bodyEl, records, total, page, pageSize, onSelect, onDownloadPdf, lang = "ru" }) {
  headEl.innerHTML = "";
  bodyEl.innerHTML = "";
  if (!records.length) return;

  const attrKeys = Object.keys(records[0].attributes || {});
  const visibleAttrs = BUSINESS_COLUMNS.filter(c => attrKeys.includes(c));
  const cols = ["rank", "id", "score", "decision", "risk_level", ...visibleAttrs, "actions"];

  const headerRow = document.createElement("tr");
  cols.forEach(col => {
    const th = document.createElement("th");
    th.textContent = COL_LABELS[col]?.[lang] || col;
    headerRow.appendChild(th);
  });
  headEl.appendChild(headerRow);

  records.forEach(record => {
    const row = document.createElement("tr");
    row.addEventListener("click", () => onSelect(record));
    cols.forEach(col => {
      const td = document.createElement("td");
      if (col === "rank") td.textContent = `#${record.rank}`;
      else if (col === "id") td.textContent = record.id;
      else if (col === "score") td.innerHTML = `<span class="score-badge ${scoreClass(record.score)}">${record.score.toFixed(1)}</span>`;
      else if (col === "decision") td.textContent = record.decision || "";
      else if (col === "risk_level") td.innerHTML = `<span class="risk-badge ${riskClass(record.risk_level)}">${riskLabel(record.risk_level, lang)}</span>`;
      else if (col === "actions") {
        td.innerHTML = `<button class="ghost row-pdf-btn" type="button" style="padding:3px 8px;font-size:11px;">PDF</button>`;
        td.querySelector(".row-pdf-btn")?.addEventListener("click", evt => {
          evt.stopPropagation();
          onDownloadPdf(record.id);
        });
      } else td.textContent = record.attributes?.[col] ?? "";
      row.appendChild(td);
    });
    bodyEl.appendChild(row);
  });

  return {
    totalPages: Math.max(1, Math.ceil((Number(total) || records.length) / Number(pageSize || 1))),
    total,
    page,
  };
}
