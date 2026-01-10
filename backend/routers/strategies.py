from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db, Strategy
from backend.schemas import StrategyCreate, StrategyResponse

router = APIRouter(prefix="/strategies", tags=["strategies"])

@router.get("/", response_model=List[StrategyResponse])
def list_strategies(db: Session = Depends(get_db)):
    return db.query(Strategy).all()

@router.post("/", response_model=StrategyResponse)
def create_strategy(strategy: StrategyCreate, db: Session = Depends(get_db)):
    # Check for duplicate Name
    existing_name = db.query(Strategy).filter(Strategy.name == strategy.name).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="Strategy with this name already exists.")
    
    # Check for duplicate TV ID
    existing_id = db.query(Strategy).filter(Strategy.tv_id == strategy.tv_id).first()
    if existing_id:
        raise HTTPException(status_code=400, detail="Strategy with this TradingView ID already exists.")
    
    new_strat = Strategy(
        name=strategy.name, 
        tv_id=strategy.tv_id, 
        risk_factor=strategy.risk_factor
    )
    db.add(new_strat)
    db.commit()
    db.refresh(new_strat)
    return new_strat

@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    strat = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    db.delete(strat)
    db.commit()
    return {"status": "deleted"}

@router.put("/{strategy_id}", response_model=StrategyResponse)
def update_strategy(strategy_id: int, strategy: StrategyCreate, db: Session = Depends(get_db)):
    strat = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Check for name uniqueness if changed
    if strategy.name != strat.name:
         existing_name = db.query(Strategy).filter(Strategy.name == strategy.name).first()
         if existing_name:
             raise HTTPException(status_code=400, detail="Strategy with this name already exists.")
             
    # Check for TV ID uniqueness if changed
    if strategy.tv_id != strat.tv_id:
         existing_id = db.query(Strategy).filter(Strategy.tv_id == strategy.tv_id).first()
         if existing_id:
             raise HTTPException(status_code=400, detail="Strategy with this TradingView ID already exists.")
    
    strat.name = strategy.name
    strat.tv_id = strategy.tv_id
    strat.risk_factor = strategy.risk_factor
    
    db.commit()
    db.refresh(strat)
    return strat
