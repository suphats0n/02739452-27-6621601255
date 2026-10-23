FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY etl /app/etl
COPY ingestion /app/ingestion
COPY web /app/web
COPY scripts /app/scripts

EXPOSE 8501
CMD ["streamlit", "run", "web/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--theme.base=dark", "--theme.primaryColor=#22D3EE", "--theme.backgroundColor=#080D1A", "--theme.secondaryBackgroundColor=#151F34", "--theme.textColor=#F8FAFC", "--theme.font=sans serif"]
