import { BUSINESS_COLUMNS } from "/static/js/constants.js";

export function renderColumns({ usedEl, excludedEl, response }) {
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
  if (!usedEl.children.length) usedEl.textContent = "Нет данных.";
  if (!excludedEl.children.length) excludedEl.textContent = "Нет исключённых полей.";
}
