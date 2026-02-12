# Manuel d'Utilisation - TopStep Trading Bot

Bienvenue dans le manuel d'utilisation de votre application de trading automatisé. Ce document détaille les fonctionnalités disponibles sur l'interface utilisateur (Front-End) une fois connecté.

## Table des Matières

1. [Vue d'ensemble du Tableau de Bord](#1-vue-densemble-du-tableau-de-bord)
2. [Gestion des Positions et du Trading](#2-gestion-des-positions-et-du-trading)
3. [Configuration Globale](#3-configuration-globale)
4. [Gestion des Stratégies](#4-gestion-des-stratégies)
5. [Calendrier Économique](#5-calendrier-économique)
6. [Journaux et Monitoring](#6-journaux-et-monitoring)

---

## 1. Vue d'ensemble du Tableau de Bord

Une fois connecté, vous accédez à l'onglet principal **Trading**. L'interface est divisée en plusieurs sections clés :

### En-tête (Header)
- **Statut de Connexion** : Indique si le bot est connecté aux serveurs TopStep et au système de données.
- **Compte Sélectionné** : Menu déroulant pour changer de compte de trading actif.
- **Info Compte** : Affiche le solde actuel, le P&L (Profit & Loss) du jour, et l'état du marché (Ouvert/Fermé).
- **Bouton Déconnexion** : Pour se déconnecter de l'application.

### Barre de Navigation
Permet de basculer entre les différentes vues :
- **Trading** : Le tableau de bord principal.
- **Logs** : Les journaux d'activité du système.
- **Strategies** : Gestion des stratégies de trading.
- **Mock API** : Interface de test (pour le développement).
- **Calendar** : Calendrier économique.
- **Settings** : Configuration globale de l'application.

### Panneaux du Dashboard
1. **Details du Compte** :
    - Affiche les métriques détaillées : Solde, Équité, P&L Latent, Marge utilisée.
    - **Interrupteur "Trading Enabled"** : Permet d'activer ou désactiver globalement la prise de position pour ce compte.

2. **Positions En Cours** :
    - Liste les positions actuellement ouvertes.
    - Affiche le symbole, le côté (Long/Short), la taille, le prix d'entrée, le prix actuel et le P&L latent.
    - **Actions** : Bouton pour fermer une position manuellement.

3. **Historique des Trades** :
    - Liste des trades clôturés.
    - Option pour "Réconcilier" (Reconcile) en cas de différence entre le bot et TopStep.

4. **Ordres** :
    - Liste des ordres en attente ou exécutés (Limit, Stop, Market).

---

## 2. Gestion des Positions et du Trading

### Fermeture Manuelle
Dans le tableau des **Positions**, chaque ligne possède un bouton **"Close"**.
- Cliquer dessus ouvrira une fenêtre de confirmation.
- Confirmer pour envoyer un ordre de fermeture immédiat au marché pour cette position spécifique.

### Bouton Panique (Flatten All)
Un bouton d'urgence **"FLATTEN ALL"** est généralement disponible (souvent en rouge).
- **Action** : Ferme TOUTES les positions ouvertes et annule TOUS les ordres en attente pour le compte sélectionné.
- **Usage** : À utiliser en cas de problème technique majeur ou de perte de contrôle.

### Réconciliation
Si vous constatez un écart entre l'interface et votre compte TopStep réel (par exemple, un trade manquant) :
1. Allez dans la section **Trades History**.
2. Cliquez sur **"Reconcile"**.
3. Le système comparera l'état local avec l'état distant et proposera des corrections (ajout de trades manquants, ajustement du P&L).

---

## 3. Configuration Globale

Accessible via le bouton **Settings** (icône d'engrenage) dans la navigation.

### Onglet "General"
- **Timezone** : Définit le fuseau horaire de l'application (ex: Europe/Brussels). Toutes les heures affichées s'adapteront à ce réglage.
- **Market Hours** : Heures d'ouverture et de fermeture du marché.
- **Trading Days** : Sélectionnez les jours où le bot est autorisé à trader (Lundi à Dimanche).
- **Blocked Trading Hours** : Ajoutez des plages horaires spécifiques où le trading est interdit (ex: pause déjeuner, clôture).
- **News Trading Blocks** :
    - Activez le blocage automatique autour des annonces économiques.
    - Définissez combien de minutes **avant** et **après** l'annonce le trading est suspendu.
- **Position Action on Blocked Hours** :
    - Choisissez l'action à entreprendre si une position est ouverte au début d'une période bloquée :
        - *Do Nothing* : Ne rien faire.
        - *Move SL to Breakeven* : Déplacer le Stop Loss au prix d'entrée.
        - *Flatten* : Fermer toutes les positions.
- **Auto-Flatten** : Heure précise à laquelle toutes les positions sont forcées à la fermeture (ex: 21:55 avant la clôture du marché).
- **Risk Rules** :
    - *Single Position Per Asset* : Empêche d'empiler plusieurs positions sur le même actif.
    - *Block Cross-Account Opposite* : Empêche d'être Long sur un compte et Short sur un autre (couverture interdite).

### Onglet "Sessions"
- Configurez les sessions de trading (Asia, London, New York).
- Définissez leurs horaires de début et de fin.
- Activez ou désactivez les sessions. Ces sessions sont utilisées par les stratégies pour filtrer les entrées.

### Onglet "Mappings"
- Permet de lier les symboles TradingView aux contrats TopStep.
- **Exemple** : `MNQ1!` (TradingView) -> `MNQH6` (TopStep).
- **Micro Equivalent** : Permet de définir un multiplicateur (ex: 10 pour trader des Minis avec des signaux Micros, ou 1 pour 1:1).

### Onglet "Notifications"
- Configurez les alertes **Discord**.
- Activez les notifications pour : Ouverture/Fermeture de position, Fermeture partielle, Résumé journalier.
- Nécessite une URL de Webhook Discord.

### Onglet "Credentials"
- Gestion sécurisée des clés API TopStep et Tokens Telegram.
- Les valeurs sont masquées par défaut. Remplissez un champ uniquement pour le modifier.

---

## 4. Gestion des Stratégies

Accessible via l'onglet **Strategies**.

### Vue Globale (Templates)
Si aucun compte n'est sélectionné, vous gérez les "Templates" de stratégies.
- **Créer une stratégie** :
    - *Name* : Nom d'affichage.
    - *Webhook ID (tv_id)* : L'identifiant envoyé par TradingView dans le message d'alerte.
    - *Risk Factor* : Multiplicateur de risque par défaut.
    - *Allowed Sessions* : Sessions autorisées par défaut (ASIA, UK, US).
    - *Outside Sessions* : Autoriser ou non le trading hors des sessions définies.
    - *Partial TP %* : Pourcentage de la position à fermer au premier Take Profit.

### Vue Compte (Account Strategy Config)
Si un compte est sélectionné, vous voyez la configuration spécifique à ce compte.
- **Ajouter une stratégie** : Importez un template existant sur ce compte.
- **Configurer** :
    - Activez/Désactivez la stratégie pour ce compte spécifiquement.
    - Surchargez les paramètres par défaut (ex: risque plus faible sur un petit compte).
    - *Move SL to BE* : Activer le déplacement automatique du Stop Loss à l'entrée après le TP1.

---

## 5. Calendrier Économique

Accessible via l'onglet **Calendar**.

- **Vue Calendrier** : Affiche les événements économiques de la semaine ou du jour.
- **Filtres** : Filtrez par Impact (High, Medium, Low) et par Pays.
- **Settings (Roue dentée)** :
    - Définissez quels pays et quels impacts sont considérés comme "Majeurs".
    - Activez les alertes Discord pour les événements majeurs (ex: 5 minutes avant).
    - Activez le résumé quotidien des annonces.

---

## 6. Journaux et Monitoring

Accessible via l'onglet **Logs**.

- Affiche les journaux système en temps réel.
- Permet de voir les erreurs, les exécutions d'ordres, et les messages de débogage.
- Utilisez le bouton "Load More" pour voir l'historique plus ancien.
- Utile pour comprendre pourquoi un trade n'a pas été pris (ex: "Rejected due to blocked hours").
