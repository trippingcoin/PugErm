# PugErm

Веб-платформа для merit-based скоринга сельхозпроизводителей. Backend на FastAPI (Python), ML-пайплайн на Python, интерфейс на HTML/CSS/JS.

## Быстрый старт

1. Установить зависимости:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r ml/requirements.txt
```

2. Запустить сервер на Python:
```bash
python3 cmd/server/main.py
```

Откройте `http://localhost:8080`. Можно загрузить свой файл или использовать `Data.xlsx`.

## Конфигурация

Переменные окружения:
- `ADDR` — адрес сервера (по умолчанию `:8080`)
- `PYTHON_BIN` — путь к Python (по умолчанию `python3`)
- `ML_SCRIPT` — путь к ML-скрипту (по умолчанию `ml/score.py`)

Параметры API:
- `POST /api/score?target=...&id=...&shortlist=...`
  - `target` — название колонки-цели для supervised режима
  - `id` — название колонки идентификатора
  - `shortlist` — размер shortlist
