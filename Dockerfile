FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ADDR=0.0.0.0:8080

WORKDIR /app

COPY requirements.txt ml/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r ml/requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "cmd/server/main.py"]
