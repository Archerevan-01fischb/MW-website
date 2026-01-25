# Midwinter Manual Search - Docker Image
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir streamlit anthropic

# Copy application files
COPY web_search_app.py .
COPY midwinter_unified.db .

# Expose Streamlit port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "web_search_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
