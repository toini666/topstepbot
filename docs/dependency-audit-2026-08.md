# Audit des dépendances — 25/08/2026

Audit complet backend (pip) + frontend (npm) + scripts d'install. Tout ce qui est écrit ici a été
**vérifié empiriquement** (venv jetable + copie du frontend dans un scratchpad), jamais depuis un
`npm outdated` lu de travers.

## TL;DR

| | Verdict |
|---|---|
| Le manifeste `requirements.txt` est-il vulnérable ? | **Une seule vraie faille : `aiohttp==3.13.4`** |
| Le `package.json` frontend est-il vulnérable ? | **Non — 0 vulnérabilité sur une install fraîche** |
| Les 38 CVE Python + 10 vulns npm affichées par les outils ? | **~95 % = dérive du venv/`node_modules` de cette machine**, pas un défaut du dépôt |
| Le problème le plus grave trouvé | **`npm config set strict-ssl false` dans `install.sh`/`update.sh`** — désactive la vérification TLS npm de façon persistante sur la machine de chaque personne qui lance le script (ce Mac est encore propre, vérifié) |
| Le bug le plus concret | **`pytest-asyncio` absent de `requirements.txt`** → sur une install neuve, 49 tests sur 82 échouent |

**Étape 1 appliquée le 25/08** (correctifs à impact runtime nul — cf. §6). Le reste attend : une
panne de livraison TradingView→ngrok est ouverte depuis le 24/08 avec 3 pistes non tranchées,
bouger aiohttp/starlette/uvicorn aujourd'hui polluerait ce diagnostic.

---

## 0. Mode d'exploitation réel : `start_bot.sh` uniquement

**Fait confirmé par l'opérateur le 25/08 : `install.sh` et `update.sh` ne sont jamais lancés ici.**
Le démarrage quotidien, c'est `./start_bot.sh`, point.

Or `start_bot.sh` **ne fait aucune opération de dépendances** (vérifié : aucun `git pull`, aucun
`pip install`, aucun `npm install`, aucun `npm run build`). Il tue les processus, active le venv,
lance uvicorn + `npm run preview` + ngrok. C'est tout.

Trois conséquences qui pilotent tout le reste de ce document :

1. **C'est l'explication complète de la dérive du §1.** Les dépendances datent littéralement de la
   dernière exécution manuelle des scripts : `starlette` écrit le **10/02/2026**,
   `frontend/node_modules/` le **29/03/2026**. Rien ne les a touchées depuis, et rien ne les
   touchera jamais tout seul.
2. **Les correctifs de l'étape 1 sur `install.sh`/`update.sh` ne s'appliqueront jamais à cette
   machine par le flux normal.** Ils protègent les *autres* utilisateurs du bot (et cette machine
   le jour d'une réinstallation). Le bénéfice immédiat ici se limite à la suppression du `ngrok`
   npm racine, au manifeste `pytest-asyncio` et au lockfile réparé.
3. **Toute mise à jour ici est manuelle, et le restera.** Les commandes de l'étape 2 doivent être
   tapées à la main — ne pas écrire « lance `update.sh` », ça ne correspond à rien.
   Corollaire moins visible : `npm run preview` sert `frontend/dist/`, qui n'est régénéré que par
   un `npm run build` explicite. Toute modif de `frontend/src/` reste invisible tant que le build
   n'est pas relancé à la main. *(État au 25/08 : `dist/` et `src/` sont tous deux au 17/05 23:24
   — cohérents, rien à rattraper.)*

---

## 1. La découverte principale : dérive locale ≠ dette du dépôt

`pip-audit` remonte **38 CVE dans 11 paquets**, `npm audit` remonte **10 vulnérabilités dont 7
« high »**. La quasi-totalité disparaît sans toucher à une seule ligne de manifeste.

**Vérification faite** — résolution de `backend/requirements.txt` **inchangé** dans un venv neuf :

| Paquet | Installé sur ce Mac | Install neuve, mêmes pins | CVE |
|---|---|---|---|
| starlette | 0.52.1 | **1.6.0** | 7 CVE → toutes corrigées |
| click | 8.3.1 | **8.4.2** | 1 CVE → corrigée |
| idna | 3.11 | **3.19** | 1 CVE → corrigée |
| pygments | 2.19.2 | **2.21.0** | 1 CVE → corrigée |
| certifi | 2026.2.25 | **2026.7.22** | pas de CVE, mais **magasin de certificats racine vieux de 5 mois** sur la machine qui fait du TLS vers le broker |

