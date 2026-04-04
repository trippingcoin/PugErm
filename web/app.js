import { dom } from "/static/js/dom.js";
import { state } from "/static/js/state.js";
import { renderSummary, renderRankingMetrics } from "/static/js/components/metrics.js";
import { renderShortlist } from "/static/js/components/shortlist.js";
import { renderFairness } from "/static/js/components/fairness.js";
import { renderRecordsTable } from "/static/js/components/recordsTable.js";
import { renderColumns } from "/static/js/components/columns.js";
import { renderKazakhstanMap } from "/static/js/components/mapKazakhstan.js";
import { renderRecordExplanation } from "/static/js/components/drawer.js";
import { renderBarChart } from "/static/js/components/charts.js";
import { getAuditApi, getDecisionApi, getLastScoreApi, getRecordsApi, getScenarioApi, getTopApi, saveDecisionApi, scoreApi } from "/static/js/services/api.js";
import { inferViewFromHash, switchView } from "/static/js/router/viewRouter.js";

let progressTimer = null;

function setStatus(message, tone = "info") {
  dom.statusEl.textContent = message;
  dom.statusEl.style.borderLeftColor = tone === "error" ? "var(--red)" : tone === "success" ? "var(--green)" : "var(--blue)";
}

function startProgress() {
  if (!dom.loadingProgressEl || !dom.loadingProgressTextEl) return;
  const stages = [
    "Загрузка файла и валидация...",
    "Подготовка и инженерия признаков...",
    "Обучение/инференс моделей...",
    "SHAP-объяснения и ранжирование...",
    "Подготовка shortlist и аналитики...",
  ];
  let i = 0;
  dom.loadingProgressTextEl.textContent = stages[i];
  dom.loadingProgressEl.classList.add("active");
  dom.loadingProgressEl.setAttribute("aria-hidden", "false");
  if (progressTimer) clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    i = (i + 1) % stages.length;
    dom.loadingProgressTextEl.textContent = stages[i];
  }, 1500);
}

function stopProgress() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  if (!dom.loadingProgressEl || !dom.loadingProgressTextEl) return;
  dom.loadingProgressEl.classList.remove("active");
  dom.loadingProgressEl.setAttribute("aria-hidden", "true");
  dom.loadingProgressTextEl.textContent = "Подготовка...";
}

function buildQuery() {
  const params = new URLSearchParams();
  if (dom.shortlistInput.value.trim()) params.set("shortlist", dom.shortlistInput.value.trim());
  if (dom.regionInput.value.trim()) params.set("region", dom.regionInput.value.trim());
  if (dom.farmSizeInput.value.trim()) params.set("farm_size", dom.farmSizeInput.value.trim());
  if (dom.subsidyTypeInput.value.trim()) params.set("subsidy_type", dom.subsidyTypeInput.value.trim());
  params.set("compact", "1");
  const q = params.toString();
  return q ? `?${q}` : "";
}

function buildFilterParams() {
  const params = new URLSearchParams();
  const region = state.selectedMapRegionRaw || dom.regionInput.value.trim();
  if (region) params.set("region", region);
  if (dom.farmSizeInput.value.trim()) params.set("farm_size", dom.farmSizeInput.value.trim());
  if (dom.subsidyTypeInput.value.trim()) params.set("subsidy_type", dom.subsidyTypeInput.value.trim());
  return params;
}

function renderFeatureImportance(features) {
  dom.globalFactorsEl.innerHTML = "";
  if (!features.length) {
    dom.globalFactorsEl.textContent = "Нет данных.";
    return;
  }
  features.slice(0, 14).forEach(f => {
    const chip = document.createElement("div");
    chip.className = "chip";
    const val = typeof f.contribution === "number" ? f.contribution.toFixed(3) : f.contribution;
    chip.textContent = `${f.feature}: ${val}`;
    dom.globalFactorsEl.appendChild(chip);
  });
}

