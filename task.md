# Tasks

- [x] Refine Specification for Breakeven Bug <!-- id: 0 -->
    - [x] Update `specs/bug_fixes_reconciliation_notifications.md` with correct diagnosis (Status Filter). <!-- id: 1 -->
- [x] Implement Reconciliation Fix <!-- id: 2 -->
    - [x] Modify `backend/services/reconciliation_service.py` to handle duplicate detection. <!-- id: 3 -->
- [x] Implement Partial Notification Fix <!-- id: 4 -->
    - [x] Modify `backend/routers/webhook.py` to aggregate split fills. <!-- id: 5 -->
- [x] Implement Breakeven Fix <!-- id: 6 -->
    - [x] Modify `backend/main.py` to filter for active orders only. <!-- id: 7 -->
- [x] Verification <!-- id: 8 -->
    - [x] Restart services and monitor logs. <!-- id: 9 -->
