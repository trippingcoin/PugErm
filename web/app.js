const form = document.getElementById("score-form");
const fileInput = document.getElementById("file-input");
const shortlistInput = document.getElementById("shortlist-input");
const regionInput = document.getElementById("region-input");
const farmSizeInput = document.getElementById("farm-size-input");
const subsidyTypeInput = document.getElementById("subsidy-type-input");
const useSampleButton = document.getElementById("use-sample");
const runButton = document.getElementById("run-btn");
const drawer = document.getElementById("explanation-drawer");
const drawerBackdrop = document.getElementById("drawer-backdrop");
const drawerClose = document.getElementById("drawer-close");

const statusEl = document.getElementById("status");
const summaryEl = document.getElementById("summary");
const globalFactorsEl = document.getElementById("global-factors");
const usedColumnsEl = document.getElementById("used-columns");
const excludedColumnsEl = document.getElementById("excluded-columns");
const shortlistEl = document.getElementById("shortlist");
const fairnessEl = document.getElementById("fairness");
const systemExplanationEl = document.getElementById("system-explanation");
const explanationEl = document.getElementById("record-explanation");
const rankingCanvas = document.getElementById("ranking-chart");
const distributionCanvas = document.getElementById("distribution-chart");

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

let latestRecords = [];

function setStatus(message, tone = "info") {
  statusEl.textContent = message;
  statusEl.style.borderColor = tone === "error" ? "rgba(255, 123, 123, 0.7)" : "rgba(120, 147, 201, 0.35)";
  statusEl.style.color = tone === "error" ? "#ff9d9d" : "#b6c5e9";
}

function buildQuery() {
  const params = new URLSearchParams();
  if (shortlistInput.value.trim()) params.set("shortlist", shortlistInput.value.trim());
  if (regionInput.value.trim()) params.set("region", regionInput.value.trim());
  if (farmSizeInput.value.trim()) params.set("farm_size", farmSizeInput.value.trim());
  if (subsidyTypeInput.value.trim()) params.set("subsidy_type", subsidyTypeInput.value.trim());
  const query = params.toString();
  return query ? `?${query}` : "";
}

async function submitScore(useSample = false) {
  document.body.classList.add("loading");
  runButton.disabled = true;
  useSampleButton.disabled = true;
  setStatus("Запускаем анализ данных и ML-скоринг...");
  const query = buildQuery();
  const options = { method: "POST" };

  try {
    if (!useSample && fileInput.files.length > 0) {
      const formData = new FormData();
      formData.append("file", fileInput.files[0]);
      options.body = formData;
    }

    const response = await fetch(`/score${query}`, options);
    const data = await response.json();
    if (!response.ok) {
      const message = data && (data.detail || data.error) ? (data.detail || data.error) : "Ошибка скоринга";
      setStatus(message, "error");
      return;
    }
    renderResult(data);
    setStatus(`Готово. Модель: ${data.meta.selected_model}. Shortlist сформирован.`);
  } finally {
    document.body.classList.remove("loading");
    runButton.disabled = false;
    useSampleButton.disabled = false;
  }
}

function renderResult(data) {
  latestRecords = data.records || [];
  renderSummary(data.meta);
  renderFeatureImportance(data.feature_importance || []);
  renderColumns(data);
  renderShortlist(data.shortlist || []);
  renderFairness(data.fairness);
  renderTable(latestRecords);
  renderRankingChart(data.shortlist || []);
  renderDistributionChart(data.score_distribution || {});
  systemExplanationEl.textContent = data.meta && data.meta.system_explanation
    ? data.meta.system_explanation
    : "Системная логика недоступна.";
}

