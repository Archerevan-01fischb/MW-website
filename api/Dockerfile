FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir flask flask-cors anthropic
COPY search_api.py .
COPY midwinter_unified.db .
EXPOSE 8500
CMD ["python", "search_api.py"]
