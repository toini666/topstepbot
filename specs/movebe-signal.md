# MOVEBE Signal — Move Stop Loss to Break Even

## Executive Summary

Ajout d'un nouveau type d'alerte webhook `MOVEBE` (Move to Break Even) dans le système de trading. Lorsqu'un signal TradingView de type `MOVEBE` est reçu, le bot recherche les positions ouvertes correspondantes (même ticker, timeframe et stratégie) et déplace leur stop loss au prix d'entrée (break even) pour protéger la position. Ce type de signal ne contient ni TP ni stop — il réutilise le prix d'entrée enregistré dans le trade.

**Cas d'usage :** Le prix évolue favorablement sur une position ouverte, mais n'a pas encore atteint le take profit. TradingView envoie un signal `MOVEBE` pour sécuriser la position en bougeant le SL au break even.

---

## Business Requirements

| ID | Requirement |
|----|-------------|
| BR-1 | Le webhook doit accepter un nouveau type `MOVEBE` dans le champ `type` du payload |
| BR-2 | Le payload `MOVEBE` ne nécessite PAS de champs `stop` et `tp` (ils sont ignorés s'ils sont présents) |
| BR-3 | Le handler doit trouver les positions ouvertes correspondantes via les mêmes critères que PARTIAL/CLOSE : `ticker` + `timeframe` + `strategy` |
| BR-4 | Pour chaque trade matching, le SL doit être modifié au `entry_price` du trade (prix d'entrée réel post-fill, pas le signal_entry_price) |
| BR-5 | Le TP existant doit rester inchangé |
| BR-6 | Une notification Telegram doit être envoyée : signal reçu + confirmation d'exécution par compte |
| BR-7 | L'événement doit être loggé dans les system logs (table `Log`) |
| BR-8 | Si aucune position ouverte ne correspond, le signal est ignoré silencieusement (pas de notification, simple log INFO) |
| BR-9 | S'il y a un échec sur l'API TopStep lors de la modification, logger l'erreur et continuer avec les autres comptes |
| BR-10 | Le `MockWebhookModal` dans le frontend doit supporter le type `MOVEBE` |

---

## User Stories

### US-1: Move SL to Break Even via Webhook
**En tant que** trader automatisé,
**Je veux** recevoir un signal `MOVEBE` de TradingView qui déplace le stop loss de mes positions ouvertes au break even,
**Afin de** protéger mes gains latents sans fermer la position.

**Critères d'acceptation :**
- Le signal `MOVEBE` est correctement parsé et routé
- Le SL est modifié au prix d'entrée du trade sur TopStep
- Le TP reste inchangé
- Une notification Telegram confirme l'action
- L'action est loggée dans les system logs

### US-2: Silent Skip When No Position
**En tant que** trader,
**Je veux** que le signal `MOVEBE` soit ignoré silencieusement quand aucune position ne correspond,
**Afin d'** éviter les alertes inutiles.

---

## Technical Architecture

### Alert Payload

```json
{
  "type": "MOVEBE",
  "ticker": "MNQ1!",
  "side": "BUY",
  "entry": 20000.00,
  "timeframe": "M5",
  "strat": "rob_rev"
}
```

> **Note :** Les champs `stop` et `tp` sont optionnels et ignorés pour ce type.

---

### Schema Changes

#### [MODIFY] [schemas.py](file:///Users/awagon/Documents/dev/topstepbot/backend/schemas.py)

Le `TradingViewAlert` est déjà compatible — `stop` et `tp` sont `Optional`. Aucune modification de schéma n'est requise. Le commentaire du champ `type` sera mis à jour pour inclure `MOVEBE`.

```diff
- type: str  # SETUP, SIGNAL, PARTIAL, CLOSE
+ type: str  # SETUP, SIGNAL, PARTIAL, CLOSE, MOVEBE
```

---

### Webhook Router Changes

#### [MODIFY] [webhook.py](file:///Users/awagon/Documents/dev/topstepbot/backend/routers/webhook.py)

**1. Routing dans `receive_webhook`** — Ajouter le routage pour `MOVEBE` :

```python
elif alert_type == "MOVEBE":
    return await handle_movebe(alert, db)
```

**2. Nouveau handler `handle_movebe`** — Suit le même pattern que `handle_close` mais modifie le SL au lieu de fermer la position :

```python
async def handle_movebe(alert: TradingViewAlert, db: Session) -> Dict[str, Any]:
    """
    MOVEBE: Move stop loss to break even (entry price) for matching positions.
    Matches on ticker + timeframe + strategy.
    """
    strategy_name = alert.strat or "default"
    from backend.services.telegram_service import telegram_service

    # Find matching open trades
    matching_trades = db.query(Trade).filter(
        Trade.ticker == alert.ticker,
        Trade.timeframe == alert.timeframe,
        Trade.strategy == strategy_name,
        Trade.status == TradeStatus.OPEN
    ).all()

    if not matching_trades:
        db.add(Log(level="INFO", message=f"MOVEBE: No matching position for {alert.ticker} TF={alert.timeframe} [{strategy_name}]"))
        db.commit()
        return {"status": "skipped", "reason": "No matching position"}

    # Notify signal received
    await telegram_service.notify_movebe_signal(
        ticker=alert.ticker,
        timeframe=alert.timeframe,
        strategy=strategy_name,
        price=alert.entry
    )

    db.add(Log(level="INFO", message=f"MOVEBE: Found {len(matching_trades)} matching trade(s) for {alert.ticker}"))

    processed = []

    for trade in matching_trades:
        account_id = trade.account_id

        try:
            # Verify position still exists on TopStep
            positions = await topstep_client.get_open_positions(account_id)
            clean_ticker = alert.ticker.replace("1!", "").replace("2!", "").upper()

            matching_pos = None
            for pos in positions:
                if clean_ticker in pos.get('contractId', '').upper():
                    matching_pos = pos
                    break

            if not matching_pos:
                db.add(Log(level="WARNING", message=f"MOVEBE: No open position on TopStep for {alert.ticker} on account {account_id}"))
                continue

            # Move SL to entry price (break even)
            entry_price = trade.entry_price
            if not entry_price:
                db.add(Log(level="WARNING", message=f"MOVEBE: No entry price for trade {trade.id}"))
                continue

            # Update SL to entry price, keep TP unchanged
            await topstep_client.update_sl_tp_orders(
                account_id=account_id,
                ticker=alert.ticker,
                sl_price=entry_price,
                tp_price=trade.tp if trade.tp else 0  # Keep existing TP
            )

            # Get account name
            account_settings = db.query(AccountSettings).filter(
                AccountSettings.account_id == account_id
            ).first()
            account_name = (account_settings.account_name 
                          if account_settings and account_settings.account_name 
                          else str(account_id))

            db.add(Log(level="INFO", message=f"MOVEBE: SL moved to BE ({entry_price}) for {alert.ticker} on {account_name}"))

            # Notify per-account execution
            await telegram_service.notify_movebe_executed(
                ticker=alert.ticker,
                entry_price=entry_price,
                account_name=account_name
            )

            processed.append(account_name)

        except Exception as e:
            db.add(Log(level="ERROR", message=f"MOVEBE failed for account {account_id}: {e}"))

    db.commit()

    if processed:
        return {"status": "processed", "accounts": processed, "type": "MOVEBE"}
    return {"status": "skipped", "reason": "No positions processed"}
```

---

### Telegram Notifications

#### [MODIFY] [telegram_service.py](file:///Users/awagon/Documents/dev/topstepbot/backend/services/telegram_service.py)

Ajouter 2 nouvelles méthodes à `TelegramService` :

**1. `notify_movebe_signal`** — Notification à la réception du signal :

```python
async def notify_movebe_signal(self, ticker: str, timeframe: str, strategy: str, price: float = None):
    """Notify of incoming MOVEBE signal."""
    msg = (
        f"🔒 <b>MOVEBE Signal</b>\n\n"
        f"• Ticker: <b>{ticker}</b>\n"
        f"• Timeframe: {timeframe}\n"
        f"• Strategy: {strategy}\n"
    )
    if price:
        msg += f"• Price: {price}\n"
    await self.send_message(msg)
    await self._log_info(f"📤 Telegram: MOVEBE signal for {ticker} [{strategy}] TF={timeframe}")
```

**2. `notify_movebe_executed`** — Notification par compte après exécution :

```python
async def notify_movebe_executed(self, ticker: str, entry_price: float, account_name: str = None):
    """Notify SL moved to break even."""
    msg = (
        f"✅ <b>SL → Break Even</b>\n\n"
        f"• Ticker: <b>{ticker}</b>\n"
        f"• SL moved to: {entry_price}\n"
    )
    if account_name:
        msg += f"• Account: {account_name}\n"
    await self.send_message(msg)
    await self._log_info(f"📤 Telegram: MOVEBE executed for {ticker} on {account_name}")
```

---

### Frontend Changes

#### [MODIFY] [MockWebhookModal.tsx](file:///Users/awagon/Documents/dev/topstepbot/frontend/src/components/MockWebhookModal.tsx)

Ajouter `MOVEBE` au tableau des types d'alertes et masquer SL/TP quand `MOVEBE` est sélectionné :

```diff
- const ALERT_TYPES = ['SETUP', 'SIGNAL', 'PARTIAL', 'CLOSE'] as const;
+ const ALERT_TYPES = ['SETUP', 'SIGNAL', 'PARTIAL', 'CLOSE', 'MOVEBE'] as const;
```

```diff
- const showSlTp = formData.type === 'SIGNAL' || formData.type === 'PARTIAL';
+ const showSlTp = formData.type === 'SIGNAL' || formData.type === 'PARTIAL';  // MOVEBE: no SL/TP
```

Ajouter la couleur pour `MOVEBE` dans le dropdown et le bouton submit (couleur : `blue-400` / `blue-600`).

Ajustement du payload pour ne pas envoyer `stop`/`tp` quand type est `MOVEBE` :

```diff
- stop: formData.type === 'CLOSE' ? null : parseNumber(formData.sl),
- tp: formData.type === 'CLOSE' ? null : parseNumber(formData.tp),
+ stop: ['CLOSE', 'MOVEBE'].includes(formData.type) ? null : parseNumber(formData.sl),
+ tp: ['CLOSE', 'MOVEBE'].includes(formData.type) ? null : parseNumber(formData.tp),
```

---

### Unit Tests

#### [MODIFY] [test_webhook.py](file:///Users/awagon/Documents/dev/topstepbot/tests/unit/test_webhook.py)

Ajouter un test pour le parsing correct du payload `MOVEBE` :

```python
def test_valid_movebe_alert(self):
    """Test parsing a valid MOVEBE alert."""
    from backend.schemas import TradingViewAlert
    
    alert = TradingViewAlert(
        ticker="MNQ1!",
        type="MOVEBE",
        side="BUY",
        entry=20000.00,
        strat="rob_rev",
        timeframe="M5"
    )
    
    assert alert.type == "MOVEBE"
    assert alert.stop is None
    assert alert.tp is None
    assert alert.ticker == "MNQ1!"
```

---

## Data Flow Diagram

```
TradingView                    Webhook Router                     TopStep API
    │                               │                                  │
    │── POST {type:"MOVEBE"} ──────▶│                                  │
    │                               │                                  │
    │                               │── Parse & Validate ──────────────│
    │                               │── Dedup Check (30s cache) ───────│
    │                               │── Log Reception (DB) ────────────│
    │                               │                                  │
    │                               │── Query matching trades ─────────│
    │                               │   (ticker+TF+strat, status=OPEN) │
    │                               │                                  │
    │                               │── IF no match: skip (log INFO)───│
    │                               │                                  │
    │                               │── Notify MOVEBE signal (TG) ─────│
    │                               │                                  │
    │                               │── FOR EACH matching trade: ──────│
    │                               │   │                              │
    │                               │   │── get_open_positions() ─────▶│
    │                               │   │◀── positions[] ──────────────│
    │                               │   │                              │
    │                               │   │── Verify position exists ────│
    │                               │   │                              │
    │                               │   │── update_sl_tp_orders() ────▶│
    │                               │   │   (SL=entry_price, TP=keep)  │
    │                               │   │                              │
    │                               │   │── Log SL moved (DB) ─────────│
    │                               │   │── Notify executed (TG) ──────│
    │                               │                                  │
    │◀── Response ──────────────────│                                  │
```

---

## Implementation Checklist

### Phase 1: Backend Core
- [ ] Mettre à jour le commentaire du champ `type` dans `schemas.py`
- [ ] Ajouter le routage `MOVEBE` dans `receive_webhook()` de `webhook.py`
- [ ] Implémenter `handle_movebe()` dans `webhook.py`
- [ ] Ajouter le commentaire de documentation en haut de `webhook.py`

### Phase 2: Notifications
- [ ] Ajouter `notify_movebe_signal()` à `TelegramService`
- [ ] Ajouter `notify_movebe_executed()` à `TelegramService`

### Phase 3: Frontend
- [ ] Ajouter `MOVEBE` au dropdown de types dans `MockWebhookModal.tsx`
- [ ] Masquer SL/TP et ajuster le payload quand type `MOVEBE`
- [ ] Ajouter le style/couleur pour le type `MOVEBE`

### Phase 4: Tests
- [ ] Ajouter test de parsing `MOVEBE` dans `test_webhook.py`
- [ ] Test manuel via `MockWebhookModal` avec un trade ouvert

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Trade sans `entry_price` (pas encore filled) | SL non déplacé | Vérification que `entry_price` est non-null avant modification + log WARNING |
| `update_sl_tp_orders` modifie aussi le TP | TP changé involontairement | Passer le `trade.tp` existant pour maintenir le TP en place |
| Signal `MOVEBE` reçu après que la position soit fermée | Erreur API ou skip inutile | Vérification que la position existe toujours via `get_open_positions()` |
| SL déjà au break even ou au-delà | Modification inutile | `update_sl_tp_orders` a une tolérance (0.01) et ne modifie que si le delta est significatif |

---

## Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/schemas.py` | MODIFY | Mettre à jour le commentaire du type pour inclure MOVEBE |
| `backend/routers/webhook.py` | MODIFY | Ajouter routage + handler `handle_movebe()` |
| `backend/services/telegram_service.py` | MODIFY | Ajouter 2 méthodes de notification |
| `frontend/src/components/MockWebhookModal.tsx` | MODIFY | Ajouter MOVEBE au dropdown + ajuster visibilité SL/TP |
| `tests/unit/test_webhook.py` | MODIFY | Ajouter test de parsing MOVEBE |

---

## Verification Plan

### Automated Tests

```bash
cd /Users/awagon/Documents/dev/topstepbot
python -m pytest tests/unit/test_webhook.py -v
```

Le test `test_valid_movebe_alert` valide que le payload MOVEBE est correctement parsé par le schéma Pydantic.

### Manual Verification

1. Lancer le bot + frontend
2. Ouvrir le `MockWebhookModal` dans le dashboard
3. Sélectionner le type `MOVEBE` — vérifier que SL/TP sont masqués
4. Si une position est ouverte, envoyer le signal MOVEBE et vérifier :
   - Notification Telegram reçue (signal + exécution)
   - Log visible dans l'onglet Logs du dashboard
   - SL modifié sur la plateforme TopStep
