"""Probe TopStep API for a recent trade and dump the raw response keys."""
import os, json, asyncio, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load env vars from .env manually (avoid dotenv stack-frame issue in heredoc)
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Force the populated DB at project root so login can log to DB
os.environ["DATABASE_URL"] = f"sqlite:///{ROOT / 'topstepbot.db'}"

from backend.services.topstep_client import topstep_client


async def main():
    await topstep_client.startup()
    ok = await topstep_client.login()
    print(f"login ok: {ok}")
    if not ok:
        return
    accounts = await topstep_client.get_accounts()
    print(f"accounts: {[(a.get('id'), a.get('name')) for a in accounts]}")

    for acc in accounts:
        aid = acc.get('id')
        fills = await topstep_client.get_historical_trades(aid, days=7, use_cache=False)
        print(f"\n=== Account {aid} ({acc.get('name')}) - {len(fills)} fills (7d) ===")
        if not fills:
            continue

        all_keys = set()
        for f in fills:
            all_keys.update(f.keys())
        print(f"Keys observed: {sorted(all_keys)}")

        entry = next((f for f in fills if f.get('profitAndLoss') is None), None)
        exit_ = next((f for f in fills if f.get('profitAndLoss') is not None), None)
        if entry:
            print(f"\nEntry sample:\n{json.dumps(entry, indent=2, default=str)}")
        if exit_:
            print(f"\nExit sample:\n{json.dumps(exit_, indent=2, default=str)}")

    await topstep_client.shutdown() if hasattr(topstep_client, 'shutdown') else None


if __name__ == "__main__":
    asyncio.run(main())
