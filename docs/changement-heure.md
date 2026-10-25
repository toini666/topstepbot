# Changement d'heure : les semaines où l'Europe et les USA sont décalés

## Le problème

Les heures du bot (ouverture/fermeture du marché, auto-flatten) sont exprimées dans le fuseau de
l'utilisateur (`USER_TIMEZONE`, ici `Europe/Brussels`). TopStep et le CME, eux, vivent à l'heure de
**Chicago**. Toute l'année, Bruxelles a 7 h d'avance sur Chicago et la config habituelle colle :

| Réglage | Heure de Bruxelles | Heure de Chicago |
|---|---|---|
| Ouverture du marché | 00:00 | 17:00 (réouverture Globex) |
| Fermeture du marché | 22:00 | 15:00 |
| Auto-flatten | 21:58 | 14:58 |
| Limite TopStep (être à plat) | 22:10 | 15:10 |

Mais l'Europe et les USA ne changent pas d'heure le même jour. Pendant 1 à 3 semaines par an, l'écart
tombe à **6 h** : tout ce qui est calé sur Chicago arrive **1 h plus tôt** à Bruxelles. Laissé à
21:58, l'auto-flatten tomberait à 15:58 CT, **après** la limite TopStep de 15:10 CT (les risk managers
commencent à fermer vers 15:08 CT) → risque de violation de règle.

## Les semaines concernées

La période va du dimanche du premier changement au dimanche du second. Appliquer la config le
dimanche du premier changement **avant 23:00** (réouverture Globex du soir), la remettre le lundi qui
suit le second changement.

| Période | 1er changement | 2nd changement | Appliquer | Remettre |
|---|---|---|---|---|
| Automne 2026 | EU dim. 25/10 | US dim. 01/11 | dim. 25/10/2026 | lun. 02/11/2026 |
| Printemps 2027 | US dim. 14/03 | EU dim. 28/03 | dim. 14/03/2027 | lun. 29/03/2027 |
| Automne 2027 | EU dim. 31/10 | US dim. 07/11 | dim. 31/10/2027 | lun. 08/11/2027 |
| Printemps 2028 | US dim. 12/03 | EU dim. 26/03 | dim. 12/03/2028 | lun. 27/03/2028 |
| Automne 2028 | EU dim. 29/10 | US dim. 05/11 | dim. 29/10/2028 | lun. 06/11/2028 |

Règle : USA = 2e dimanche de mars / 1er dimanche de novembre ; Europe = dernier dimanche de mars /
dernier dimanche d'octobre.

## Ce qu'il faut changer dans le bot

| Réglage | Habituel | Semaine décalée |
|---|---|---|
| Ouverture du marché | 00:00 | 00:00 |
| Fermeture du marché | 22:00 | **23:59** |
| Auto-flatten | 21:58 | **20:58** |
| Jours de trading | MON–FRI | MON–FRI **+ SUN** |

Pourquoi ces valeurs :

- **Fermeture 23:59 = marché « ouvert 24 h »**, pour prendre l'ouverture Globex qui tombe à 23:00.
  C'est TradingView qui décide des heures d'envoi des signaux.
- **Ne jamais mettre l'ouverture à 23:00.** `check_market_hours` (`backend/services/risk_engine.py`)
  ne gère pas une plage qui passe minuit : avec ouverture 23:00 et fermeture 21:00, le bot refuse
  tout, 24 h sur 24.
- **Ne pas écrire 24:00** : la valeur n'est pas parsable, le bot retombe sur une fermeture à 22:00.
  Seule la minute 23:59→00:00 reste donc fermée.
- **Dimanche** : la réouverture du dimanche soir tombe à 23:00 le dimanche au lieu de 00:00 le lundi.
  Seul `trading_days` filtre les webhooks (`webhook.py`) ; le réglage « Weekend markets open » ne pilote
  que le bandeau du dashboard, qui affichera « Market closed (Sunday) » sans bloquer les trades.
- **Hors session** : les sessions ASIA/UK/US s'arrêtent à 21:59, donc tout ce qui arrive entre 22:00 et
  minuit est « hors session ». Les stratégies actives du compte en trading doivent avoir
  **Allow outside sessions** activé, sinon les signaux de l'ouverture sont refusés.

Point de vigilance : avec une fermeture à 23:59, le bot ne filtre plus rien après le flatten. Un signal
reçu entre 20:58 et 21:10 ouvrirait une position qui passerait la limite TopStep. Les alertes
TradingView doivent donc arrêter d'envoyer avant ~20:55.

## Comment l'appliquer

