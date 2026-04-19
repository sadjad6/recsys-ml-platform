# =============================================================================
# RecSys ML Platform — Spark Job Container
# =============================================================================
# Extends bitnami/spark to include our python code.
#
# Build: docker build -t recsys-spark ./spark
# =============================================================================

FROM bitnami/spark:3.5.0

USER root

# Install any required python packages here if needed.
# bitnami/spark already comes with python and pyspark.
RUN pip install --no-cache-dir pyspark==3.5.0

# Set working directory
WORKDIR /app/spark

# Copy all Spark code
COPY . /app/spark

# Switch back to the non-root user that bitnami uses
USER 1001
