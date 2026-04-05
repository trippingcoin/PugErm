const TRANSLATIONS = {
  ru: {
    html_lang: "ru",
    brand_sub: "Case 2 · Subsidy Intelligence",
    menu_overview: "Обзор",
    menu_shortlist: "Shortlist",
    menu_records: "Заявители",
    menu_analytics: "Аналитика",
    menu_geo: "Карта",
    sidebar_note: "AI помогает комиссии принимать решения, но не заменяет эксперта.",
    topbar_eyebrow: "Government Decision Support",
    topbar_title: "Скоринг заявок на субсидии",
    topbar_chip: "Explainable AI · Live Scoring",
    language: "Language",
    screen_overview: "Экран 1 · Главная страница",
    screen_shortlist: "Экран 2 · Shortlist",
    screen_records: "Экран 3 · Таблица заявителей",
    screen_analytics: "Экран 5 · Аналитика и метрики",
    launch_title: "Запуск анализа",
    launch_desc: "Загрузите датасет или используйте демонстрационный файл.",
    file_data: "Файл данных (xlsx, csv, json)",
    shortlist_size: "Размер shortlist",
    region: "Регион",
    region_placeholder: "например: область Абай",
    farm_size: "Размер хозяйства",
    all: "Все",
    subsidy_type: "Тип субсидии",
    subsidy_placeholder: "наименование субсидирования",
    run_scoring: "Запустить скоринг",
    use_sample: "Использовать Data.xlsx",
    ready_status: "Готово к запуску скоринга.",
    loading_prepare: "Подготовка...",
    loading_1: "Загрузка файла и валидация...",
    loading_2: "Подготовка и инженерия признаков...",
    loading_3: "Обучение/инференс моделей...",
    loading_4: "SHAP-объяснения и ранжирование...",
    loading_5: "Подготовка shortlist и аналитики...",
    run_metrics: "Метрики запуска",
    run_metrics_desc: "NDCG и Lift — главный аргумент против FCFS",
    top_candidates: "Топ кандидатов в рекомендации комиссии",
    feature_importance: "Feature Importance",
    system_logic: "Системная логика",
    system_logic_default: "Модель ранжирует заявки по продуктивности, стабильности и эффективности использования субсидий.",
    ndcg_vs_fcfs: "NDCG vs FCFS",
    fairness_check: "Fairness Check",
    score_distribution: "Score Distribution",
    top_ranking_chart: "Top Ranking Chart",
    roi_scenario: "ROI Scenario",
    kz_map: "Карта Казахстана",
    kz_map_desc: "Средний скор по регионам. Клик по региону применяет локальный фильтр.",
    region_analytics: "Региональная аналитика",
    all_regions: "Все регионы",
    reset_map: "Сбросить фильтр карты",
    used_fields: "Используемые поля",
    excluded_fields: "Исключённые поля",
    all_applicants: "Все заявители",
    applicants_desc: "Кликните по строке для объяснения и compliance-флагов.",
    prev: "← Prev",
    next: "Next →",
    page_size: "Page Size",
    explanation_title: "Объяснение по заявителю",
    close: "Закрыть",
    explanation_hint: "Кликните по строке таблицы для детального объяснения.",
    commission_decision: "Решение комиссии",
    decision: "Решение",
    reason_code: "Код причины",
    reason_placeholder: "например: COMPLIANCE_GAP",
    comment: "Комментарий",
    comment_placeholder: "Комментарий комиссии",
    expert: "Эксперт",
    expert_placeholder: "ФИО / login",
    save_decision: "Сохранить решение",
    download_pdf: "Скачать PDF",
    audit_log: "Журнал аудита",
    no_events: "Событий пока нет.",
    summary_applicants: "Заявителей",
    summary_mean: "Скор среднее",
    summary_recommended: "Рекомендованы",
    summary_high_risk: "Высокий риск",
    summary_lift: "Lift vs FCFS%",
    metrics_model_ndcg: "NDCG@20 (наша модель)",
    metrics_base_ndcg: "NDCG@20 (FCFS baseline)",
    metrics_model_precision: "Precision@20 (модель)",
    metrics_base_precision: "Precision@20 (FCFS)",
    metrics_lift: "Lift vs FCFS, %",
    no_data: "Нет данных.",
    no_shortlist: "Shortlist пуст.",
    rank: "Ранг",
    risk_low: "низкий",
    risk_medium: "средний",
    risk_high: "высокий",
    recommended: "Рекомендован",
    flags_count: "флагов",
    amount: "Сумма",
    region_label: "Регион",
    fairness_high: "⚠ Высокий дисбаланс по регионам",
    fairness_mid: "~ Умеренный дисбаланс",
    fairness_ok: "✓ Дисбаланс в норме",
    fairness_gap: "Разрыв среднего score",
    median: "медиана",
    insufficient_data: "Недостаточно данных.",
    no_excluded_fields: "Нет исключённых полей.",
    no_chart_data: "Нет данных для графика",
    records_page: "Страница {page} из {totalPages} · всего {total}",
    records_no_data: "Нет данных",
    loading_saved_state: "Загружено сохранённое состояние: {rows} записей",
    lang_switched_ru: "Язык переключён: Русский",
    lang_switched_kz: "Тіл ауысты: Қазақша",
    scoring_start: "Запускаем ML-скоринг (Stacking Ensemble + SHAP)...",
    done_status: "✓ Готово. Модель: {model} | Строк: {rows}",
    score_error: "Ошибка скоринга",
    error_prefix: "Ошибка: {message}",
    scenario_title: "Сценарий: финансирование топ-{n}",
    scenario_budget: "Бюджет",
    scenario_gain: "Ожидаемый прирост продукции",
    scenario_gain_risk: "С учётом рисков",
    map_low: "Низкий скор",
    map_high: "Высокий скор",
    map_grey: "Серый: нет данных ({count})",
    map_no_data: "Нет региональных данных.",
    map_load_error: "Не удалось загрузить карту.",
    map_loading: "Загрузка карты...",
    map_selected_region: "Выбран регион: {region}",
    map_requests: "Заявок",
    zoom_reset: "Reset",
    breakdown_title: "Разбивка скора",
    shap_title: "SHAP — вклад факторов",
    text_explanation: "Текстовое объяснение ({lang})",
    positive_factors: "▲ Позитивные факторы",
    negative_factors: "▼ Факторы риска",
    compliance_violations: "⚠ Нарушения Compliance ({count})",
    no_violations: "✓ Нарушений не выявлено",
    recommended_review: "На рассмотрение",
  },
  kz: {
    html_lang: "kk",
    brand_sub: "2-case · Subsidy Intelligence",
    menu_overview: "Шолу",
    menu_shortlist: "Shortlist",
    menu_records: "Өтінімдер",
    menu_analytics: "Аналитика",
    menu_geo: "Карта",
    sidebar_note: "AI комиссияға шешім қабылдауға көмектеседі, бірақ сарапшыны алмастырмайды.",
    topbar_eyebrow: "Government Decision Support",
    topbar_title: "Субсидия өтінімдерін скорингтеу",
    topbar_chip: "Explainable AI · Live Scoring",
    language: "Тіл",
    screen_overview: "1-экран · Басты бет",
    screen_shortlist: "2-экран · Shortlist",
    screen_records: "3-экран · Өтінімдер кестесі",
    screen_analytics: "5-экран · Аналитика және метрикалар",
    launch_title: "Талдауды бастау",
    launch_desc: "Деректер жиынын жүктеңіз немесе демо файлды пайдаланыңыз.",
    file_data: "Деректер файлы (xlsx, csv, json)",
    shortlist_size: "Shortlist өлшемі",
    region: "Өңір",
    region_placeholder: "мысалы: Абай облысы",
    farm_size: "Шаруашылық өлшемі",
    all: "Барлығы",
    subsidy_type: "Субсидия түрі",
    subsidy_placeholder: "субсидиялау атауы",
    run_scoring: "Скорингті іске қосу",
    use_sample: "Data.xlsx пайдалану",
    ready_status: "Скорингті іске қосуға дайын.",
    loading_prepare: "Дайындау...",
    loading_1: "Файлды жүктеу және тексеру...",
    loading_2: "Белгілерді дайындау және feature engineering...",
    loading_3: "Модельдерді оқыту/инференс...",
    loading_4: "SHAP түсіндірмелері мен ранжирлеу...",
    loading_5: "Shortlist және аналитиканы дайындау...",
    run_metrics: "Іске қосу метрикалары",
    run_metrics_desc: "NDCG және Lift — FCFS-ке қарсы негізгі дәлел",
    top_candidates: "Комиссияға ұсынылатын үздік кандидаттар",
    feature_importance: "Feature Importance",
    system_logic: "Жүйе логикасы",
    system_logic_default: "Модель өтінімдерді өнімділік, тұрақтылық және субсидияны пайдалану тиімділігі бойынша ранжирлейді.",
    ndcg_vs_fcfs: "NDCG vs FCFS",
    fairness_check: "Fairness Check",
    score_distribution: "Score Distribution",
    top_ranking_chart: "Top Ranking Chart",
    roi_scenario: "ROI Сценарийі",
    kz_map: "Қазақстан картасы",
    kz_map_desc: "Өңірлер бойынша орташа скор. Өңірді басу жергілікті фильтрді қолданады.",
    region_analytics: "Өңірлік аналитика",
    all_regions: "Барлық өңірлер",
    reset_map: "Карта фильтрін тазалау",
    used_fields: "Қолданылатын өрістер",
    excluded_fields: "Шығарылған өрістер",
    all_applicants: "Барлық өтінімдер",
    applicants_desc: "Түсіндірме мен compliance-флагтарды көру үшін жолды басыңыз.",
    prev: "← Артқа",
    next: "Келесі →",
    page_size: "Бет өлшемі",
    explanation_title: "Өтінім бойынша түсіндірме",
    close: "Жабу",
    explanation_hint: "Толық түсіндірмені көру үшін кесте жолын басыңыз.",
    commission_decision: "Комиссия шешімі",
    decision: "Шешім",
    reason_code: "Себеп коды",
    reason_placeholder: "мысалы: COMPLIANCE_GAP",
    comment: "Пікір",
    comment_placeholder: "Комиссия пікірі",
    expert: "Сарапшы",
    expert_placeholder: "Аты-жөні / login",
    save_decision: "Шешімді сақтау",
    download_pdf: "PDF жүктеу",
    audit_log: "Аудит журналы",
    no_events: "Оқиғалар әзірге жоқ.",
    summary_applicants: "Өтінімдер",
    summary_mean: "Орташа скор",
    summary_recommended: "Ұсынылған",
    summary_high_risk: "Жоғары тәуекел",
    summary_lift: "Lift vs FCFS%",
    metrics_model_ndcg: "NDCG@20 (біздің модель)",
    metrics_base_ndcg: "NDCG@20 (FCFS baseline)",
    metrics_model_precision: "Precision@20 (модель)",
    metrics_base_precision: "Precision@20 (FCFS)",
    metrics_lift: "Lift vs FCFS, %",
    no_data: "Дерек жоқ.",
    no_shortlist: "Shortlist бос.",
    rank: "Ранг",
    risk_low: "төмен",
    risk_medium: "орташа",
    risk_high: "жоғары",
    recommended: "Ұсынылған",
    flags_count: "флаг",
    amount: "Сома",
    region_label: "Өңір",
    fairness_high: "⚠ Өңірлер бойынша жоғары дисбаланс",
    fairness_mid: "~ Орташа дисбаланс",
    fairness_ok: "✓ Дисбаланс қалыпты",
    fairness_gap: "Орташа score айырмасы",
    median: "медиана",
    insufficient_data: "Дерек жеткіліксіз.",
    no_excluded_fields: "Шығарылған өрістер жоқ.",
    no_chart_data: "График үшін дерек жоқ",
    records_page: "{page}-бет / {totalPages} · барлығы {total}",
    records_no_data: "Дерек жоқ",
    loading_saved_state: "Сақталған күй жүктелді: {rows} жазба",
    lang_switched_ru: "Язык переключён: Русский",
    lang_switched_kz: "Тіл ауысты: Қазақша",
    scoring_start: "ML-скоринг іске қосылуда (Stacking Ensemble + SHAP)...",
    done_status: "✓ Дайын. Модель: {model} | Жолдар: {rows}",
    score_error: "Скоринг қатесі",
    error_prefix: "Қате: {message}",
    scenario_title: "Сценарий: топ-{n} қаржыландыру",
    scenario_budget: "Бюджет",
    scenario_gain: "Күтілетін өнім өсімі",
    scenario_gain_risk: "Тәуекелді ескере отырып",
    map_low: "Төмен скор",
    map_high: "Жоғары скор",
    map_grey: "Сұр: дерек жоқ ({count})",
    map_no_data: "Өңірлік деректер жоқ.",
    map_load_error: "Картаны жүктеу мүмкін болмады.",
    map_loading: "Карта жүктелуде...",
    map_selected_region: "Таңдалған өңір: {region}",
    map_requests: "Өтінімдер",
    zoom_reset: "Қалпына келтіру",
    breakdown_title: "Скор құрылымы",
    shap_title: "SHAP — фактор үлесі",
    text_explanation: "Мәтіндік түсіндірме ({lang})",
    positive_factors: "▲ Оң факторлар",
    negative_factors: "▼ Тәуекел факторлары",
    compliance_violations: "⚠ Compliance бұзушылықтары ({count})",
    no_violations: "✓ Бұзушылық анықталмады",
    recommended_review: "Қаралуда",
  },
};