Pourquoi ? `fastapi` déclare `starlette>=0.46.0` **sans borne haute**. `pip install -r
requirements.txt` (ce que fait `update.sh`) ne touche pas une dépendance transitive déjà
« satisfaite » : starlette est resté figé à 0.52.1 depuis mars pendant que les installs neuves
partaient sur 1.6.0.

Idem côté frontend — copie de `frontend/` dans un scratchpad, `npm install` sans lockfile
(exactement ce que fait `install.sh`) :

```
added 226 packages in 28s
found 0 vulnerabilities        ← contre 10 vulns (7 high) sur le node_modules actuel
npm run build → ✓ built in 2.16s (exit 0)
```

Les 4 « high » (vite, postcss, nanoid, js-yaml) sont couverts par les plages `^` déjà en place.
Le `package.json` n'a **rien** à corriger.

> **⚠️ Piège : `pip install -U -r requirements.txt` ne suffit PAS.**
> pip utilise `--upgrade-strategy=only-if-needed` par défaut : il ne remonte une dépendance
> transitive que si un paquet épinglé l'*exige*. Comme `fastapi==0.135.2` se contente de
> starlette 0.52.1, `-U` ne le touche pas. **Vérifié en dry-run sur le venv actuel :**
>
> ```
> pip install -U -r backend/requirements.txt --dry-run
>   → starlette, click, idna, certifi : ABSENTS de « Would install »   (no-op)
>
> pip install -U --upgrade-strategy=eager -r backend/requirements.txt --dry-run
>   → Would install: starlette-1.6.0 click-8.4.2 idna-3.19 certifi-2026.7.22 Pygments-2.21.0 ✅
> ```
>
> **Conséquence pratique :** le remède est `rm -rf node_modules && npm install` côté front, et côté
> back `pip install -U --upgrade-strategy=eager -r requirements.txt` **ou** `rm -rf venv &&
> ./install.sh` — **pas** de nouveaux pins, et surtout **pas** un `-U` nu.
>
> C'est aussi le correctif à porter dans `update.sh:14`, qui fait aujourd'hui un
> `pip install -r requirements.txt` sans `-U` du tout : c'est le mécanisme exact qui a laissé
> starlette figé cinq mois.

---

## 2. Les 3 vrais problèmes (hors CVE)

### 2.1 🔴 `npm config set strict-ssl false` — TLS désactivé globalement, pour tout le monde

`install.sh:49` et `update.sh:21`. `npm config set` écrit dans le fichier de config **utilisateur**,
pas dans le projet — vérifié : `npm config get userconfig` → `/Users/awagon/.npmrc`. La
vérification des certificats TLS est donc désactivée **pour tous les `npm install` de la machine,
définitivement**, chez chaque personne qui lance `install.sh`. C'est une porte ouverte à un paquet
substitué en MITM — sur une machine qui détient les credentials TopStep.

**Bonne nouvelle sur cette machine :** `npm config get strict-ssl` → `true`, et `~/.npmrc`
(21 octets, daté du 05/11/2025) ne contient qu'une ligne `prefix`. `install.sh`/`update.sh` n'ont
donc pas été lancés ici depuis. **Le risque est devant, pas derrière** — mais il concerne déjà les
autres utilisateurs du bot qui, eux, ont lancé le script.

Ajouté volontairement en `d3f70a2` (« disable strict SSL for npm operations »), donc il y a un vrai
problème derrière : proxy d'entreprise, antivirus qui intercepte le TLS, ou certificat racine
manquant. À traiter à la source :

```bash
# le vrai correctif — on garde la vérification TLS, on lui donne le bon certificat :
npm config set cafile /chemin/vers/le/certificat-racine.pem

# repli acceptable — désactive quand même le TLS, mais seulement pour cette commande,
# sans contaminer la config de la machine :
npm install --strict-ssl=false

# et chez quiconque a déjà lancé install.sh :
npm config get strict-ssl        # si "false" →
npm config delete strict-ssl     # restaure la vérification
```

### 2.2 🟠 Le lockfile frontend est mort-né

`install.sh:48` fait `rm -rf node_modules package-lock.json` avant `npm install`, alors que
`frontend/package-lock.json` est **versionné dans git** (dernière écriture : 29 mars). Résultat :
zéro build reproductible — deux utilisateurs installant à deux semaines d'écart n'ont pas les mêmes
versions, et le lockfile du dépôt ne décrit plus rien.

C'est aussi ce qui explique la colonne `Current ≠ Wanted` sur **23 paquets** de `npm outdated`.

