# AgriScore KZ

GovTech AI-прототип для Decentrathon 5.0 (Case 2): explainable scoring сельхозпроизводителей для распределения субсидий.

## Что важно сразу

- Да, система **работает без внешних API** (live enrichment опциональный).
- Фронт теперь модульный и stateful.
- Большая таблица работает через серверную пагинацию.
- Последний скоринг сохраняется и восстанавливается после рестарта.

## Архитектура

```text
app/
  api/routes.py
  data/
    loader.py
    features.py
    live_enrichment.py        # NEW: live внешние данные по регионам (опционально)
  models/trainer.py
  services/
    scoring_service.py        # NEW: persisted last score state
    rules.py
    reporting.py
    decision_store.py
  schemas.py
cmd/server/main.py
web/
  app.js                      # thin orchestrator
  js/
    dom.js
    state.js
    constants.js
    utils.js
    router/viewRouter.js
    services/api.js
    components/
      metrics.js
      shortlist.js
      recordsTable.js
      fairness.js
      columns.js
      mapKazakhstan.js
      drawer.js
      charts.js
  index.html
  styles.css
Data.xlsx
```

## ML и скоринг

Основной supervised режим:
- stacking ensemble (`XGBoost`, `LightGBM`, `CatBoost`, если доступны),
- SHAP explainability,
- fallback режимы при недоступности части backend’ов,
- unsupervised fallback при отсутствии валидного target.

Формула финального скора:

```text
FinalScore = 0.60*ML + 0.20*Compliance + 0.12*Growth + 0.08*FraudSafety
```

## API

Базовый URL: `http://localhost:8080`

Служебные:
- `GET /health`
- `GET /api/diagnostics`

Скоринг:
- `POST /api/score`
  - query: `shortlist`, `target`, `id`, `region`, `farm_size`, `subsidy_type`, `compact`
  - `compact=1` возвращает облегчённый ответ (без full `records`)
- `GET /api/score/last?compact=1` — последний сохранённый скоринг
- `GET /api/top`
- `GET /api/records?page=&page_size=&region=&farm_size=&subsidy_type=`
- `GET /api/feature-importance`
- `GET /api/scenario/simulate`

Комиссия и аудит:
- `POST /api/decisions`
- `GET /api/decisions/{application_id}`
- `GET /api/audit/{application_id}`

Отчёт:
- `GET /api/reports/{application_id}.pdf?lang=ru|kz`

## Stateful поведение

- Результат последнего скоринга сохраняется в:
  - `.runtime/state/last_score_response.json`
- При старте сервиса состояние автоматически поднимается.

## Frontend

Ключевые вещи:
- экранная навигация (overview / shortlist / records / analytics / geo),
- серверная пагинация таблицы заявителей,
- прогресс-бар на время скоринга,
- PDF-кнопки:
  - в drawer,
  - в карточках shortlist,
  - в строках большой таблицы,
- карта Казахстана (SVG), фильтр по региону кликом.

## Live enrichment (опционально)

### По умолчанию

Ничего настраивать не нужно. Система работает без внешних источников.

### Если хотите дергать внешние endpoint’ы на каждый скоринг

Настройте env переменные для источников (egov/stat/weather/market).  
Тогда на каждом `POST /api/score` добавятся фичи:
- `fe_ext_egov`
- `fe_ext_statgov`
- `fe_ext_weather`
- `fe_ext_market`

Пример для одного источника:

```bash
export AGRISCORE_EGOV_REGION_STATS_URL="https://your-endpoint.example/api/stats"
export AGRISCORE_EGOV_REGION_KEY="region"
export AGRISCORE_EGOV_VALUE_KEY="value"
# если endpoint принимает регион как query param:
export AGRISCORE_EGOV_QUERY_REGION_PARAM="region"
```

Аналогичные группы переменных:
- `AGRISCORE_STAT_*`
- `AGRISCORE_WEATHER_*`
- `AGRISCORE_MARKET_*`

Поведение fail-safe:
- если внешний API не отвечает/ошибка/таймаут, скоринг не падает.

## Запуск

```bash
cd /Users/dauletermukhanov/Documents/PugErm
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
MPLCONFIGDIR=.runtime/matplotlib .venv/bin/python cmd/server/main.py
```

Открыть:
- `http://localhost:8080`

## Быстрая проверка

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/diagnostics
curl "http://localhost:8080/api/score/last?compact=1"
```

## Troubleshooting

### LightGBM на macOS

Если ошибка `libomp.dylib`:

```bash
brew install libomp
```

### Медленный скоринг

Это ожидаемо на больших данных: stacking + CV + SHAP + rules/fairness.  
Для демо используйте `compact=1` и серверную пагинацию (уже включено во фронте).