const STATIC_SELECTORS = {
  ".brand-sub": "brand_sub",
  ".menu-item[data-view-link='overview']": "menu_overview",
  ".menu-item[data-view-link='shortlist']": "menu_shortlist",
  ".menu-item[data-view-link='records']": "menu_records",
  ".menu-item[data-view-link='analytics']": "menu_analytics",
  ".menu-item[data-view-link='geo']": "menu_geo",
  ".sidebar-foot p": "sidebar_note",
  ".topbar > div:first-child .eyebrow": "topbar_eyebrow",
  ".topbar > div:first-child h1": "topbar_title",
  ".topbar-chip": "topbar_chip",
  ".topbar .field span": "language",
  ".screen-view[data-view='overview'].eyebrow": "screen_overview",
  ".screen-view[data-view='shortlist'].eyebrow": "screen_shortlist",
  ".screen-view[data-view='records'].eyebrow": "screen_records",
  ".screen-view[data-view='analytics'].eyebrow": "screen_analytics",
  "#overview .card-head h2": "launch_title",
  "#overview .card-head p": "launch_desc",
  "label[for='file-input'] span": "file_data",
};

export function t(key, lang = "ru", vars = {}) {
  const text = TRANSLATIONS[lang]?.[key] ?? TRANSLATIONS.ru[key] ?? key;
  return String(text).replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? `{${name}}`);
}

