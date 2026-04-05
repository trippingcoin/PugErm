import { BUSINESS_COLUMNS } from "/static/js/constants.js";
import { t } from "/static/js/i18n.js";

export function renderColumns({ usedEl, excludedEl, response, lang = "ru" }) {
  usedEl.innerHTML = "";
  excludedEl.innerHTML = "";
  const attrs = (response.records?.[0]?.attributes) || (response.shortlist?.[0]?.attributes) || {};
  BUSINESS_COLUMNS.filter(c => c in attrs).forEach(c => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = c;
    usedEl.appendChild(chip);
  });

  (response.meta?.excluded_columns || []).forEach(c => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = c;
    excludedEl.appendChild(chip);
  });
  if (!usedEl.children.length) usedEl.textContent = t("no_data", lang);
  if (!excludedEl.children.length) excludedEl.textContent = t("no_excluded_fields", lang);
}