function renderSummary(meta) {
  summaryEl.innerHTML = "";
  if (!meta) return;
  const items = [
    { label: "Заявителей", value: meta.rows },
    { label: "Исходных полей", value: meta.source_columns },
    { label: "Инженерных признаков", value: meta.engineered_features },
    { label: "Режим", value: meta.mode },
    { label: "Лучшая модель", value: meta.selected_model },
    { label: "Минимум", value: meta.score_min.toFixed(2) },
    { label: "Среднее", value: meta.score_mean.toFixed(2) },
    { label: "Максимум", value: meta.score_max.toFixed(2) },
    { label: "Compliance High", value: meta.compliance_summary?.high ?? 0 },
    { label: "Compliance Medium", value: meta.compliance_summary?.medium ?? 0 },
  ];
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<span>${item.label}</span><strong>${item.value}</strong>`;
    summaryEl.appendChild(card);
  });
}

function renderFeatureImportance(features) {
  globalFactorsEl.innerHTML = "";
  if (!features.length) {
    globalFactorsEl.textContent = "Данные о важности признаков недоступны.";
    return;
  }
  features.slice(0, 12).forEach((factor) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = `${factor.feature}: ${factor.contribution.toFixed(3)}`;
    globalFactorsEl.appendChild(chip);
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

function renderShortlist(shortlist) {
  shortlistEl.innerHTML = "";
  if (!shortlist.length) {
    shortlistEl.textContent = "Shortlist пуст.";
    return;
  }
  shortlist.forEach((item) => {
    const wrap = document.createElement("div");
    wrap.className = "short-item";
    const attrs = item.attributes || {};
    const pos = (item.explanation?.positive || []).slice(0, 2).join(", ");
    const neg = (item.explanation?.negative || []).slice(0, 2).join(", ");
    const failedRules = (item.compliance_flags || []).filter((f) => !f.passed);
    wrap.innerHTML = `
      <strong>Rank #${item.rank} | ID: ${item.id}</strong>
      <span>Score: ${item.score.toFixed(2)}</span>
      <span>Регион: ${attrs["Область"] || "—"}</span>
      <span>Сумма: ${attrs["Причитающая сумма"] || "—"}</span>
      <span>Позитив: ${pos || "—"}</span>
      <span>Риски: ${neg || "—"}</span>
      <span>Rule flags: ${failedRules.map((f) => `${f.code}(${f.severity})`).join(", ") || "нет"}</span>
    `;
    shortlistEl.appendChild(wrap);
  });
}

function renderFairness(fairness) {
  fairnessEl.innerHTML = "";
  if (!fairness || !fairness.groups || !fairness.groups.length) {
    fairnessEl.textContent = "Недостаточно данных для fairness-оценки.";
    return;
  }
  const gap = document.createElement("div");
  gap.className = "short-item";
  gap.innerHTML = `<strong>Mean score gap: ${fairness.mean_score_gap.toFixed(2)}</strong><span>Атрибут: ${fairness.protected_attribute}</span>`;
  fairnessEl.appendChild(gap);
  fairness.groups.slice(0, 6).forEach((g) => {
    const item = document.createElement("div");
    item.className = "short-item";
    item.innerHTML = `<strong>${g.group}</strong><span>count=${g.count}</span><span>mean=${g.mean_score.toFixed(2)}</span>`;
    fairnessEl.appendChild(item);
  });
}

function renderTable(records) {
  tableHead.innerHTML = "";
  tableBody.innerHTML = "";
  if (!records.length) return;

  const attributeKeys = Object.keys(records[0].attributes || {});
  const visibleAttributes = BUSINESS_COLUMNS.filter((column) => attributeKeys.includes(column));
  const columns = ["rank", "id", "score"].concat(visibleAttributes);

  const headRow = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col;
    headRow.appendChild(th);
  });
  tableHead.appendChild(headRow);

  records.forEach((record) => {
    const tr = document.createElement("tr");
    tr.addEventListener("click", () => renderRecordExplanation(record));
    columns.forEach((col) => {
      const td = document.createElement("td");
      if (col === "rank") td.textContent = record.rank;
      else if (col === "id") td.textContent = record.id;
      else if (col === "score") td.textContent = record.score.toFixed(2);
      else td.textContent = record.attributes && record.attributes[col] != null ? record.attributes[col] : "";
      tr.appendChild(td);
    });
    tableBody.appendChild(tr);
  });
}

function renderRecordExplanation(record) {
  const top = (record.explanation?.top_features || [])
    .map((f) => `${f.feature}: ${f.contribution.toFixed(2)}`)
    .join("; ");
  const failedRules = (record.compliance_flags || [])
    .filter((f) => !f.passed)
    .map((f) => `${f.code} [${f.severity}] - ${f.message}`)
    .join(" | ");
  explanationEl.innerHTML = `
    <strong>Rank #${record.rank} | ID: ${record.id} | Score: ${record.score.toFixed(2)}</strong>
    <span>Положительные факторы: ${(record.explanation?.positive || []).join(", ") || "—"}</span>
    <span>Отрицательные факторы: ${(record.explanation?.negative || []).join(", ") || "—"}</span>
    <span>Top features: ${top || "—"}</span>
    <span>Compliance flags: ${failedRules || "Нарушений не выявлено"}</span>
  `;
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
}

function drawBarChart(canvas, labels, values, color = "#b04a2f") {
  canvas.width = canvas.clientWidth || 520;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  if (!labels.length) return;

  const pad = 24;
  const chartW = width - pad * 2;
  const chartH = height - pad * 2;
  const barW = chartW / labels.length;
  const max = Math.max(...values, 1);

  ctx.fillStyle = "#99a7c7";
  ctx.font = "11px Manrope";

  values.forEach((v, i) => {
    const h = (v / max) * (chartH - 20);
    const x = pad + i * barW + 4;
    const y = pad + chartH - h;
    ctx.fillStyle = color;
    ctx.fillRect(x, y, Math.max(barW - 8, 6), h);
    ctx.fillStyle = "#99a7c7";
    ctx.fillText(labels[i], x, pad + chartH + 12);
  });
}

function renderRankingChart(shortlist) {
  const labels = shortlist.slice(0, 10).map((r) => `#${r.rank}`);
  const values = shortlist.slice(0, 10).map((r) => r.score);
  drawBarChart(rankingCanvas, labels, values, "#2f5e4a");
}

function renderDistributionChart(distribution) {
  const labels = (distribution.bins || []).map((x) => `${Math.round(x)}`);
  const values = distribution.counts || [];
  drawBarChart(distributionCanvas, labels, values, "#b04a2f");
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitScore(false).catch((err) => setStatus(`Ошибка: ${err.message}`, "error"));
});

useSampleButton.addEventListener("click", () => {
  submitScore(true).catch((err) => setStatus(`Ошибка: ${err.message}`, "error"));
});

drawerClose.addEventListener("click", () => {
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
});

drawerBackdrop.addEventListener("click", () => {
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
});
