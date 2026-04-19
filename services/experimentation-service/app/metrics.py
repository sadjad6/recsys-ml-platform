"""
Metrics tracking and aggregation for experiments.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from collections import defaultdict
import logging

from .models import ExperimentMetric, ExperimentAssignment

logger = logging.getLogger(__name__)

async def record_metric(db: AsyncSession, experiment_id: str, group: str, metric_name: str, value: float) -> None:
    """Record a single metric event."""
    metric = ExperimentMetric(
        experiment_id=experiment_id,
        group=group,
        metric_name=metric_name,
        metric_value=value
    )
    db.add(metric)
    await db.commit()

async def get_experiment_metrics(db: AsyncSession, experiment_id: str) -> dict:
    """
    Aggregate metrics per group.
    Returns:
      {
        "control": {"ctr": 0.032, "engagement": 0.15, "sample_size": 5000},
        "treatment": {"ctr": 0.041, "engagement": 0.18, "sample_size": 4800}
      }
    """
    # 1. Get sample sizes (number of assignments per group)
    assignment_query = select(ExperimentAssignment.group, func.count(ExperimentAssignment.id)).where(
        ExperimentAssignment.experiment_id == experiment_id
    ).group_by(ExperimentAssignment.group)
    
    assignment_result = await db.execute(assignment_query)
    sample_sizes = {row[0]: row[1] for row in assignment_result.all()}
    
    # 2. Get sum of metrics per group and metric_name
    metrics_query = select(
        ExperimentMetric.group, 
        ExperimentMetric.metric_name, 
        func.sum(ExperimentMetric.metric_value)
    ).where(
        ExperimentMetric.experiment_id == experiment_id
    ).group_by(ExperimentMetric.group, ExperimentMetric.metric_name)
    
    metrics_result = await db.execute(metrics_query)
    
    # Structure the output
    output = {
        "control": {"sample_size": sample_sizes.get("control", 0), "metrics": {}},
        "treatment": {"sample_size": sample_sizes.get("treatment", 0), "metrics": {}}
    }
    
    for row in metrics_result.all():
        group = row[0]
        metric_name = row[1]
        metric_sum = row[2]
        
        # Calculate average (e.g. sum(clicks) / sample_size)
        sample_size = sample_sizes.get(group, 0)
        if sample_size > 0:
            avg_val = metric_sum / sample_size
            if group in output:
                output[group]["metrics"][metric_name] = round(avg_val, 4)
                
    return output

def check_significance(control_metrics: dict, treatment_metrics: dict) -> dict:
    """
    Run basic statistical significance test placeholder.
    In a real system, this would use scipy.stats.
    """
    # Placeholder for actual significance testing
    return {
        "significant": False, 
        "p_value": 1.0, 
        "confidence": 0.0
    }
