FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY services/shared /app/services/shared

# Copy app code
COPY services/user-service/app /app/app

# Set python path so shared utilities can be imported
ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
