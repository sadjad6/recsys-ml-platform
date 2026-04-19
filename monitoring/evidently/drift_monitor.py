"""
Evidently Drift Monitoring Script.

This script compares the latest feature store snapshot with the reference
dataset from the last training run to detect data and target drift.
"""

import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime

# Evidently components
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset, DataQualityPreset

logger = logging.getLogger(__name__)

# Paths
REFERENCE_DATA_PATH = os.getenv("REFERENCE_DATA_PATH", "/app/data/training/reference.parquet")
CURRENT_DATA_PATH = os.getenv("CURRENT_DATA_PATH", "/app/data/feature_store/latest.parquet")
REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", "/app/monitoring/evidently/reports")

def generate_mock_data():
    """Generate mock data for demonstration if parquet files don't exist."""
    np.random.seed(42)
    n_samples = 1000
    
    ref_df = pd.DataFrame({
        'user_interaction_count': np.random.poisson(lam=5, size=n_samples),
        'item_popularity': np.random.poisson(lam=100, size=n_samples),
        'target_rating': np.random.normal(loc=3.5, scale=1.0, size=n_samples)
    })
    
    # Current df with slight drift
    curr_df = pd.DataFrame({
        'user_interaction_count': np.random.poisson(lam=7, size=n_samples), # Drifted
        'item_popularity': np.random.poisson(lam=100, size=n_samples),
        'target_rating': np.random.normal(loc=3.2, scale=1.2, size=n_samples) # Drifted
    })
    
    return ref_df, curr_df

def run_drift_analysis():
    """Run Evidently analysis and generate HTML report."""
    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    
    logger.info("Loading reference and current datasets...")
    # In production, read from Parquet
    # ref_df = pd.read_parquet(REFERENCE_DATA_PATH)
    # curr_df = pd.read_parquet(CURRENT_DATA_PATH)
    ref_df, curr_df = generate_mock_data()
    
    logger.info("Configuring Evidently Report...")
    drift_report = Report(metrics=[
        DataQualityPreset(),
        DataDriftPreset(),
        TargetDriftPreset()
    ])
    
    logger.info("Running drift computation...")
    # Assume 'target_rating' is the target column
    drift_report.run(reference_data=ref_df, current_data=curr_df, column_mapping=None)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORT_OUTPUT_DIR, f"drift_report_{timestamp}.html")
    
    logger.info(f"Saving drift report to {report_path}")
    drift_report.save_html(report_path)
    
    # Extract metrics as JSON for pushing to Prometheus or triggering retraining
    drift_dict = drift_report.as_dict()
    
    # In a real pipeline, we would parse drift_dict to see if any feature drifted
    # and push metrics to a Prometheus Pushgateway
    logger.info("Drift analysis completed successfully.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_drift_analysis()
