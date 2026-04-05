FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ADDR=0.0.0.0:8080 \
    MPLCONFIGDIR=/app/.runtime/matplotlib

WORKDIR /app

RUN mkdir -p /app/ml /app/.runtime/state /app/.runtime/matplotlib

COPY requirements.txt ./requirements.txt
COPY ml/requirements.txt ./ml/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r ml/requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "cmd/server/main.py"]
