"""
Strategy Templates Router - CRUD for global strategy definitions.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db, Strategy
from backend.schemas import StrategyCreate, StrategyResponse

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("/", response_model=List[StrategyResponse])
def list_strategies(db: Session = Depends(get_db)):
    """List all strategy templates."""
    return db.query(Strategy).all()


@router.post("/", response_model=StrategyResponse)
def create_strategy(strategy: StrategyCreate, db: Session = Depends(get_db)):
    """Create a new strategy template."""
    # Check for duplicate name
    existing_name = db.query(Strategy).filter(Strategy.name == strategy.name).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="Strategy with this name already exists")
    
    # Check for duplicate TV ID
    existing_id = db.query(Strategy).filter(Strategy.tv_id == strategy.tv_id).first()
    if existing_id:
        raise HTTPException(status_code=400, detail="Strategy with this TradingView ID already exists")
    
    new_strat = Strategy(
        name=strategy.name,
        tv_id=strategy.tv_id,
        default_risk_factor=strategy.default_risk_factor,
        default_allowed_sessions=strategy.default_allowed_sessions,
        default_partial_tp_percent=strategy.default_partial_tp_percent,
        default_move_sl_to_entry=strategy.default_move_sl_to_entry
    )
    db.add(new_strat)
    db.commit()
    db.refresh(new_strat)
    return new_strat


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Get a specific strategy."""
    strat = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strat


@router.put("/{strategy_id}", response_model=StrategyResponse)
def update_strategy(strategy_id: int, strategy: StrategyCreate, db: Session = Depends(get_db)):
    """Update a strategy template."""
    strat = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Check name uniqueness if changed
    if strategy.name != strat.name:
        existing = db.query(Strategy).filter(Strategy.name == strategy.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Strategy with this name already exists")
    
    # Check TV ID uniqueness if changed
    if strategy.tv_id != strat.tv_id:
        existing = db.query(Strategy).filter(Strategy.tv_id == strategy.tv_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Strategy with this TradingView ID already exists")
    
    strat.name = strategy.name
    strat.tv_id = strategy.tv_id
    strat.default_risk_factor = strategy.default_risk_factor
    strat.default_allowed_sessions = strategy.default_allowed_sessions
    strat.default_partial_tp_percent = strategy.default_partial_tp_percent
    strat.default_move_sl_to_entry = strategy.default_move_sl_to_entry
    
    db.commit()
    db.refresh(strat)
    return strat


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Delete a strategy template."""
    strat = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    db.delete(strat)
    db.commit()
    return {"status": "deleted"}
