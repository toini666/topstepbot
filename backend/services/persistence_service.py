import json
import os
from typing import Optional
from backend.database import Log, SessionLocal

PERSISTENCE_FILE = os.getenv("PERSISTENCE_FILE", "persistence.json")

def save_state(data: dict):
    """
    Saves the provided dictionary to persistence.json.
    """
    try:
        with open(PERSISTENCE_FILE, 'w') as f:
            json.dump(data, f)
        # print("✅ State persisted.") # Too noisy for every shutdown? Using it for debug is fine.
    except Exception as e:
        print(f"❌ Failed to save state: {e}")

def load_state() -> dict:
    """
    Loads state from persistence.json. Returns empty dict if file not found or error.
    """
    if os.path.exists(PERSISTENCE_FILE):
        try:
            with open(PERSISTENCE_FILE, 'r') as f:
                data = json.load(f)
                print(f"✅ State loaded from {PERSISTENCE_FILE}")
                return data
        except Exception as e:
            print(f"❌ Failed to load state: {e}")
            _log_error(f"Failed to load persistence file: {e}")
    return {}

def _log_error(message):
    db = SessionLocal()
    try:
        db.add(Log(level="ERROR", message=message))
        db.commit()
    finally:
        db.close()


def save_ngrok_url(url: str):
    """
    Saves the Ngrok URL to persistence.
    Merges with existing state to avoid overwriting other data.
    """
    state = load_state()
    state["last_ngrok_url"] = url
    save_state(state)


def get_last_ngrok_url() -> Optional[str]:
    """
    Retrieves the last known Ngrok URL from persistence.
    Returns None if not found.
    """
    state = load_state()
    return state.get("last_ngrok_url")

