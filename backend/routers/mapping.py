from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db, TickerMap
from backend.schemas import TickerMapResponse, TickerMapCreate
from backend.services.topstep_client import topstep_client
import logging

router = APIRouter()

@router.get("/mappings", response_model=List[TickerMapResponse])
def get_mappings(db: Session = Depends(get_db)):
    """List all configured mappings."""
    return db.query(TickerMap).all()

@router.post("/mappings", response_model=TickerMapResponse)
def create_mapping(mapping: TickerMapCreate, db: Session = Depends(get_db)):
    """Create or Update a mapping."""
    # Check if exists
    existing = db.query(TickerMap).filter(TickerMap.tv_ticker == mapping.tv_ticker).first()
    if existing:
        # Update existing
        existing.ts_contract_id = mapping.ts_contract_id
        existing.ts_ticker = mapping.ts_ticker
        existing.tick_size = mapping.tick_size
        existing.tick_value = mapping.tick_value
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        new_map = TickerMap(**mapping.model_dump())
        db.add(new_map)
        db.commit()
        db.refresh(new_map)
        return new_map

@router.delete("/mappings/{id}")
def delete_mapping(id: int, db: Session = Depends(get_db)):
    """Delete a mapping."""
    item = db.query(TickerMap).filter(TickerMap.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    db.delete(item)
    db.commit()
    return {"status": "deleted"}

@router.get("/mappings/available-contracts")
async def get_available_contracts():
    """Fetches currently available contracts from TopStep API for the UI dropdown."""
    # We can perform a broad search or list 'Tradable Objects'
    # Based on client code, we have `get_contract_details` but not a list_all method exposed clearly.
    # However, `get_contract_details` calls `/api/Contract/available`.
    # Let's create a helper to just list them.
    
    # We need to access the private logic or add a method to client.
    # Actually, let's just use the client method I'm about to add or piggyback.
    # Wait, `get_contract_details` filters by ticker.
    # I should add `get_all_contracts` to topstep_client.py first or here?
    # Better to keep API logic in client.
    
    # For now, let's try to search for the main indices to populate the list.
    # Or better, let's IMPLEMENT `get_available_contracts` in TopStepClient.
    
    contracts = await topstep_client.get_all_computable_contracts()
    return contracts
