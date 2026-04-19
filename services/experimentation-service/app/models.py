"""
SQLAlchemy models for Experimentation Service.
"""

from sqlalchemy import Column, String, Integer, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
import uuid

from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Experiment(Base):
    __tablename__ = "experiments"

    experiment_id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="paused")  # "active", "paused", "completed"
    traffic_percentage = Column(Integer, default=50) # 0-100
    control_model_version = Column(String, nullable=False)
    treatment_model_version = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    experiment_id = Column(String, ForeignKey("experiments.experiment_id"), nullable=False)
    group = Column(String, nullable=False) # "control" or "treatment"
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint('user_id', 'experiment_id', name='uix_user_experiment'),)


class ExperimentMetric(Base):
    __tablename__ = "experiment_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(String, ForeignKey("experiments.experiment_id"), nullable=False)
    group = Column(String, nullable=False)
    metric_name = Column(String, nullable=False) # e.g., "ctr", "engagement"
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
