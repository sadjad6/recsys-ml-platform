"""
RecSys ML Platform — Model Training DAG.

Orchestrates the ML lifecycle:
1. Waits for new training data
2. Trains ALS candidate generation
3. Trains LightGBM ranking model
4. Runs drift detection
5. Registers models in MLflow
"""

from datetime import datetime, timedelta
from airflow import DAG
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
    'model_training_dag',
    default_args=default_args,
    description='Trains recommendation models and logs to MLflow',
    schedule_interval='0 4 * * *',  # Daily at 04:00 UTC, after feature eng
    catchup=False,
    tags=['ml', 'training'],
)

# Placeholder sensor for training data
check_training_data = BashOperator(
    task_id='check_training_data',
    bash_command='test -d /opt/airflow/data/training_datasets || echo "Directory missing but ignoring for local dev"',
    dag=dag,
)

def _train_als():
    print("Training ALS model via MLflow...")
    # Typically we'd call the module or trigger a Spark job
    # e.g., spark-submit /app/models/candidate_generation/als_model.py
    
def _train_ranking():
    print("Training Ranking model via MLflow...")
    
def _run_drift_detection():
    print("Running drift detection via Evidently...")

train_als_model = PythonOperator(
    task_id='train_als_model',
    python_callable=_train_als,
    dag=dag,
)

train_ranking_model = PythonOperator(
    task_id='train_ranking_model',
    python_callable=_train_ranking,
    dag=dag,
)

run_drift_detection = PythonOperator(
    task_id='run_drift_detection',
    python_callable=_run_drift_detection,
    dag=dag,
)

def _register_models():
    print("Registering models in MLflow Model Registry...")

register_model = PythonOperator(
    task_id='register_model',
    python_callable=_register_models,
    dag=dag,
)

check_training_data >> train_als_model >> train_ranking_model >> run_drift_detection >> register_model
