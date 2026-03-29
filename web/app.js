const form = document.getElementById("score-form");
const fileInput = document.getElementById("file-input");
const shortlistInput = document.getElementById("shortlist-input");
const useSampleButton = document.getElementById("use-sample");

const statusEl = document.getElementById("status");
const summaryEl = document.getElementById("summary");
const globalFactorsEl = document.getElementById("global-factors");
const usedColumnsEl = document.getElementById("used-columns");
const excludedColumnsEl = document.getElementById("excluded-columns");
const shortlistEl = document.getElementById("shortlist");
const tableHead = document.querySelector("#records-table thead");
const tableBody = document.querySelector("#records-table tbody");

const BUSINESS_COLUMNS = [
  "Область",
  "Акимат",
  "Направление водства",
  "Наименование субсидирования",
  "Статус заявки",
  "Норматив",
  "Причитающая сумма",
  "Район хозяйства",
];

function humanizeMode(mode) {
  if (mode === "unsupervised_svd") return "Prototype ranking";
  if (mode === "supervised_classification") return "Supervised classification";
  if (mode === "supervised_regression") return "Supervised regression";
  return mode || "—";
}

function setStatus(message, tone = "info") {
  statusEl.textContent = message;
  statusEl.style.borderColor = tone === "error" ? "rgba(176, 74, 47, 0.8)" : "rgba(176, 74, 47, 0.4)";
  statusEl.style.color = tone === "error" ? "#8b2e20" : "#5c5c55";
}

function buildQuery() {
  const params = new URLSearchParams();
  if (shortlistInput.value.trim()) params.set("shortlist", shortlistInput.value.trim());
  const query = params.toString();
  return query ? `?${query}` : "";
}

async function submitScore(useSample = false) {
  setStatus("Запускаем ML‑скоринг...");
  const query = buildQuery();
  const options = { method: "POST" };

  if (!useSample && fileInput.files.length > 0) {
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    options.body = formData;
  }

  const response = await fetch(`/api/score${query}`, options);
  const data = await response.json();
  if (!response.ok) {
    const message = data && data.error ? data.error : "Ошибка скоринга";
    setStatus(message, "error");
    return;
  }
  renderResult(data);
  setStatus("Готово. Shortlist сформирован.");
}

function renderResult(data) {
  renderSummary(data.meta);
  renderGlobalFactors(data.global_factors || []);
  renderColumns(data);
  renderShortlist(data.shortlist || []);
  renderTable(data.records || []);
}

function renderSummary(meta) {
  summaryEl.innerHTML = "";
  if (!meta) return;
  const items = [
    { label: "Заявителей", value: meta.rows },
    { label: "Признаков", value: meta.features },
    { label: "Исходных полей", value: meta.source_columns || "—" },
    { label: "Использовано полей", value: meta.used_columns || "—" },
    { label: "Режим", value: humanizeMode(meta.mode) },
    { label: "Минимум", value: meta.score_min.toFixed(2) },
    { label: "Среднее", value: meta.score_mean.toFixed(2) },
    { label: "Максимум", value: meta.score_max.toFixed(2) },
  ];

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<span>${item.label}</span><strong>${item.value}</strong>`;
    summaryEl.appendChild(card);
  });
}

function renderColumns(data) {
  usedColumnsEl.innerHTML = "";
  excludedColumnsEl.innerHTML = "";

  const records = data.records || [];
  const firstAttributes = records.length > 0 ? records[0].attributes || {} : {};
  const usedColumns = BUSINESS_COLUMNS.filter((column) => column in firstAttributes);
  const excludedColumns = (data.meta && data.meta.excluded_columns) || [];

  if (usedColumns.length === 0) {
    usedColumnsEl.textContent = "Нет данных по используемым полям.";
  } else {
    usedColumns.forEach((column) => {
      const chip = document.createElement("div");
      chip.className = "chip";
      chip.textContent = column;
      usedColumnsEl.appendChild(chip);
    });
  }

  if (excludedColumns.length === 0) {
    excludedColumnsEl.textContent = "Нет исключённых полей.";
  } else {
    excludedColumns.forEach((column) => {
      const chip = document.createElement("div");
      chip.className = "chip";
      chip.textContent = column;
      excludedColumnsEl.appendChild(chip);
    });
  }
}

function renderGlobalFactors(factors) {
  globalFactorsEl.innerHTML = "";
  if (factors.length === 0) {
    globalFactorsEl.textContent = "Недостаточно данных для глобальных факторов.";
    return;
  }
  factors.forEach((factor) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = `${factor.feature}: ${factor.contribution.toFixed(3)}`;
    globalFactorsEl.appendChild(chip);
  });
}

function renderShortlist(shortlist) {
  shortlistEl.innerHTML = "";
  if (shortlist.length === 0) {
    shortlistEl.textContent = "Shortlist пуст.";
    return;
  }
  shortlist.forEach((item) => {
    const wrap = document.createElement("div");
    wrap.className = "short-item";
    const factors = (item.top_factors || [])
      .map((f) => `${f.feature} (${f.contribution.toFixed(2)})`)
      .join(", ");
    const attrs = item.attributes || {};
    wrap.innerHTML = `
      <strong>ID: ${item.id}</strong>
      <span>Score: ${item.score.toFixed(2)}</span>
      <span>Регион: ${attrs["Область"] || "—"}</span>
      <span>Программа: ${attrs["Наименование субсидирования"] || "—"}</span>
      <span>Сумма: ${attrs["Причитающая сумма"] || "—"}</span>
      <span>Факторы: ${factors || "—"}</span>
    `;
    shortlistEl.appendChild(wrap);
  });
}

function renderTable(records) {
  tableHead.innerHTML = "";
  tableBody.innerHTML = "";
  if (records.length === 0) {
    return;
  }

  const attributeKeys = Object.keys(records[0].attributes || {});
  const visibleAttributes = BUSINESS_COLUMNS.filter((column) => attributeKeys.includes(column));
  const columns = ["id", "score", "top_factors"].concat(visibleAttributes);

  const headRow = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col;
    headRow.appendChild(th);
  });
  tableHead.appendChild(headRow);

  records.forEach((record) => {
    const tr = document.createElement("tr");
    columns.forEach((col) => {
      const td = document.createElement("td");
      if (col === "id") {
        td.textContent = record.id;
      } else if (col === "score") {
        td.textContent = record.score.toFixed(2);
      } else if (col === "top_factors") {
        td.textContent = (record.top_factors || [])
          .map((f) => `${f.feature}: ${f.contribution.toFixed(2)}`)
          .join("; ");
      } else {
        const value = record.attributes ? record.attributes[col] : "";
        td.textContent = value === null || value === undefined ? "" : value;
      }
      tr.appendChild(td);
    });
    tableBody.appendChild(tr);
  });
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitScore(false).catch((err) => {
    setStatus(`Ошибка: ${err.message}`, "error");
  });
});

useSampleButton.addEventListener("click", () => {
  submitScore(true).catch((err) => {
    setStatus(`Ошибка: ${err.message}`, "error");
  });
});
