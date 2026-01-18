"""
Price Cache Service - In-memory cache for current prices.

Batches API calls to reduce load and provides near real-time prices
for unrealized PnL calculations.
"""

from datetime import datetime
from typing import Dict, Optional
import asyncio


class PriceCache:
    """
    In-memory cache for current prices.
    Batches API calls to reduce load.
    """
    
    def __init__(self):
        self._cache: Dict[str, dict] = {}  # {contract_id: {price, timestamp}}
        self._cache_ttl = 5  # seconds
    
    def get_price(self, contract_id: str) -> Optional[float]:
        """Get cached price if still valid."""
        if contract_id in self._cache:
            entry = self._cache[contract_id]
            age = (datetime.now() - entry["timestamp"]).total_seconds()
            if age < self._cache_ttl:
                return entry["price"]
        return None
    
    def set_price(self, contract_id: str, price: float):
        """Store price in cache."""
        self._cache[contract_id] = {
            "price": price,
            "timestamp": datetime.now()
        }
    
    async def refresh_prices(self, contract_ids: list, topstep_client):
        """
        Batch refresh prices for all given contracts.
        
        Args:
            contract_ids: List of contract IDs to refresh
            topstep_client: TopStepClient instance for API calls
        """
        for contract_id in contract_ids:
            price = await topstep_client.get_current_price(contract_id)
            if price is not None:
                self.set_price(contract_id, price)
            await asyncio.sleep(0.1)  # Small delay to avoid rate limits
    
    def get_all_prices(self) -> Dict[str, float]:
        """
        Get all currently cached prices (valid or not).
        Useful for debugging.
        """
        return {k: v["price"] for k, v in self._cache.items()}
    
    def clear(self):
        """Clear all cached prices."""
        self._cache = {}


# Global singleton instance
price_cache = PriceCache()
