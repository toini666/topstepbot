# Task List

- [/] Restore Partial PnL Logic <!-- id: 0 -->
    - [/] Check `backend/routers/webhook.py`- [x] Restore Partial PnL Fixes <!-- id: 2 -->
    - [x] Verify `size` key check in `backend/routers/webhook.py` <!-- id: 13 -->
    - [x] Re-implement PnL existence filter (remove Side filter) <!-- id: 3 -->
- [ ] Verification <!-- id: 4 -->
    - [ ] Restart service <!-- id: 5 -->

- [x] Investigate News Block Issue <!-- id: 6 -->
    - [x] Check `backend/services/calendar_service.py` fetching logic <!-- id: 7 -->
    - [x] Verify timezone handling and date filtering <!-- id: 8 -->
    - [x] Check global settings for news blocking <!-- id: 9 -->

- [x] Fix Calendar Settings UI <!-- id: 10 -->
    - [x] Locate Calendar Settings modal component <!-- id: 11 -->
    - [x] Fix CSS centering and overlay issues <!-- id: 12 -->

- [x] Debug Reconciliation Discrepancy <!-- id: 13 -->
    - [x] Fetch raw trades for account 16630119 <!-- id: 14 -->
    - [x] Check `reconciliation_service` logic for missing historical trades <!-- id: 15 -->
    - [x] Fix sync logic to import missing closed trades <!-- id: 16 -->