async function loadRecordsPage(page = 1) {
  const params = buildFilterParams();
  params.set("page", String(page));
  params.set("page_size", String(state.recordsPageSize));
  const res = await getRecordsApi(params);
  if (!res.ok) return;
  const data = await res.json();
  state.recordsPage = Number(data.page || page);
  state.recordsTotal = Number(data.total || 0);
  const tableMeta = renderRecordsTable({
    headEl: dom.tableHead,
    bodyEl: dom.tableBody,
    records: data.records || [],
    total: state.recordsTotal,
    page: state.recordsPage,
    pageSize: state.recordsPageSize,
    onSelect: openRecordDrawer,
    onDownloadPdf: downloadReportById,
  });
  if (!tableMeta) {
    dom.recordsPageInfoEl.textContent = "Нет данных";
    return;
  }
  dom.recordsPageInfoEl.textContent = `Страница ${tableMeta.page} из ${tableMeta.totalPages} · всего ${tableMeta.total}`;
  dom.recordsPrevBtn.disabled = tableMeta.page <= 1;
  dom.recordsNextBtn.disabled = tableMeta.page >= tableMeta.totalPages;
}

async function loadShortlist() {
  const params = buildFilterParams();
  params.set("n", String(dom.shortlistInput.value.trim() || 20));
  const res = await getTopApi(params);
  if (!res.ok) return;
  const data = await res.json();
  state.latestShortlist = data.records || state.latestShortlist;
  renderShortlist({
    el: dom.shortlistEl,
    shortlist: state.latestShortlist,
    onSelect: openRecordDrawer,
    onDownloadPdf: downloadReportById,
  });
}

function refreshMap() {
  renderKazakhstanMap({
    mapEl: dom.kzMapEl,
    legendEl: dom.kzLegendEl,
    statsEl: dom.kzRegionStatsEl,
    activeRegionEl: dom.kzActiveRegionEl,
    records: state.latestRecords,
    fairness: state.lastFairness,
    selectedRegionNorm: state.selectedMapRegion,
    selectedRegionLabel: state.selectedMapRegionRaw,
    onRegionClick: regionInfo => {
      const next = state.selectedMapRegion === regionInfo.norm ? "" : regionInfo.norm;
      state.selectedMapRegion = next;
      state.selectedMapRegionRaw = next ? regionInfo.region : "";
      refreshMap();
      loadShortlist().catch(() => {});
      loadRecordsPage(1).catch(() => {});
    },
  });
}

async function renderScenario() {
  const res = await getScenarioApi();
  if (!res.ok) return;
  const data = await res.json();
  dom.scenarioRoiEl.innerHTML = "";
  const card = document.createElement("div");
  card.className = "short-item";
  card.innerHTML = `
    <strong>Сценарий: финансирование топ-${data.selected_farms}</strong>
    <span>Бюджет: <b style="color:var(--amber)">${Number(data.estimated_budget).toLocaleString("ru-RU")} ₸</b></span>
    <span>Ожидаемый прирост продукции: <b style="color:var(--green)">+${data.expected_output_gain_pct}%</b></span>
    <span>С учётом рисков: <b style="color:var(--teal)">+${data.expected_risk_adjusted_gain_pct}%</b></span>
  `;
  dom.scenarioRoiEl.appendChild(card);
}

function renderResult(data) {
  state.lastResponse = data;
  state.latestRecords = data.records || [];
  state.latestShortlist = data.shortlist || [];
  state.lastFairness = data.fairness || null;

  const source = state.latestRecords.length ? state.latestRecords : state.latestShortlist;
  renderSummary({ el: dom.summaryEl, meta: data.meta, sourceRecords: source });
  renderRankingMetrics({ el: dom.rankingMetricsEl, metrics: data.meta?.ranking_metrics || {} });
  renderFeatureImportance(data.feature_importance || []);
  renderColumns({ usedEl: dom.usedColumnsEl, excludedEl: dom.excludedColumnsEl, response: data });
  renderShortlist({
    el: dom.shortlistEl,
    shortlist: state.latestShortlist,
    onSelect: openRecordDrawer,
    onDownloadPdf: downloadReportById,
  });
  renderFairness({ el: dom.fairnessEl, fairness: data.fairness });
  refreshMap();
  loadRecordsPage(1).catch(() => {});

  renderBarChart(
    dom.rankingCanvas,
    (data.shortlist || []).slice(0, 10).map(r => `#${r.rank}`),
    (data.shortlist || []).slice(0, 10).map(r => r.score),
    "var(--teal)",
  );
  renderBarChart(
    dom.distributionCanvas,
    (data.score_distribution?.bins || []).map(x => Math.round(x)),
    data.score_distribution?.counts || [],
    "var(--blue)",
  );
  dom.systemExplanationEl.textContent = data.meta?.system_explanation || "";
  renderScenario().catch(() => {});
}

