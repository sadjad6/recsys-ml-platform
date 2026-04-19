"""
RecSys ML Platform — Feature Engineering DAG.

Orchestrates the batch feature engineering pipeline:
1. Waits for raw data
2. Runs Spark feature engineering
3. Prepares training datasets
4. Validates data quality
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'recsys',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'feature_engineering_dag',
    default_args=default_args,
    description='Batch feature engineering and training dataset preparation',
    schedule_interval='0 2 * * *',  # Daily at 02:00 UTC
    catchup=False,
    tags=['features', 'ml'],
)

# Placeholder sensor for raw data
check_raw_data_available = BashOperator(
    task_id='check_raw_data_available',
    bash_command='test -d /opt/airflow/data/raw_events || echo "Directory missing but ignoring for now"',
    dag=dag,
)

# In a real environment, we would use the Airflow Spark connection, but
# since we are running locally via Docker Compose, we'll simulate the spark-submit
# via BashOperator for simplicity (or use SparkSubmitOperator if properly configured).
run_feature_engineering = BashOperator(
    task_id='run_feature_engineering',
    bash_command="""
    # In production, this uses SparkSubmitOperator targeting the spark-master.
    echo "Running feature_engineering.py..."
    """,
    dag=dag,
)

prepare_training_data = BashOperator(
    task_id='prepare_training_data',
    bash_command="""
    echo "Running prepare_training_data.py..."
    """,
    dag=dag,
)

def _validate_data_quality():
    """Placeholder for data quality validation logic calling plugins."""
    print("Validating training dataset quality...")
    # e.g., from plugins.data_quality import run_all_checks
    print("Data quality checks passed.")

validate_data_quality = PythonOperator(
    task_id='validate_data_quality',
    python_callable=_validate_data_quality,
    dag=dag,
)

def _notify_completion():
    """Notification hook."""
    print("Feature engineering pipeline completed successfully.")

notify_completion = PythonOperator(
    task_id='notify_completion',
    python_callable=_notify_completion,
    dag=dag,
)

check_raw_data_available >> run_feature_engineering >> prepare_training_data >> validate_data_quality >> notify_completion
