FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
ENV PORT=8080
CMD exec gunicorn --bind "0.0.0.0:${PORT}" --workers 1 server:app