async function submitScore(useSample = false) {
  document.body.classList.add("loading");
  dom.runButton.disabled = true;
  dom.useSampleButton.disabled = true;
  setStatus("Запускаем ML-скоринг (Stacking Ensemble + SHAP)...");
  startProgress();
  state.selectedMapRegion = "";
  state.selectedMapRegionRaw = "";

  try {
    const { res, data } = await scoreApi({
      query: buildQuery(),
      file: !useSample && dom.fileInput.files.length > 0 ? dom.fileInput.files[0] : null,
    });
    if (!res.ok) {
      setStatus(data.detail || "Ошибка скоринга", "error");
      return;
    }
    renderResult(data);
    setStatus(`✓ Готово. Модель: ${data.meta.selected_model} | Строк: ${data.meta.rows}`, "success");
  } catch (err) {
    setStatus(`Ошибка: ${err.message}`, "error");
  } finally {
    stopProgress();
    document.body.classList.remove("loading");
    dom.runButton.disabled = false;
    dom.useSampleButton.disabled = false;
  }
}

async function loadDecisionAndAudit(applicationId) {
  dom.auditLogEl.innerHTML = "";
  const [dRes, aRes] = await Promise.all([getDecisionApi(applicationId), getAuditApi(applicationId)]);
  if (dRes.ok) {
    const d = await dRes.json();
    if (d?.decision) {
      dom.decisionInput.value = d.decision.decision || "APPROVE";
      dom.reasonCodeInput.value = d.decision.reason_code || "";
      dom.decisionCommentInput.value = d.decision.comment || "";
      dom.decidedByInput.value = d.decision.decided_by || dom.decidedByInput.value;
      dom.decisionStatusEl.textContent = `Сохранено: ${d.decision.decision} (${d.decision.reason_code || "—"})`;
    }
  }
  if (aRes.ok) {
    const a = await aRes.json();
    const entries = a.entries || [];
    dom.auditLogEl.innerHTML = "";
    if (!entries.length) {
      dom.auditLogEl.textContent = "Событий пока нет.";
      return;
    }
    entries.forEach(e => {
      const item = document.createElement("div");
      item.className = "short-item";
      item.innerHTML = `<strong>${e.action}</strong><span>${e.at}</span><span>actor = ${e.actor}</span>`;
      dom.auditLogEl.appendChild(item);
    });
  }
}

function openRecordDrawer(record) {
  state.selectedRecord = record;
  renderRecordExplanation({ explanationEl: dom.explanationEl, record, currentLang: state.currentLang });
  dom.drawer.classList.add("open");
  dom.drawer.setAttribute("aria-hidden", "false");
  dom.decisionStatusEl.textContent = "Решение пока не сохранено.";
  loadDecisionAndAudit(record.id).catch(() => {
    dom.auditLogEl.textContent = "Не удалось загрузить аудит.";
  });
}

async function saveCommissionDecision() {
  if (!state.selectedRecord) {
    dom.decisionStatusEl.textContent = "Выберите заявителя.";
    return;
  }
  const payload = {
    application_id: state.selectedRecord.id,
    decision: dom.decisionInput.value,
    reason_code: dom.reasonCodeInput.value.trim() || "UNSPECIFIED",
    comment: dom.decisionCommentInput.value.trim() || null,
    decided_by: dom.decidedByInput.value.trim() || "commission_user",
  };
  const res = await saveDecisionApi(payload);
  if (!res.ok) {
    dom.decisionStatusEl.textContent = "Ошибка сохранения.";
    return;
  }
  dom.decisionStatusEl.textContent = `✓ Решение сохранено: ${payload.decision}`;
  loadDecisionAndAudit(state.selectedRecord.id).catch(() => {});
}

