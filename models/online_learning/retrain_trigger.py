"""
Warm-start retraining trigger for Online Learning.
"""

import logging
import httpx
from dataclasses import dataclass
from typing import Tuple
import time

logger = logging.getLogger(__name__)

@dataclass
class RetrainingConfig:
    new_event_threshold: int = 10000
    drift_score_threshold: float = 0.3
    max_hours_since_retrain: float = 48.0
    airflow_api_url: str = "http://airflow:8080/api/v1/dags/warm_start_retrain_dag/dagRuns"
    airflow_auth: tuple = ("admin", "admin")

@dataclass
class SystemStats:
    new_events_count: int
    current_drift_score: float
    hours_since_last_retrain: float

class RetrainingTrigger:
    """Decides when to trigger a full model retrain with warm start."""

    def __init__(self, config: RetrainingConfig):
        self.config = config
        self.last_retrain_time = time.time()
        self.events_since_retrain = 0

    def record_events(self, count: int) -> None:
        """Record processed events."""
        self.events_since_retrain += count

    def should_retrain(self, stats: SystemStats) -> Tuple[bool, str]:
        """Returns (should_retrain, reason)."""
        if stats.new_events_count >= self.config.new_event_threshold:
            return True, f"Event threshold exceeded ({stats.new_events_count} >= {self.config.new_event_threshold})"
            
        if stats.current_drift_score >= self.config.drift_score_threshold:
            return True, f"Drift threshold exceeded ({stats.current_drift_score} >= {self.config.drift_score_threshold})"
            
        if stats.hours_since_last_retrain >= self.config.max_hours_since_retrain:
            return True, f"Time threshold exceeded ({stats.hours_since_last_retrain}h >= {self.config.max_hours_since_retrain}h)"
            
        return False, "Conditions not met"

    def check_and_trigger(self, current_drift_score: float = 0.0) -> bool:
        """Check internal state and trigger if necessary."""
        hours_since = (time.time() - self.last_retrain_time) / 3600.0
        
        stats = SystemStats(
            new_events_count=self.events_since_retrain,
            current_drift_score=current_drift_score,
            hours_since_last_retrain=hours_since
        )
        
        should_retrain, reason = self.should_retrain(stats)
        
        if should_retrain:
            logger.info(f"Triggering warm-start retraining. Reason: {reason}")
            self.trigger_retrain()
            self.last_retrain_time = time.time()
            self.events_since_retrain = 0
            return True
            
        return False

    def trigger_retrain(self) -> None:
        """Trigger Airflow DAG for warm-start retraining via API."""
        try:
            # Example API call to Airflow 2.0+
            # In a real environment, this depends on Airflow's network presence.
            logger.info(f"Sending POST to {self.config.airflow_api_url}")
            # response = httpx.post(
            #     self.config.airflow_api_url,
            #     auth=self.config.airflow_auth,
            #     json={"conf": {"trigger_source": "online_learning"}},
            #     timeout=5.0
            # )
            # response.raise_for_status()
            logger.info("Successfully triggered warm-start DAG (mock).")
        except Exception as e:
            logger.error(f"Failed to trigger retraining DAG: {e}")