Correctif : supprimer le `rm -rf` et utiliser `npm ci` (install déterministe depuis le lockfile),
en régénérant le lock une bonne fois. Si le `rm -rf` avait été mis pour contourner un cache npm
corrompu, `npm ci` le résout de toute façon (il repart d'un `node_modules` vide par construction).

### 2.3 🟠 `pytest-asyncio` absent de `requirements.txt` → suite de tests inutilisable à neuf

`pytest.ini` déclare `asyncio_mode = auto`, ce qui exige `pytest-asyncio` — absent du manifeste.
Il n'est présent sur cette machine que parce qu'il y a été installé à la main un jour.

**Vérification faite**, venv neuf depuis `requirements.txt` :

```
49 failed, 33 passed        ← « async def functions are not natively supported »
```
puis après `pip install pytest-asyncio` :
```
4 failed, 78 passed         ← identique au venv local
```

Note connexe : `signalrcore==0.9.71` est installé dans le venv local mais **importé nulle part**
(`market_hub_client.py` parle SignalR en natif via `websockets`). Vestige de la même dérive.

---

## 3. Triage des CVE par accessibilité réelle

Le compte de CVE ne veut rien dire ici ; ce qui compte c'est le code qui les atteint.

| CVE | Accessible ? | Détail |
|---|---|---|
| **aiohttp** — 14 CVE, dont bypass SNI TLS sur connexion réutilisée (`PYSEC-2026-237`) et lecture hors-bornes du parseur C (`PYSEC-2026-3545`) | 🟡 **Faible mais réel** | aiohttp n'est utilisé qu'à **un seul endroit** : `backend/jobs/health_checks.py` (heartbeat optionnel). `ClientSession` recréée à chaque appel → pas de réutilisation de connexion, donc le bypass SNI n'est pas atteignable. Le parseur C, lui, traite la réponse d'un endpoint externe. **Le broker passe par `httpx`, pas aiohttp** — pas d'exposition côté ordres. |
| **starlette** — 7 CVE (Host header / `request.url`, limites `form()`, `HTTPEndpoint`) | 🟢 **Non atteignable** | Aucun `request.url` dans `backend/routers/`, aucun `StaticFiles`, aucun `HTTPEndpoint`. Et corrigées d'office sur toute install neuve (§1). |
| **starlette `StaticFiles` UNC SSRF (Windows)** | 🟢 **N/A** | Pas de `StaticFiles` dans le code — y compris pour les utilisateurs Windows (`install.ps1`). |
| **urllib3, requests, pip, setuptools, pytest, msgpack, mako** | 🟢 **Outillage uniquement** | Aucun `import requests` ni `import urllib3` dans `backend/` (seul le stdlib `urllib` est utilisé). Tirés par `pip-audit`/`alembic`, pas par le runtime du bot. |
| **vite / postcss / nanoid / js-yaml (7 « high » npm)** | 🟢 **Build-time** | `start_bot.sh:70` sert le front avec `npm run preview` → `vite preview` (statique), jamais le dev-server visé par les CVE de lecture de fichier arbitraire. Et 0 vuln sur install fraîche (§1). |

**Un seul item mérite un changement de manifeste : `aiohttp==3.13.4` → `3.14.3`.**

---

## 4. Bonus : 4 vulnérabilités supprimables en effaçant un fichier

Le `package.json` **à la racine** ne contient qu'une dépendance : `ngrok@^5.0.0-beta.2`. Elle date
du commit initial (`3d321e6`) et n'est **référencée nulle part** :

- `start_bot.sh:86-97` cherche `ngrok` dans le PATH, sinon un binaire `./ngrok` local
- `start_bot.ps1:106-109` fait pareil (`ngrok` PATH, sinon `ngrok.exe`)
- aucun `npx ngrok` ni chemin `node_modules/ngrok` nulle part
- le binaire n'a même jamais été téléchargé (`node_modules/ngrok/bin/` vide)
- ngrok réellement utilisé ici = **CLI Homebrew v3.34.1** (`/opt/homebrew/bin/ngrok`)

Supprimer `package.json`, `package-lock.json` et `node_modules/` à la racine élimine les
**4 vulnérabilités racine** (extract-zip, uuid, yaml) et ~40 paquets morts. Zéro risque
fonctionnel, macOS comme Windows.

⚠️ Ne **jamais** lancer `npm audit fix --force` à la racine : il « corrigerait » en rétrogradant
ngrok en 4.3.3.

---

## 5. Mises à jour recommandées

### Backend — nouveau `requirements.txt` proposé

```diff
 fastapi==0.135.2          →  0.141.1
 uvicorn[standard]==0.42.0 →  inchangé (voir note)
 pydantic==2.12.5          →  2.13.4
 sqlalchemy==2.0.48        →  2.0.52
 httpx==0.28.1                inchangé (à jour)
-aiohttp==3.13.4           →  3.14.3      ← seule correction de sécurité réelle
 python-dotenv==1.2.2      →  1.2.3
 pytest==9.0.2             →  9.1.1
+pytest-asyncio==1.4.0                    ← manquant, casse la suite de tests (1.3.0 si pytest reste en 9.0.2)
 pytz==2026.1.post1        →  2026.3.post1
 alembic==1.18.4           →  1.19.1
 apscheduler==3.11.2       →  3.11.3
 xmltodict==1.0.4             inchangé (à jour)
 websockets==16.0          →  17.0.1      ← à valider en live (voir note)
+starlette>=1.6.0                         ← optionnel : fige explicitement ce qu'une install neuve prend déjà
```

**Vérifié** dans un venv jetable avec ce jeu complet : l'app importe, les 44 routes OpenAPI sont
présentes, et la suite de tests donne **exactement le même résultat que la baseline** (78 passés /
4 échoués).

Notes :

- **`fastapi` 0.141 change une structure interne** : `app.routes` n'expose plus les routes
  aplaties mais des objets `_IncludedRouter` (12 entrées au lieu de 60). Le schéma OpenAPI reste
  identique (44 chemins) et aucun code du dépôt n'itère sur `app.routes` — mais c'est le genre de
  détail qui casserait un futur endpoint de debug.
- **`uvicorn` 0.42 → 0.52 : laissé de côté.** Saut de 10 versions mineures sur le serveur qui reçoit
  les webhooks TradingView, en pleine investigation de panne de livraison. Aucune CVE ne le
  concerne. À faire plus tard, isolément.
- **`websockets` 16 → 17 : bump majeur, non validable hors-ligne.** `market_hub_client.py:78`
  appelle `websockets.connect(ping_interval, ping_timeout, close_timeout)` — la signature accepte
  toujours ces paramètres en 17.0.1 (vérifié), mais le handshake SignalR réel n'est testable qu'en
  connexion live. À faire séparément, avec un market hub ouvert sous les yeux.

### Frontend — aucun changement de `package.json`

Le manifeste est sain. Il suffit de réinstaller (§1). Les mises à jour dans les plages `^` déjà
déclarées suffisent, et le build passe.

### 🚫 À ne pas faire

Ruptures garanties, bénéfice nul pour un bot local qui fonctionne :

| Paquet | Actuel → Dernier | Pourquoi non |
|---|---|---|
| typescript | 5.9 → **7.0** | Réécriture du compilateur, refonte de la config |
| eslint | 9.39 → **10.0** | Config plate v10, plugins à re-valider |
| vite | 7.3 → **8.2** | Majeure ; `vite preview` marche très bien |
| @vitejs/plugin-react | 5 → **6** | Suit vite 8 |
| lucide-react | 0.563 → **1.34** | Renommages d'icônes → dashboard cassé |
| @types/node | 25 → **26** | Suit une majeure Node non installée (Node 22 ici) |
| starlette (fresh) | ≥1.6 | *Autorisé* : validé par les tests ci-dessus, et déjà pris par toute install neuve |

`eslint@9.39.5` affiche « no longer supported » à l'install. Non bloquant (outil de dev, jamais en
prod). À planifier tranquillement, hors fenêtre de trading.

