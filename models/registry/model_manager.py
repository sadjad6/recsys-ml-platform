"""
RecSys ML Platform — MLflow Model Registry Manager.

Provides a wrapper around MLflow Client to handle model registration,
stage transitions, and loading specific model versions.
"""

import os
import mlflow
from mlflow.tracking import MlflowClient

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_URI)

class ModelManager:
    def __init__(self):
        self.client = MlflowClient()

    def register_model(self, name: str, run_id: str, version_desc: str = "") -> mlflow.entities.model_registry.ModelVersion:
        """Register a new model version from a given MLflow run."""
        model_uri = f"runs:/{run_id}/model"
        print(f"Registering model '{name}' from run '{run_id}'")
        
        try:
            # Create registered model if it doesn't exist
            self.client.create_registered_model(name)
        except mlflow.exceptions.RestException:
            pass # Already exists
            
        result = mlflow.register_model(model_uri, name)
        
        if version_desc:
            self.client.update_model_version(
                name=name,
                version=result.version,
                description=version_desc
            )
            
        return result

    def transition_stage(self, name: str, version: int, stage: str, archive_existing: bool = True) -> None:
        """
        Transition a model version to a new stage (e.g., 'Staging', 'Production').
        """
        print(f"Transitioning model '{name}' version {version} to {stage}")
        self.client.transition_model_version_stage(
            name=name,
            version=version,
            stage=stage,
            archive_existing_versions=archive_existing
        )

    def get_production_model_uri(self, name: str) -> str:
        """Get the URI for the current production model."""
        return f"models:/{name}/Production"
        
    def get_model_by_version_uri(self, name: str, version: int) -> str:
        """Get the URI for a specific model version."""
        return f"models:/{name}/{version}"

    def list_versions(self, name: str):
        """List all versions of a registered model."""
        return self.client.search_model_versions(f"name='{name}'")
