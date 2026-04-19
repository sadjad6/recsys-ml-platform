"""
Pydantic Schemas for Experimentation Service.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    traffic_percentage: int = Field(50, ge=0, le=100)
    control_model_version: str
    treatment_model_version: str

class ExperimentUpdate(BaseModel):
    status: Optional[str] = None # active, paused, completed
    traffic_percentage: Optional[int] = Field(None, ge=0, le=100)

class ExperimentResponse(BaseModel):
    experiment_id: str
    name: str
    description: Optional[str]
    status: str
    traffic_percentage: int
    control_model_version: str
    treatment_model_version: str
    created_at: datetime
    updated_at: Optional[datetime]

class AssignGroupResponse(BaseModel):
    group: str
    model_version: str

class MetricEvent(BaseModel):
    group: str
    metric_name: str
    value: float = 1.0

class GroupMetrics(BaseModel):
    sample_size: int
    metrics: Dict[str, float]

class ExperimentMetricsResponse(BaseModel):
    experiment_id: str
    control: GroupMetrics
    treatment: GroupMetrics
    significance: Optional[Dict[str, Any]] = None
