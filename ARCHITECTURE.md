# Архитектура PugErm

## Назначение

PugErm — это explainable AI-прототип для Case 2: ранжирование заявок на субсидии сельхозпроизводителей с формированием shortlist для комиссии.

Система не принимает решение вместо человека. Она помогает эксперту быстрее увидеть приоритетные заявки и понять, почему они оказались выше или ниже в ранжировании.

## Основные компоненты

### 1. Frontend

Файлы:
- `web/index.html`
- `web/app.js`
- `web/styles.css`
- `web/js/*`

Функции:
- загрузка XLSX/CSV,
- запуск скоринга,
- отображение summary,
- отображение глобальных факторов,
- отображение shortlist,
- отображение fairness и ranking-метрик,
- показ используемых и исключённых полей,
- отображение таблицы заявителей,
- карта регионов,
- PDF-отчёт по заявителю,
- RU/KZ переключение интерфейса.

### 2. Backend API

Файлы:
- `cmd/server/main.py`
- `app/api/routes.py`

Функции:
- отдаёт веб-интерфейс,
- принимает `POST /api/score`,
- сохраняет загруженный файл во временную директорию,
- вызывает scoring service внутри приложения,
- возвращает JSON-результат во frontend.

### 3. ML Scoring Engine

Файлы:
- `app/services/scoring_service.py`
- `app/models/trainer.py`
- `app/data/features.py`
- `app/services/rules.py`
- `ml/score.py` (`CLI`-обертка для локального запуска)

Функции:
- читает XLSX/CSV,
- очищает данные,
- исключает технические поля,
- подготавливает признаки,
- запускает supervised/proxy-supervised/unsupervised scoring,
- рассчитывает финальный score,
- выделяет глобальные и локальные факторы,
- рассчитывает compliance / eligibility / fraud / growth сигналы,
- формирует shortlist.

## Поток данных

1. Пользователь открывает веб-интерфейс.
2. Загружает файл или использует встроенный `Data.xlsx`.
3. Frontend отправляет `POST /api/score`.
4. Backend вызывает `ScoringService.run_scoring(...)`.
5. Сервис:
   - загружает данные,
   - удаляет пустые поля,
   - исключает идентификаторы и технические колонки,
   - строит признаки,
   - определяет доступный режим обучения,
   - запускает ML ranking,
   - применяет compliance / eligibility / fraud / growth слой,
   - формирует explanations,
   - возвращает JSON.
6. Backend отдаёт JSON во frontend.
7. Frontend показывает shortlist, summary, факторы, карту, аналитику и PDF.

## Режимы скоринга

### 1. Supervised ranking

Если есть валидный `target`, используется stacking ensemble:
- `XGBoost`
- `LightGBM`
- `CatBoost`
- meta-model поверх out-of-fold predictions

Explainability:
- глобальная importance,
- локальные SHAP-факторы,
- breakdown итогового скора.

### 2. Proxy-supervised ranking

Если явного target нет, система пытается построить proxy-target:
- по статусу,
- по utility-сигналу статуса и суммы,
- по amount-based proxy.

Это не “идеальный ground truth”, а прагматичный fallback для реальных госданных.

### 3. Unsupervised fallback

Если supervised target отсутствует полностью:
- используется `TruncatedSVD`,
- строится latent ranking signal,
- система остаётся рабочей и explainable.

## Финальная логика score

Итоговый score собирается из нескольких слоев:

```text
FinalScore = 0.60*ML + 0.20*Compliance + 0.12*Growth + 0.08*FraudSafety
```

Дополнительно:
- eligibility failures дают сильный penalty,
- rule-based policy checks остаются видимыми для комиссии,
- окончательное решение принимает человек.

## Логика explainability

Explainability реализован на двух уровнях:

- Глобальный уровень:
  показывает, какие признаки сильнее всего влияют на ранжирование в целом.

- Локальный уровень:
  показывает top factors для конкретной записи, чтобы комиссия понимала причину высокого или низкого score.

Дополнительно в интерфейсе показываются:
- используемые поля,
- исключённые поля и причины исключения.

Также доступны:
- PDF-отчёт по заявителю,
- compliance flags,
- fairness summary,
- ranking metrics против FCFS baseline.

## Regulatory слой

Нормативная логика применяется через кодовые справочники и rules:
- допустимые нормы,
- субсидийные программы,
- eligibility и consistency checks,
- отдельные anti-fraud сигналы.

Важно:
- `.regulatory` PDF не парсятся автоматически в рантайме;
- в scoring используются уже вынесенные в код нормативные данные.

## Почему решение соответствует финальному прототипу

В репозитории уже есть:
- рабочий scoring engine,
- web dashboard,
- explainable AI,
- human-in-the-loop decision flow,
- audit trail,
- PDF export,
- state restore после рестарта,
- Docker-запуск.

## Ограничения архитектуры

- Пока нет БД и постоянного хранения результатов.
- Пока нет очереди задач и фоновой обработки.
- Пока нет аутентификации и разграничения ролей.
- ML-режим сильно зависит от качества входного `target` или proxy-target.
- `.regulatory` документы пока не используются как автоматический NLP-source.
- На больших объёмах данных возможны задержки ответа.

## Расширение на следующие этапы

Архитектура может быть усилена без полной переделки:
- добавить хранилище результатов и версий модели,
- вынести scoring engine в отдельный сервис,
- добавить feature store или слой подготовки данных,
- подключить более сильную supervised-модель,
- добавить экспорт shortlist и журнал аудита решений.
