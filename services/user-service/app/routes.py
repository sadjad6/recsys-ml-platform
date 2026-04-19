"""
User Service API Routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from .database import get_db
from .models import User
from .schemas import UserCreate, UserResponse, UserUpdate

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user."""
    # Check if user exists
    result = await db.execute(select(User).where((User.username == user.username) | (User.email == user.email)))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
        
    db_user = User(
        username=user.username,
        email=user.email,
        preferences=user.preferences
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get user by ID."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return user

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List users with pagination."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_update: UserUpdate, db: AsyncSession = Depends(get_db)):
    """Update user preferences."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Update preferences by merging dicts
    current_prefs = user.preferences or {}
    current_prefs.update(user_update.preferences)
    user.preferences = current_prefs
    
    await db.commit()
    await db.refresh(user)
    return user