function downloadReport() {
  if (!state.selectedRecord) {
    dom.decisionStatusEl.textContent = "Выберите заявителя.";
    return;
  }
  window.open(`/api/reports/${encodeURIComponent(state.selectedRecord.id)}.pdf?lang=${state.currentLang}`, "_blank");
}

function downloadReportById(applicationId) {
  window.open(`/api/reports/${encodeURIComponent(applicationId)}.pdf?lang=${state.currentLang}`, "_blank");
}

function bindEvents() {
  dom.form.addEventListener("submit", e => {
    e.preventDefault();
    submitScore(false);
  });
  dom.useSampleButton.addEventListener("click", () => submitScore(true));
  dom.drawerClose.addEventListener("click", () => {
    dom.drawer.classList.remove("open");
    dom.drawer.setAttribute("aria-hidden", "true");
  });
  dom.drawerBackdrop.addEventListener("click", () => {
    dom.drawer.classList.remove("open");
    dom.drawer.setAttribute("aria-hidden", "true");
  });
  dom.saveDecisionBtn.addEventListener("click", () => {
    saveCommissionDecision().catch(err => {
      dom.decisionStatusEl.textContent = `Ошибка: ${err.message}`;
    });
  });
  dom.downloadReportBtn.addEventListener("click", downloadReport);
  dom.kzMapResetBtn?.addEventListener("click", () => {
    state.selectedMapRegion = "";
    state.selectedMapRegionRaw = "";
    refreshMap();
    loadShortlist().catch(() => {});
    loadRecordsPage(1).catch(() => {});
  });
  dom.recordsPrevBtn?.addEventListener("click", () => {
    if (state.recordsPage > 1) loadRecordsPage(state.recordsPage - 1).catch(() => {});
  });
  dom.recordsNextBtn?.addEventListener("click", () => {
    const totalPages = Math.max(1, Math.ceil(state.recordsTotal / state.recordsPageSize));
    if (state.recordsPage < totalPages) loadRecordsPage(state.recordsPage + 1).catch(() => {});
  });
  dom.recordsPageSizeEl?.addEventListener("change", () => {
    state.recordsPageSize = Number(dom.recordsPageSizeEl.value || 50);
    loadRecordsPage(1).catch(() => {});
  });
  dom.viewLinks.forEach(link => {
    link.addEventListener("click", () => {
      switchView({ screenViews: dom.screenViews, viewLinks: dom.viewLinks, view: link.dataset.viewLink || "overview" });
    });
  });
  dom.langToggle.addEventListener("change", () => {
    state.currentLang = dom.langToggle.value || "ru";
    setStatus(state.currentLang === "kz" ? "Тіл ауысты: Қазақша" : "Язык переключён: Русский");
  });
  window.addEventListener("hashchange", () => {
    switchView({ screenViews: dom.screenViews, viewLinks: dom.viewLinks, view: inferViewFromHash(window.location.hash) });
  });
  window.addEventListener("resize", () => {
    if (!state.lastResponse) return;
    renderBarChart(
      dom.rankingCanvas,
      (state.lastResponse.shortlist || []).slice(0, 10).map(r => `#${r.rank}`),
      (state.lastResponse.shortlist || []).slice(0, 10).map(r => r.score),
      "var(--teal)",
    );
    renderBarChart(
      dom.distributionCanvas,
      (state.lastResponse.score_distribution?.bins || []).map(x => Math.round(x)),
      state.lastResponse.score_distribution?.counts || [],
      "var(--blue)",
    );
  });
}

async function bootstrapLastState() {
  const res = await getLastScoreApi(true);
  if (!res.ok) return;
  const data = await res.json();
  renderResult(data);
  setStatus(`Загружено сохранённое состояние: ${data.meta?.rows || 0} записей`, "success");
}

state.recordsPageSize = Number(dom.recordsPageSizeEl?.value || 50);
switchView({ screenViews: dom.screenViews, viewLinks: dom.viewLinks, view: inferViewFromHash(window.location.hash) });
bindEvents();
bootstrapLastState().catch(() => {});
