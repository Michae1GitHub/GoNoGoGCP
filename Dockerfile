FROM python:3.11-slim

WORKDIR /app

COPY app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

COPY app/ .

ENV PORT=8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
