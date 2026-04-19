# =============================================================================
# RecSys ML Platform — Kafka Producer/Consumer Container
# =============================================================================
# Python 3.12 slim image with kafka-python for running producers and consumers.
#
# Build:  docker build -t recsys-kafka-tools ./kafka
# Run:    docker run --network recsys-network recsys-kafka-tools \
#           python -m producers.event_producer --eps 10
# =============================================================================

FROM python:3.12-slim

LABEL maintainer="recsys-ml-platform"
LABEL description="Kafka producer/consumer tools for RecSys ML Platform"

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Default command: run the event producer
CMD ["python", "-m", "producers.event_producer"]
