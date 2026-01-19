"""
Price Cache Service - In-memory cache for current prices.

Batches API calls to reduce load and provides near real-time prices
for unrealized PnL calculations.
"""

from datetime import datetime
from typing import Dict, Optional
import asyncio
import logging

logger = logging.getLogger("topstepbot")


class PriceCache:
    """
    In-memory cache for current prices.
    Batches API calls to reduce load.
    """
    
    def __init__(self):
        self._cache: Dict[str, dict] = {}  # {contract_id: {price, timestamp}}
        self._cache_ttl = 10  # seconds (increased from 5 to reduce API calls)
        self._stale_ttl = 60  # Keep stale prices for 60 seconds as fallback
    
    def get_price(self, contract_id: str, allow_stale: bool = False) -> Optional[float]:
        """
        Get cached price.
        
        Args:
            contract_id: Contract to look up
            allow_stale: If True, return stale price if fresh one unavailable
            
        Returns:
            Cached price or None
        """
        if contract_id in self._cache:
            entry = self._cache[contract_id]
            age = (datetime.now() - entry["timestamp"]).total_seconds()
            
            # Fresh price
            if age < self._cache_ttl:
                return entry["price"]
            
            # Stale but still usable as fallback
            if allow_stale and age < self._stale_ttl:
                logger.debug(f"Using stale price for {contract_id} (age: {age:.1f}s)")
                return entry["price"]
        
        return None
    
    def set_price(self, contract_id: str, price: float):
        """Store price in cache."""
        self._cache[contract_id] = {
            "price": price,
            "timestamp": datetime.now()
        }
    
    async def refresh_prices(self, contract_ids: list, topstep_client, is_simulated: bool = True):
        """
        Batch refresh prices for all given contracts.
        
        Args:
            contract_ids: List of contract IDs to refresh
            topstep_client: TopStepClient instance for API calls
            is_simulated: Whether accounts are simulated (affects API call)
        """
        if not contract_ids:
            return
            
        logger.debug(f"Refreshing prices for {len(contract_ids)} contracts: {contract_ids}")
        
        success_count = 0
        for contract_id in contract_ids:
            price = await topstep_client.get_current_price(contract_id, is_simulated=is_simulated)
            if price is not None:
                self.set_price(contract_id, price)
                success_count += 1
            else:
                # Log failure but keep any existing stale price
                existing = self._cache.get(contract_id)
                if existing:
                    age = (datetime.now() - existing["timestamp"]).total_seconds()
                    logger.warning(
                        f"Failed to refresh price for {contract_id}, "
                        f"keeping stale price (age: {age:.1f}s)"
                    )
                else:
                    logger.warning(f"Failed to get price for {contract_id}, no fallback available")
            
            await asyncio.sleep(0.2)  # Increased delay to avoid rate limits
        
        logger.debug(f"Price refresh complete: {success_count}/{len(contract_ids)} successful")

    
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