export function riskLabel(risk, lang = "ru") {
  const value = String(risk || "low").toLowerCase();
  return t(`risk_${value}`, lang);
}

export function applyStaticTranslations(lang = "ru") {
  document.documentElement.lang = t("html_lang", lang);

  const setText = (selector, key) => {
    const el = document.querySelector(selector);
    if (el) el.textContent = t(key, lang);
  };

  setText(".brand-sub", "brand_sub");
  setText(".menu-item[data-view-link='overview']", "menu_overview");
  setText(".menu-item[data-view-link='shortlist']", "menu_shortlist");
  setText(".menu-item[data-view-link='records']", "menu_records");
  setText(".menu-item[data-view-link='analytics']", "menu_analytics");
  setText(".menu-item[data-view-link='geo']", "menu_geo");
  setText(".sidebar-foot p", "sidebar_note");
  setText(".topbar > div:first-child .eyebrow", "topbar_eyebrow");
  setText(".topbar > div:first-child h1", "topbar_title");
  setText(".topbar-chip", "topbar_chip");
  setText(".topbar .field span", "language");
  setText(".screen-view[data-view='overview'].eyebrow", "screen_overview");
  setText(".screen-view[data-view='shortlist'].eyebrow", "screen_shortlist");
  setText(".screen-view[data-view='records'].eyebrow", "screen_records");
  setText(".screen-view[data-view='analytics'].eyebrow", "screen_analytics");
  setText("#overview .card-head h2", "launch_title");
  setText("#overview .card-head p", "launch_desc");

  const formLabels = Array.from(document.querySelectorAll("#score-form .field > span"));
  if (formLabels[0]) formLabels[0].textContent = t("file_data", lang);
  if (formLabels[1]) formLabels[1].textContent = t("shortlist_size", lang);
  if (formLabels[2]) formLabels[2].textContent = t("region", lang);
  if (formLabels[3]) formLabels[3].textContent = t("farm_size", lang);
  if (formLabels[4]) formLabels[4].textContent = t("subsidy_type", lang);

  const regionInput = document.getElementById("region-input");
  if (regionInput) regionInput.placeholder = t("region_placeholder", lang);
  const subsidyTypeInput = document.getElementById("subsidy-type-input");
  if (subsidyTypeInput) subsidyTypeInput.placeholder = t("subsidy_placeholder", lang);

  const farmSize = document.getElementById("farm-size-input");
  if (farmSize?.options?.length >= 4) {
    farmSize.options[0].textContent = t("all", lang);
    farmSize.options[1].textContent = "Small";
    farmSize.options[2].textContent = "Medium";
    farmSize.options[3].textContent = "Large";
  }

  const runBtn = document.getElementById("run-btn");
  if (runBtn) runBtn.textContent = t("run_scoring", lang);
  const sampleBtn = document.getElementById("use-sample");
  if (sampleBtn) sampleBtn.textContent = t("use_sample", lang);
  const status = document.getElementById("status");
  if (status && !status.dataset.dynamic) status.textContent = t("ready_status", lang);
  const loadingText = document.getElementById("loading-progress-text");
  if (loadingText && !document.body.classList.contains("loading")) loadingText.textContent = t("loading_prepare", lang);

  const overviewHeads = document.querySelectorAll("#overview .card-head");
  if (overviewHeads[1]) {
    const h3 = overviewHeads[1].querySelector("h3");
    const p = overviewHeads[1].querySelector("p");
    if (h3) h3.textContent = t("run_metrics", lang);
    if (p) p.textContent = t("run_metrics_desc", lang);
  }

  setText("#shortlist-screen .card-head h3", "top_candidates");
  const featureHeads = document.querySelectorAll("#feature-section .card-head h3");
  if (featureHeads[0]) featureHeads[0].textContent = t("feature_importance", lang);
  if (featureHeads[1]) featureHeads[1].textContent = t("system_logic", lang);
  const systemText = document.getElementById("system-explanation");
  if (systemText && !systemText.dataset.dynamic) systemText.textContent = t("system_logic_default", lang);

  const analyticsHeads = document.querySelectorAll("#analytics .card-head h3");
  if (analyticsHeads[0]) analyticsHeads[0].textContent = t("ndcg_vs_fcfs", lang);
  if (analyticsHeads[1]) analyticsHeads[1].textContent = t("fairness_check", lang);
  const metricHeads = document.querySelectorAll("#metrics .card-head h3");
  if (metricHeads[0]) metricHeads[0].textContent = t("score_distribution", lang);
  if (metricHeads[1]) metricHeads[1].textContent = t("top_ranking_chart", lang);
  if (metricHeads[2]) metricHeads[2].textContent = t("roi_scenario", lang);

  const geoHeads = document.querySelectorAll("#geo .card-head");
  if (geoHeads[0]) {
    const h3 = geoHeads[0].querySelector("h3");
    const p = geoHeads[0].querySelector("p");
    if (h3) h3.textContent = t("kz_map", lang);
    if (p) p.textContent = t("kz_map_desc", lang);
  }
  if (geoHeads[1]) {
    const h3 = geoHeads[1].querySelector("h3");
    if (h3) h3.textContent = t("region_analytics", lang);
  }
  const activeRegion = document.getElementById("kz-active-region");
  if (activeRegion && !activeRegion.dataset.dynamic) activeRegion.textContent = t("all_regions", lang);
  const resetBtn = document.getElementById("kz-map-reset");
  if (resetBtn) resetBtn.textContent = t("reset_map", lang);

  const colsHeads = document.querySelectorAll("#columns-section .card-head h3");
  if (colsHeads[0]) colsHeads[0].textContent = t("used_fields", lang);
  if (colsHeads[1]) colsHeads[1].textContent = t("excluded_fields", lang);

  const recordsHead = document.querySelector("#records .card-head");
  if (recordsHead) {
    const h3 = recordsHead.querySelector("h3");
    const p = recordsHead.querySelector("p");
    if (h3) h3.textContent = t("all_applicants", lang);
    if (p) p.textContent = t("applicants_desc", lang);
  }
  setText("#records-prev", "prev");
  setText("#records-next", "next");
  const pageSizeLabel = document.querySelector("label[style*='max-width: 120px;'] span");
  if (pageSizeLabel) pageSizeLabel.textContent = t("page_size", lang);

  setText(".drawer-head h3", "explanation_title");
  setText("#drawer-close", "close");
  const exp = document.getElementById("record-explanation");
  if (exp && !exp.dataset.dynamic) exp.textContent = t("explanation_hint", lang);
  const drawerContent = document.querySelectorAll(".drawer-content");
  if (drawerContent[1]) {
    const h4 = drawerContent[1].querySelector("h4");
    if (h4) h4.textContent = t("commission_decision", lang);
    const spans = drawerContent[1].querySelectorAll(".field > span");
    if (spans[0]) spans[0].textContent = t("decision", lang);
    if (spans[1]) spans[1].textContent = t("reason_code", lang);
    if (spans[2]) spans[2].textContent = t("comment", lang);
    if (spans[3]) spans[3].textContent = t("expert", lang);
  }
  const reasonInput = document.getElementById("reason-code-input");
  if (reasonInput) reasonInput.placeholder = t("reason_placeholder", lang);
  const commentInput = document.getElementById("decision-comment-input");
  if (commentInput) commentInput.placeholder = t("comment_placeholder", lang);
  const expertInput = document.getElementById("decided-by-input");
  if (expertInput) expertInput.placeholder = t("expert_placeholder", lang);
  setText("#save-decision-btn", "save_decision");
  setText("#download-report-btn", "download_pdf");
  const auditHeader = document.querySelectorAll(".drawer-content h4")[1];
  if (auditHeader) auditHeader.textContent = t("audit_log", lang);
}
