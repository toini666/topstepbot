
import logging
import asyncio
from backend.database import SessionLocal, TickerMap, Log
from backend.services.topstep_client import topstep_client
from backend.services.telegram_service import telegram_service

logger = logging.getLogger("topstepbot")

class ContractValidator:
    """
    Validates that configured contracts in TickerMap are still available/active 
    in the Topstep API.
    """
    
    @staticmethod
    async def validate_active_mappings():
        """
        Daily check: fetches available contracts and compares with local TickerMap.
        Sends an alert for any configured contract that is missing/expired.
        """
        logger.info("Starting Daily Contract Validation...")
        
        db = SessionLocal()
        try:
            # 1. Get all configured mappings
            mappings = db.query(TickerMap).all()
            if not mappings:
                logger.info("Contract Validation: No mappings found in DB. Skipping.")
                return

            # 2. Get all available contracts from Topstep (Live & Sim)
            # This fetches active contracts (live=True and live=False fallback)
            available_contracts = await topstep_client.get_all_computable_contracts()
            
            if not available_contracts:
                logger.error("Contract Validation Failed: Could not fetch active contracts from API.")
                return
                
            # Create a set of available contract NAMES (e.g., "MNQZ5", "MGCG6")
            # and IDs if possible, but mappings usually target the Name/Symbol.
            # API 'name' field usually contains the full ticker with expiry (e.g. "MNQH6")
            available_names = {c.get('name') for c in available_contracts if c.get('name')}
            available_ids = {str(c.get('id')) for c in available_contracts if c.get('id')}

            invalid_mappings = []

            for m in mappings:
                # We check both ts_contract_id and ts_ticker against available names/ids
                # Typically ts_ticker = "MNQZ5" (Contract Name)
                # ts_contract_id might be the ID or Name depending on usage.
                
                is_valid = False
                
                # Check Name Match
                if m.ts_ticker and m.ts_ticker in available_names:
                    is_valid = True
                
                # Check ID Match (if ts_contract_id is numeric or specific ID)
                elif m.ts_contract_id and str(m.ts_contract_id) in available_ids:
                    is_valid = True
                
                # Fallback: Check if ts_contract_id is effectively the name
                elif m.ts_contract_id and m.ts_contract_id in available_names:
                    is_valid = True
                    
                if not is_valid:
                    invalid_mappings.append(m)

            # 3. Alert if invalid found
            if invalid_mappings:
                msg_lines = ["⚠️ <b>CONTRACT EXPIRATION WARNING</b>", ""]
                msg_lines.append("The following configured contracts are no longer listed as 'Available' by Topstep:")
                
                for m in invalid_mappings:
                    msg_lines.append(f"• <b>{m.tv_ticker}</b> mapped to <code>{m.ts_ticker or m.ts_contract_id}</code>")
                
                msg_lines.append("")
                msg_lines.append("<i>Please update your configurations in Ticker Map.</i>")
                
                alert_text = "\n".join(msg_lines)
                
                # Send Configured Alerts
                await telegram_service.send_message(alert_text)
                
                logger.warning(f"Contract Validation found {len(invalid_mappings)} invalid contracts.")
                
                # Log to DB
                db.add(Log(level="WARNING", message=f"Contract Validation: Found {len(invalid_mappings)} expired contracts ({', '.join([m.tv_ticker for m in invalid_mappings])})"))
                db.commit()
            else:
                logger.info("Contract Validation Passed: All configured contracts are available.")
                
        except Exception as e:
            logger.error(f"Contract Validation Error: {e}")
            db.add(Log(level="ERROR", message=f"Contract Validation Error: {e}"))
            db.commit()
        finally:
            db.close()

contract_validator = ContractValidator()
