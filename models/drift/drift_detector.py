"""
RecSys ML Platform — Drift Detection.

Uses Evidently to compute Data Drift and Model Drift between reference
datasets (training data) and current datasets (latest feature store snapshot).
"""

import os
import pandas as pd
import mlflow
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset

class DriftDetector:
    def __init__(self, reference_data_path: str, current_data_path: str):
        self.reference_data = pd.read_parquet(reference_data_path)
        self.current_data = pd.read_parquet(current_data_path)
        
    def detect_data_drift(self, output_html_path: str) -> bool:
        """Run data drift detection and save report."""
        print("Running data drift detection...")
        
        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=self.reference_data, current_data=self.current_data)
        
        os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
        report.save_html(output_html_path)
        
        # Log to MLflow if active run exists
        if mlflow.active_run():
            mlflow.log_artifact(output_html_path, "drift_reports")
            
        # Parse result to return boolean indicator of drift
        result = report.as_dict()
        dataset_drift = result["metrics"][0]["result"]["dataset_drift"]
        
        print(f"Data Drift detected: {dataset_drift}")
        return dataset_drift

    def detect_target_drift(self, output_html_path: str) -> bool:
        """Run target drift detection and save report."""
        print("Running target drift detection...")
        
        # Ensure label column exists
        if "label" not in self.reference_data.columns or "label" not in self.current_data.columns:
            print("Warning: 'label' column missing. Skipping target drift detection.")
            return False
            
        report = Report(metrics=[TargetDriftPreset()])
        report.run(reference_data=self.reference_data, current_data=self.current_data)
        
        os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
        report.save_html(output_html_path)
        
        if mlflow.active_run():
            mlflow.log_artifact(output_html_path, "drift_reports")
            
        result = report.as_dict()
        target_drift = result["metrics"][0]["result"]["drift_by_columns"]["label"]["drift_detected"]
        
        print(f"Target Drift detected: {target_drift}")
        return target_drift