---

## 6. Plan d'application séquencé

**Étape 0 — attendre.** Ne rien toucher au backend tant que l'incident TradingView→ngrok du 24/08
n'est pas tranché. Changer aiohttp/starlette/fastapi maintenant ajouterait une 4ᵉ variable à un
diagnostic à 3 inconnues.

**Étape 1 — ✅ APPLIQUÉE le 25/08** (impact runtime nul, bot resté en marche — `/health` → `ok`,
uvicorn/vite/ngrok intacts, `pytest` toujours à 78/4) :

1. ✅ **`package.json` + `package-lock.json` + `node_modules/` racine supprimés** → −4 vulns,
   −44 paquets morts. Vérifié avant : le lock ne contenait que l'arbre `ngrok`, et les 4 `npm
   install` du dépôt sont tous exécutés depuis `cd frontend` (les deux scripts `.sh` et les deux
   `.ps1`) — aucun ne touchait la racine.
2. ✅ **`pytest-asyncio==1.3.0` ajouté à `requirements.txt`.** 1.3.0 et non 1.4.0 : c'est la paire
   testée avec le `pytest==9.0.2` épinglé (78/4). Vérifié en dry-run : **le venv local ne bouge
   pas** (« already satisfied »), donc zéro risque sur le bot en cours. Le couple
   `pytest 9.1.1 + pytest-asyncio 1.4.0` viendra à l'étape 2, testé aussi.
3. ✅ **`npm config set strict-ssl false` supprimé** de `install.sh` et `update.sh`, remplacé par
   `npm install --strict-ssl=false` (portée = la commande). Un commentaire dans `install.sh`
   explique pourquoi et pointe vers le vrai correctif (`cafile`). Flag validé sur npm 10.9.8.
   → **Action manuelle restante pour les autres utilisateurs** : `npm config get strict-ssl`, et si
   `false`, `npm config delete strict-ssl`.
4. ✅ **Lockfile frontend réparé** (remonté de l'étape 3, parce que le §2.2 devenait faux sinon) :
   `install.sh` ne détruit plus `package-lock.json`, et le lock du dépôt a été régénéré depuis le
   `package.json` actuel. Validé en scratchpad : `npm ci` → 227 paquets, **0 vulnérabilité**,
   `npm run build` OK avec des hashes de sortie identiques (`index-22RLgDFi.js`) → build
   reproductible. Les installs futures repartent d'un arbre propre au lieu de re-résoudre au hasard.

   Dans la foulée, `npm cache clean --force` a été retiré d'`install.sh` : même famille de défaut
   que le §2.1 — il vidait le cache npm **global** de la machine et forçait le re-téléchargement
   des 227 paquets à chaque install. Remplacé par `npm cache verify` (répare sans détruire) ; le
   déterminisme vient désormais du lockfile.

   ⚠️ Deux réserves assumées :
   - le lock fige `eslint@9.39.5`, que npm signale déjà comme *no longer supported*. Sans gravité
     (outil de dev, jamais en prod) mais tout `npm ci` futur le réinstallera tel quel jusqu'à la
     migration eslint 10 de l'étape 4 ;
   - le `node_modules/` **local** n'a volontairement pas été réinstallé : `vite preview` tourne
     dessus en ce moment. C'est l'étape 2, bot arrêté.

**Non fait volontairement à l'étape 1 :** `update.sh:14` fait toujours un `pip install -r` nu —
le mécanisme qui fige les transitives (§1). Y mettre `--upgrade-strategy=eager` donnerait à
l'updater le droit de remonter n'importe quelle transitive sans prévenir, sur un bot qui passe des
ordres : ça se fait bot arrêté, avec les tests derrière, donc à l'étape 2. Sachant que ce script
n'est de toute façon jamais lancé sur cette machine (§0), l'enjeu est pour les autres utilisateurs.
**Côté Python, la dérive locale n'est pas refermée : elle ne le sera que par les commandes
manuelles de l'étape 2.**

**Étape 2 — après l'incident, bot arrêté, un seul lot.** Commandes à taper à la main : sur cette
machine rien ne se met à jour tout seul (§0).

4. `pip install -U --upgrade-strategy=eager -r requirements.txt` avec le nouveau manifeste (§5)
   — **surtout pas un `-U` nu**, cf. l'encadré du §1 — puis `pytest` → attendre 78/4
5. Front : `cd frontend && rm -rf node_modules && npm install && npm run build` → 0 vuln
   (le lockfile réparé à l'étape 1 rend cette install déterministe)
6. Redémarrer, surveiller un cycle de signal TradingView complet

**Étape 3 — isolément, chacun son tour, jamais en séance :**

7. `uvicorn` 0.42 → 0.52 (surveiller la réception webhook)
8. `websockets` 16 → 17 (surveiller le market hub SignalR)
9. ~~Corriger `install.sh` pour ne plus détruire le lockfile~~ → fait à l'étape 1

**Étape 4 — dette froide, hors trading :** eslint 10, vite 8, typescript 7, lucide-react 1.x.

---

## 7. Baseline de référence (avant toute modification)

```
Python 3.12.12 · Node v22.22.3 · npm 10.9.8 · ngrok CLI 3.34.1 (Homebrew)
pytest : 4 échecs / 78 passés — préexistants, sans lien avec les dépendances :
  - test_position_monitor.py::test_detects_full_position_closure
  - test_position_monitor.py::test_detects_new_position
  - test_risk_engine.py::TestMarketHoursCheck::test_market_closed_before_open  (OPEN vs CLOSED)
  - test_topstep_client.py::test_circuit_breaker_blocks_subsequent_requests
```

Ces 4 échecs sont de la dérive de tests (attentes obsolètes), pas des régressions de dépendances :
identiques dans le venv local, dans un venv neuf, et avec le jeu de versions mis à jour. Ils sont
le seuil de comparaison pour valider n'importe quelle mise à jour — mais ils méritent d'être
corrigés à part, sinon ils masqueront la prochaine vraie régression.
