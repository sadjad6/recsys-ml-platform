# =============================================================================
# RecSys ML Platform — Airflow Container
# =============================================================================
# Extends apache/airflow:2.7.2 to include ML, PySpark, and data dependencies.
# =============================================================================

FROM apache/airflow:2.7.2

USER root

# Install OpenJDK-11 for PySpark
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         openjdk-17-jre-headless \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER airflow

# Install python dependencies
RUN pip install --no-cache-dir \
    pyspark==3.5.0 \
    mlflow \
    evidently \
    kafka-python-ng