Depuis le dashboard : **Settings → General** (Market Hours, Trading Days, Auto-Flatten).

Ou depuis un terminal **sur le Mac** (y compris une session Claude Code ouverte sur le Mac et
pilotée à distance). C'est pris en compte immédiatement, sans redémarrage. Les valeurs ne sont pas
validées par l'API : respecter le format exact `HH:MM`.

```bash
# Semaine décalée
curl -s -X POST localhost:8080/api/dashboard/config -H 'Content-Type: application/json' \
  -d '{"market_open_time":"00:00","market_close_time":"23:59","auto_flatten_time":"20:58","trading_days":["MON","TUE","WED","THU","FRI","SUN"]}'

# Retour à la normale
curl -s -X POST localhost:8080/api/dashboard/config -H 'Content-Type: application/json' \
  -d '{"market_close_time":"22:00","auto_flatten_time":"21:58","trading_days":["MON","TUE","WED","THU","FRI"]}'

# Vérifier
curl -s localhost:8080/api/dashboard/config
curl -s localhost:8080/api/dashboard/market-status   # is_trading_allowed doit être true
```

Vérifier le hors session des stratégies actives (lecture seule) :

```bash
sqlite3 "file:topstepbot.db?mode=ro" "select a.account_name, s.name, c.enabled, c.allow_outside_sessions
  from account_settings a join account_strategy_configs c on c.account_id = a.account_id
  join strategies s on s.id = c.strategy_id where a.trading_enabled = 1"
```

À distance, Telegram ne permet pas de modifier ces réglages (seulement `/on`, `/off`, `/flatten`…),
et le dashboard n'est pas joignable de l'extérieur (ngrok n'expose que le backend).

Oublier de remettre la config est sans danger : le bot fermerait simplement une heure trop tôt.

## TradingView

Les blackouts des indicateurs dépendent du fuseau utilisé dans les scripts Pine :

- **Heure de la bourse (Chicago) ou New York** : rien à changer, ils suivent déjà les USA.
- **Europe/Brussels ou Europe/Paris** : décaler d'1 h plus tôt les créneaux liés aux annonces US, puis
  les remettre en même temps que le bot.

Repères US à l'heure de Bruxelles :

| Événement | Habituel | Semaine décalée |
|---|---|---|
| Stats US 8h30 New York (CPI, NFP, PIB…) | 14:30 | 13:30 |
| Ouverture de Wall Street | 15:30 | 14:30 |
| Stats 10h00 New York | 16:00 | 15:00 |
| FOMC (taux / conférence) | 20:00 / 20:30 | 19:00 / 19:30 |
| Limite TopStep | 22:10 | 21:10 |
| Clôture CME | 23:00 | 22:00 |
| Réouverture Globex | 00:00 | 23:00 |

Les annonces européennes (8h, ouverture de Londres, BCE) ne bougent pas.

## Ce qui n'a pas besoin d'être touché

- **Calendrier économique et alertes news** : la conversion UTC → fuseau utilisateur se fait à chaque
  rechargement (tous les jours à 07:00), donc les heures sont justes.
- **Tâches planifiées** (calendrier 07:00, validation des contrats 23:00) : elles suivent le
  changement d'heure toutes seules.
- **Sessions ASIA/UK/US** : simples étiquettes si les stratégies autorisent toutes les sessions et le
  hors session. La session US démarre en réalité à 14:30 pendant ces semaines.
- **Plages bloquées du bot** : sans effet si désactivées. Si elles sont actives, décaler celles qui
  sont calées sur les USA (ex. 14:30 → 13:30).

Effet secondaire possible : les soirées comptant comme heures de trading, l'alerte Telegram
« No signal received » peut se déclencher en soirée sans vrai problème.

## Pour supprimer cette manip un jour

Deux évolutions de code la rendraient inutile :

1. Gérer les plages qui passent minuit dans `check_market_hours` (comme le fait déjà
   `check_blocked_periods`) : on pourrait mettre l'ouverture à 23:00 au lieu du contournement 23:59.
2. Exprimer la fermeture et l'auto-flatten en heure de Chicago : ils suivraient TopStep sans
   intervention.

## Historique

- **Mars 2026** : auto-flatten passé de 21:58 à 20:58 du 10 au 25 mars (visible dans l'historique des
  trades : fermetures à 19:58 UTC au lieu de 20:58 UTC), puis remis à 21:58 après le 29 mars.
- **25/10/2026** : config « semaine décalée » appliquée à distance depuis une session Claude Code sur
  le Mac (fermeture 23:59, auto-flatten 20:58, dimanche ajouté). Retour prévu le lundi 02/11/2026.
