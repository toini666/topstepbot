# Product

<!-- impeccable:product-schema 1 -->

> All facts below are inferred from the repository and the redesign brief (user delegated the interview: "carte blanche, tu travailles en autonomie"). None are user-confirmed unless marked [pinned].

## Platform

web

## Users

Retail futures traders running automated TradingView strategies against TopStep funded accounts. Primary user is the operator-owner (and a handful of other self-hosting users), monitoring from a Mac at home with the bot running locally 24/7, plus remote control from a phone via Telegram. They are experienced traders, comfortable with terminals and dense data.

## Product Purpose

TopStepBot receives TradingView webhook alerts through an ngrok tunnel and executes/manages futures trades on TopStep accounts: order placement with broker-side SL/TP brackets, per-account risk settings, strategy management, copy-trading, reconciliation with the broker, logs, and a P&L calendar. The dashboard is the local mission-control: watch live positions and P&L, arm/disarm trading, flatten in an emergency, configure everything.

## Operating Context

- Runs locally (TopStep forbids VPS/remote servers). One long-lived browser tab, mostly dark-room/evening use, often glanced at rather than studied.
- Money is live: the most important reads are connection status, trading armed/disarmed, open positions, and daily P&L. The most important action is FLATTEN (panic).
- Backend FastAPI on :8080, frontend built bundle served by `vite preview` on :5173. No router — tab navigation.

## Capabilities and Constraints

- Stack: React 19 + TypeScript + Vite 7 + Tailwind CSS 4, lucide-react icons, sonner toasts, axios, clsx + tailwind-merge. No component library, no React Router. [pinned by existing codebase]
- Surfaces: Dashboard (Header/KPIs, Positions, Account details, Trades history, Orders, Logs), Strategies manager, P&L Calendar, Settings modal (4 tabs), Setup wizard, Mock-webhook tester, Reconciliation modal, Confirmation modal.
- Redesign constraint [pinned by user]: purely visual — zero functional/behavioral change; keep the existing color theme (dark slate ground, indigo primary, emerald/red P&L semantics, amber warnings).

## Brand Commitments

- Dark slate + indigo identity [pinned by user: "garde le thème de couleur"].
- Name/voice: "TopStep Bot", hobbyist-pro tone, footer signature "made with love by toini666".

## Evidence on Hand

- Live backend with real accounts/positions/trades available at localhost:8080 for verification. No marketing claims exist or should be invented; the app is a private tool.

## Product Principles

1. Glanceable truth first: connection, armed state, P&L and open risk legible from across the room.
2. Dangerous actions look dangerous; the panic path is never more than one glance and two clicks away.
3. Density with hierarchy: traders want data, not whitespace theater.
4. One coherent component language everywhere — dashboard, modals, wizard alike.
5. Motion communicates state (live/loading/changed), never decorates for its own sake.
