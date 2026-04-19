"""
Experimentation Service API Routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from .database import get_db
from .models import Experiment, ExperimentAssignment
from .schemas import (
    ExperimentCreate, 
    ExperimentResponse, 
    ExperimentUpdate,
    AssignGroupResponse,
    MetricEvent,
    ExperimentMetricsResponse,
    GroupMetrics
)
from .assignment import assign_user_to_group
from .metrics import record_metric, get_experiment_metrics, check_significance

router = APIRouter()

@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
async def create_experiment(exp: ExperimentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new experiment."""
    # Check if experiment name exists
    result = await db.execute(select(Experiment).where(Experiment.name == exp.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Experiment name already exists")
        
    db_exp = Experiment(**exp.model_dump())
    db.add(db_exp)
    await db.commit()
    await db.refresh(db_exp)
    return db_exp

@router.get("/experiments", response_model=List[ExperimentResponse])
async def list_experiments(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """List all experiments."""
    result = await db.execute(select(Experiment).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/experiments/{experiment_id}", response_model=ExperimentMetricsResponse)
async def get_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    """Get experiment details and metrics."""
    result = await db.execute(select(Experiment).where(Experiment.experiment_id == experiment_id))
    exp = result.scalars().first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    metrics_data = await get_experiment_metrics(db, experiment_id)
    significance = check_significance(metrics_data["control"]["metrics"], metrics_data["treatment"]["metrics"])
    
    return ExperimentMetricsResponse(
        experiment_id=experiment_id,
        control=GroupMetrics(**metrics_data["control"]),
        treatment=GroupMetrics(**metrics_data["treatment"]),
        significance=significance
    )

@router.put("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: str, exp_update: ExperimentUpdate, db: AsyncSession = Depends(get_db)
):
    """Update experiment status or traffic."""
    result = await db.execute(select(Experiment).where(Experiment.experiment_id == experiment_id))
    exp = result.scalars().first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    update_data = exp_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(exp, key, value)
        
    await db.commit()
    await db.refresh(exp)
    return exp

@router.get("/assign", response_model=AssignGroupResponse)
async def assign_group(
    user_id: str = Query(...), 
    experiment_id: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Assign user to a group for an experiment."""
    # If no experiment ID is provided, try to find an active one
    if not experiment_id:
        result = await db.execute(select(Experiment).where(Experiment.status == "active").order_by(Experiment.created_at.desc()))
        exp = result.scalars().first()
        if not exp:
            return AssignGroupResponse(group="control", model_version="production")
    else:
        result = await db.execute(select(Experiment).where(Experiment.experiment_id == experiment_id))
        exp = result.scalars().first()
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
            
    if exp.status != "active":
        return AssignGroupResponse(group="control", model_version=exp.control_model_version)
        
    group = assign_user_to_group(user_id, exp.experiment_id, exp.traffic_percentage)
    
    if group == "excluded":
        model_version = exp.control_model_version
        assignment_group = "control"
    elif group == "control":
        model_version = exp.control_model_version
        assignment_group = "control"
    else:
        model_version = exp.treatment_model_version
        assignment_group = "treatment"
        
    # Record assignment asynchronously (for real system, consider background tasks)
    # Check if assignment already exists
    assign_check = await db.execute(
        select(ExperimentAssignment).where(
            ExperimentAssignment.user_id == user_id, 
            ExperimentAssignment.experiment_id == exp.experiment_id
        )
    )
    if not assign_check.scalars().first() and group != "excluded":
        assignment = ExperimentAssignment(
            user_id=user_id,
            experiment_id=exp.experiment_id,
            group=group
        )
        db.add(assignment)
        await db.commit()
        
    return AssignGroupResponse(group=assignment_group, model_version=model_version)

@router.post("/experiments/{experiment_id}/metrics")
async def add_metric(experiment_id: str, metric: MetricEvent, db: AsyncSession = Depends(get_db)):
    """Record a metric event."""
    result = await db.execute(select(Experiment).where(Experiment.experiment_id == experiment_id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    await record_metric(db, experiment_id, metric.group, metric.metric_name, metric.value)
    return {"status": "success"}

@router.get("/assign-group", response_model=AssignGroupResponse)
async def assign_group_alias(
    user_id: str = Query(...),
    experiment_id: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Alias for /assign to match Spec.md endpoint contract."""
    return await assign_group(user_id=user_id, experiment_id=experiment_id, db=db)
