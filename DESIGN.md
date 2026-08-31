---
name: TopStepBot
description: A prop-firm risk-desk console for local automated futures trading — glanceable truth, guarded danger, motion as state.
colors:
  command-indigo-bright: "#818cf8"
  command-indigo: "#6366f1"
  command-indigo-deep: "#4f46e5"
  pnl-up-emerald: "#34d399"
  armed-emerald: "rgba(16, 185, 129, 0.9)"
  pnl-down-red: "#f87171"
  danger-red: "#ef4444"
  danger-red-deep: "#dc2626"
  caution-amber: "#fbbf24"
  session-sky: "#38bdf8"
  strategy-violet: "#a78bfa"
  ground-slate-950: "#020617"
  panel-slate-900: "#0f172a"
  surface-hairline: "rgba(148, 163, 184, 0.1)"
  surface-hairline-strong: "rgba(148, 163, 184, 0.18)"
  surface-panel-top: "rgba(30, 41, 59, 0.5)"
  surface-panel-bottom: "rgba(15, 23, 42, 0.38)"
  surface-well: "rgba(2, 6, 23, 0.6)"
  ink-white: "#ffffff"
  ink-muted-slate-400: "#94a3b8"
typography:
  display:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 700
    lineHeight: "1.2"
    letterSpacing: "-0.025em"
  title:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: "1.556"
    letterSpacing: "-0.025em"
  body:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: "1.625"
    letterSpacing: "normal"
  label:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: "1rem"
    letterSpacing: "0.05em"
  mono:
    fontFamily: "ui-monospace, \"SF Mono\", \"Cascadia Mono\", \"Roboto Mono\", Menlo, Consolas, monospace"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: "1.25rem"
    letterSpacing: "normal"
rounded:
  md: "6px"
  lg: "8px"
  xl: "12px"
  2xl: "16px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  ms: "12px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.command-indigo}"
    textColor: "{colors.ink-white}"
    rounded: "{rounded.xl}"
    padding: "8px 24px"
  button-kill:
    backgroundColor: "rgba(239, 68, 68, 0.08)"
    textColor: "#fca5a5"
    rounded: "{rounded.xl}"
    padding: "8px 16px"
  button-kill-hover:
    backgroundColor: "{colors.danger-red}"
    textColor: "{colors.ink-white}"
    rounded: "{rounded.xl}"
    padding: "8px 16px"
  badge-success:
    backgroundColor: "rgba(16, 185, 129, 0.1)"
    textColor: "#6ee7b7"
    rounded: "{rounded.md}"
    padding: "2px 8px"
  card:
    backgroundColor: "{colors.surface-panel-top}"
    rounded: "{rounded.2xl}"
    padding: "24px"
  input:
    backgroundColor: "{colors.surface-well}"
    textColor: "{colors.ink-white}"
    rounded: "{rounded.lg}"
    padding: "8px 12px"
  status-lamp:
    backgroundColor: "rgba(30, 41, 59, 0.55)"
    textColor: "{colors.ink-muted-slate-400}"
    rounded: "{rounded.full}"
    padding: "4px 12px"
  toggle-armed:
    backgroundColor: "{colors.armed-emerald}"
    rounded: "{rounded.full}"
    height: "24px"
    width: "44px"
  stat-readout:
    backgroundColor: "rgba(15, 23, 42, 0.6)"
    rounded: "{rounded.xl}"
    padding: "12px 16px"
---

# Design System: TopStepBot

## Overview

**Creative North Star: "The Risk Desk"**

TopStepBot is not a fintech dashboard — it's a prop-firm risk-desk console, glanced at from across a dark room rather than studied up close. Every surface sits on one continuous slate-950 ground, etched with a 32px grid and lit by an indigo aura bleeding from the top edge; console panels float on that ground as translucent, hairline-bordered layers, never as opaque blocks. Numbers are the product — P&L, size, entry, balance — so they are set in tabular mono and read with their own semantic weight (green up, red down) instead of being flattened into uniform stat cards. Indigo is the one color that means "you can act here"; it never leaks into a status reading. Motion exists to report state — a lamp breathes because a connection is live, a cell flashes because a number just moved, a list rises in a capped stagger because it just populated — never to decorate.

This is a deliberate rejection of the generic glassy fintech-dashboard arrangement of same-size, same-weight stat tiles. Danger looks dangerous (the flatten switch is outlined and inert until you reach for it, then floods red); configuration and setup feel calm (soft indigo brand moments, unhurried step progress). The system is dense — traders want data, not whitespace theater — but every panel keeps a consistent physical grammar: a 1px hairline border, a top-edge light catch, and a soft ambient shadow, like sheet-metal console modules bolted to the same rack.

**Key Characteristics:**
- One continuous ground (slate-950 + etched grid + indigo aura) that every panel floats above, never covers
- Indigo is the only interactive/command color; status is read through emerald/red/amber/sky/violet, which never respond to hover
- Numerics are always tabular mono, most are right-aligned, P&L numbers carry a matching text-shadow glow
- A five-step radius ladder (6/8/12/16/full) and a six-step spacing scale (4/8/12/16/24/32) tied to the 32px etched grid unit
- Motion is a state vocabulary (breathing lamps, flash-up/down, capped stagger), not embellishment
- Danger is guarded: the kill switch is nearly invisible until you approach it, then commits fully on hover

## Colors

Every hue in the system carries meaning, not decoration: one command color, a pair of P&L/danger semantics, three lower-priority status accents, and a neutral scale built mostly from translucent layering tokens rather than opaque fills.

### Primary
- **Command Indigo** (`#6366f1`, indigo-500): the base fill for every interactive surface — `.btn-primary`, active tab, active filter segment, dropdown-item hover tint, indigo toggle track. Always the top stop of a two-step vertical gradient down to Command Indigo Deep.
- **Command Indigo Bright** (`#818cf8`, indigo-400): icon tint inside `CardHeader`/`Stat`/`StatusLamp`, the global `:focus-visible` outline color, and the glow ring around the app logo. This is indigo's "at rest, drawing attention" shade.
- **Command Indigo Deep** (`#4f46e5`, indigo-600): the bottom gradient stop for `.btn-primary`/`.tab-btn-active`/`.filter-btn-active`, giving every indigo command surface a subtle top-lit bevel.

### Secondary
- **P&L Up Emerald** (`#34d399`, emerald-400): the "live/positive" lamp and icon tone — connection-online lamp, armed-trading badge accent, P&L-up icon. Readout *text* uses the lighter emerald-300 (`#6ee7b7`) with a matching glow, distinct from the lamp/icon shade.
- **Armed Emerald** (`rgba(16, 185, 129, 0.9)`, emerald-500 @ 90%): the fill of an "on" toggle track (bot trading armed) — the single most consequential switch in the app.
- **P&L Down Red** (`#f87171`, red-400): the "danger/negative" lamp and icon tone. Readout text uses the lighter red-300 (`#fca5a5`) with a matching glow.
- **Danger Red** (`#ef4444`, red-500) → **Danger Red Deep** (`#dc2626`, red-600): the gradient used by `.btn-danger` at rest and by `.btn-kill` only once it's hovered/committed. This pair never appears as a *resting* fill on the kill switch — see the Guarded Kill Rule in Components.

### Tertiary
- **Caution Amber** (`#fbbf24`, amber-400): market-session lamp, warning badges, force-reconnect action, blocked-period/news-block accents. Never used for a clickable command.
- **Session Sky** (`#38bdf8`, sky-400): market-open lamp/value only — the one color reserved exclusively for market-hours state.
- **Strategy Violet** (`#a78bfa`, violet-400): the tag color for strategy/timeframe labels in tables, and the timezone step icon in setup — a quiet fourth accent for "classification," never for state or action.

### Neutral
- **Ground Slate** (`#020617`, slate-950): the base color of `<body>`, under the etched grid and aura. Nothing else should paint this color as a flat fill — see the Ground Ownership Rule.
- **Panel Slate** (`#0f172a`, slate-900): the solid backing for compact modules that don't use the panel gradient — `Stat`, `status-pill`, the tab-rail well, icon chips.
- **Surface Hairline** (`rgba(148, 163, 184, 0.1)`) and **Surface Hairline Strong** (`rgba(148, 163, 184, 0.18)`): the 1px border on every panel, input, and divider; the "strong" variant is the hover/emphasis state of the same border.
- **Surface Panel Top** (`rgba(30, 41, 59, 0.5)`) → **Surface Panel Bottom** (`rgba(15, 23, 42, 0.38)`): the vertical gradient every `.card` is built from — translucent, so the ground's grid and aura show faintly through.
- **Surface Well** (`rgba(2, 6, 23, 0.6)`): the recessed fill for data wells — log stream, inputs, code blocks — anything meant to read as "sunken into the console" rather than "floating on it."
- **Ink White** (`#ffffff`): headline text and hero values (account balance, page H1).
- **Ink Muted** (`#94a3b8`, slate-400): secondary text, captions, status-pill values, placeholders.

### Named Rules
**The Ground Ownership Rule.** `<body>` alone paints the slate-950 ground, the 32px etched grid, and the indigo aura (`background-image` layers in `index.css`). No container between body and a panel should ever apply an opaque `bg-slate-*` fill — doing so blocks the ground from showing through and defeats the entire "console modules floating on a lit rack" premise. Panels stay translucent (Surface Panel Top/Bottom, Surface Well) so the ground is always faintly present underneath.

**The One Command Color Rule.** Indigo is used exclusively for things the user can act on: buttons, active tab/filter state, focus rings, input focus, dropdown hover, the indigo toggle variant. Emerald/red/amber/sky/violet exist to be *read*, not clicked — none of them carry a hover or active interaction state anywhere in the system.

## Typography

**Display/Body Font:** the system sans stack (`ui-sans-serif, system-ui, sans-serif`, plus emoji fallbacks) — no custom webfont is loaded; Tailwind's default stack is used everywhere prose or headings appear.
**Mono/Label-numeric Font:** `ui-monospace, "SF Mono", "Cascadia Mono", "Roboto Mono", Menlo, Consolas, monospace` (the `--font-mono` theme token) — reserved for anything that is data rather than prose: numerics, account IDs, log timestamps, code/JSON.

**Character:** a plain, high-legibility sans for everything a human reads as language, handed off hard to mono the instant a value becomes a number worth comparing at a glance. The pairing has no personality flourishes — it's built to disappear so the color and motion system can carry the weight.

### Hierarchy
- **Display** (700, 1.875rem/30px desktop → 1.5rem/24px mobile, tight tracking `-0.025em`): the app H1 ("TopStep Bot Toini666" in the header, "TopStepBot" in the setup wizard brand moment). Used exactly twice in the whole app — it is not a section-heading weight.
- **Title** (700, 1.125rem/18px, tight tracking `-0.025em`): `.section-title` — every `CardHeader` title and wizard step heading. This is the workhorse heading; there is no separate "headline" tier between Display and Title in this system.
- **Body** (400, 0.875rem/14px, relaxed leading 1.625): paragraph copy in modals, wizard explainer text, empty-state hints.
- **Label** (600, uppercase, two sizes): form labels (`.label`, 0.75rem/12px, tracking `0.05em`, slate-400) and console module captions (`.micro-label`, 0.65rem/10.4px, tracking `0.14em`, slate-500) — the second is tighter and quieter, used for the small all-caps tag above a `Stat` value or a table's own column headers.
- **Mono** (400 base / 700 for P&L readouts, size is contextual — 0.75rem in table cells up to 1.5rem for the account balance): every numeral in the app renders through this role. `* { font-variant-numeric: tabular-nums }` is global, so digits never shift width even outside an explicit mono class.

### Named Rules
**The Numerics-Are-Mono Rule.** Any value a trader compares at a glance — price, size, P&L, balance, contract count, timestamp — is set in the mono role via `.num` (mono + right-aligned + `whitespace-nowrap`) or `.readout-up/-down/-flat` (mono + bold + directional color + glow). Prose never borrows the mono font, and numerics never sit in the sans font.

## Layout

The page is a single `max-w-7xl`, centered column: header → orphaned-orders warning → tab rail → tab content → footer, with `space-y-8` (32px) rhythm between major blocks and outer page padding of `p-4` (16px) mobile / `md:p-8` (32px) desktop. The Trading tab's top row is a 3-column grid (`lg:grid-cols-3`) — Positions takes 2 columns, Account Details takes 1 — with a `gap-8` (32px) gutter.

Density inside panels is tight and consistent: table cells use `py-3 px-4` (12px/16px), `Stat`/`status-pill` modules use `px-4 py-3`/`px-3 py-1`, and card internal padding is a flat `p-6` (24px) regardless of panel size. There is no separate "compact" density mode — the whole app reads at one density.

Responsive behavior is breakpoint-driven at Tailwind's standard `sm/md/lg` steps: the tab rail wraps and hides label text behind `hidden sm:inline` before it ever shrinks touch targets; the header stacks to a column below `lg`; tables scroll horizontally (`overflow-x-auto`) rather than reflow. Coarse-pointer devices get larger targets (see Do's and Don'ts) instead of a different layout.

### Named Rules
**The 32px Grid Rule.** The ground's etched grid tile is 32px. Outer page padding on desktop (`md:p-8`), the vertical rhythm between major sections (`space-y-8`), and the gutter of the main content grid (`gap-8`) all resolve to that same 32px unit — panels visually snap to the grid that's lit into the floor beneath them.

## Elevation & Depth

Depth is conveyed by translucent layering and glow, not a conventional shadow scale. Panels are built from a vertical gradient of two low-alpha slate stops (Surface Panel Top → Surface Panel Bottom) over the lit ground, edged with a 1px hairline border and a 1px inset top highlight (`inset 0 1px 0 rgba(255,255,255,0.045–0.18)`) that reads as a light catch along a beveled physical edge. An ambient, near-black, heavily-offset shadow (`0 16px 40px -24px rgba(0,0,0,0.7)`) sits underneath for separation from the ground; it deepens slightly on `.card-hover`. Recessed elements (`.well`) invert this: an inset shadow (`inset 0 2px 8px rgba(0,0,0,0.35)`) makes log streams and code blocks read as sunken into the console rather than floating on it.

Interactive elements get colored glow instead of neutral drop-shadow: `.btn-primary` casts an indigo shadow (`0 8px 20px -8px rgba(79,70,229,0.55)`), `.btn-danger`/`.btn-kill:hover` cast red, the armed toggle casts emerald, the logo ring casts indigo. A button's shadow color always matches its semantic hue — there is no generic gray/black button shadow anywhere in the system. Overlays (modal, dropdown) get the heaviest ambient shadows in the system (`0 32px 64px -16px rgba(0,0,0,0.7)` and `0 20px 40px -12px rgba(0,0,0,0.7)` respectively) to read clearly above everything else.

### Shadow Vocabulary
- **Panel ambient** (`0 16px 40px -24px rgba(0,0,0,0.7)`): resting `.card`.
- **Panel ambient, hover** (`0 20px 48px -24px rgba(0,0,0,0.8)`): `.card-hover` on interaction.
- **Overlay ambient** (`0 32px 64px -16px rgba(0,0,0,0.7)`): `.modal-container`.
- **Menu ambient** (`0 20px 40px -12px rgba(0,0,0,0.7)`): `.dropdown-menu`.
- **Recessed well** (`inset 0 2px 8px rgba(0,0,0,0.35)`): `.well` (log stream, JSON, code).
- **Command glow** (semantic-colored, e.g. `0 8px 20px -8px rgba(79,70,229,0.55)` indigo, `rgba(220,38,38,0.55)` red): buttons, armed toggle, logo ring — always tinted to the element's own hue.
- **Top-edge highlight** (`inset 0 1px 0 rgba(255,255,255,0.045–0.18)`): every panel, button, and overlay — the shared "beveled console metal" cue.

### Named Rules
**The Glow-as-Elevation Rule.** Command surfaces don't get taller drop-shadows to signal importance — they get a colored glow matched to their semantic hue. Depth communicates hierarchy (panel vs. overlay); glow communicates meaning (this is indigo/red/emerald and it's interactive or armed).

## Shapes

Five radius steps cover the entire system, and every one of them is used consistently by role, not by component size:
- **6px** (`rounded-md`): the smallest, densest chips — badges, in-modal filter/segment buttons.
- **8px** (`rounded-lg`): inputs, `.btn-sm`, the segmented-control's own container.
- **12px** (`rounded-xl`): the default interactive-surface radius — all full-size buttons, the tab rail buttons, `.well`, `.dropdown-menu`, the `Stat` module.
- **16px** (`rounded-2xl`): containers — `.card`, `.modal-container`, the tab-rail nav wrapper, the `EmptyState` icon well.
- **Full** (`rounded-full`): anything meant to read as a physical dial or switch — lamps, toggle tracks/dots, `status-pill`.

Borders are hairline throughout (1px, `rgba(148,163,184,0.1–0.18)`) — there is no solid, opaque, high-contrast border anywhere in the resting state; emphasis is expressed by moving to the "strong" hairline variant or by adding a colored ring (`ring-1 ring-inset ring-{color}-400/20`) on badges. A recurring "icon chip" motif — a small rounded-xl/2xl square with a 15–25%-opacity tinted background hosting a single Lucide icon — marks module identity throughout (wizard step icons, `EmptyState` icon well, account-selector power glyph).

## Components

### Buttons
- **Shape:** 12px radius (`rounded-xl`) for all full-size variants; `.btn-sm` drops to 8px.
- **Primary:** `.btn-primary` — vertical gradient Command Indigo → Command Indigo Deep, white text, inset top highlight, indigo command glow. The only button that should read as "the main action" on a screen.
- **Danger:** `.btn-danger` — Danger Red → Danger Red Deep gradient, used inside modals already gated by a confirmation step (e.g. "Close Position").
- **Kill:** `.btn-kill` — see the Guarded Kill Rule below. Reserved for panic-class actions (Flatten & Cancel All).
- **Ghost / Outline:** `.btn-ghost` (transparent, slate text, fills slate-800/80 on hover) and `.btn-outline` (translucent slate-800 fill, hairline border) — secondary/tertiary actions with no semantic charge.
- **Hover/Focus:** primary/danger/outline lift 1px and brighten (`filter: brightness(1.08)`) on hover, settle on active (`brightness(0.97)`, no lift); all variants pick up the global `:focus-visible` indigo outline. Hover lift is suppressed under `(hover: none)` for primary/danger.

#### Named Rules
**The Guarded Kill Rule.** `.btn-kill` starts nearly invisible — an 8%-alpha red tint on transparent, outlined, red-300 text — and only becomes a solid red block with white text and full command glow on hover. Danger reveals itself as the operator's pointer approaches it; it never announces itself passively the way `.btn-danger` (already-solid) does. Don't use `.btn-danger` and `.btn-kill` interchangeably: danger is a committed action already behind a confirmation modal; kill is the guarded trigger that *opens* one.

### Badges
- **Style:** 6px radius pill, 10%-alpha tinted background, matching-hue text, `ring-1 ring-inset` at 20% alpha. Six variants: success/danger/warning/info/neutral/violet.
- **State:** static — badges are status readouts, not controls; an optional leading dot (`dot` prop) reinforces the reading without adding interactivity.

### Cards / Containers
- **Corner Style:** 16px (`rounded-2xl`).
- **Background:** Surface Panel Top → Surface Panel Bottom vertical gradient (translucent — see Ground Ownership Rule).
- **Shadow Strategy:** Panel ambient at rest, Panel ambient (hover) when `hover` is set — see Elevation & Depth.
- **Border:** 1px hairline, strengthening on hover when `hover` is set.
- **Internal Padding:** 24px, flat regardless of card size. `CardHeader` (icon + title + optional annotation, actions right-aligned) is the standard header row for every panel.

### Inputs / Fields
- **Style:** Surface Well background, hairline border, 8px radius. `.input` for prose values, `.input-mono` for anything numeric/technical (API keys, webhook URLs, tokens).
- **Focus:** border shifts to indigo-400/60 and a soft 3px indigo glow ring (`box-shadow: 0 0 0 3px rgba(99,102,241,0.18)`) appears — the input-level echo of the One Command Color Rule.
- **Labels:** `.label` (uppercase, 12px) sits above every field; `.help-text` (12px, muted, relaxed leading) follows for context.

### Toggle
- **Style:** pill track (`rounded-full`), 24px (md) or 20px (sm) tall, white circular dot that translates on state change.
- **State:** off = slate-700/80 track; on = either Armed Emerald (`activeColor="emerald"`, the default — used for the trading-armed switch, the highest-stakes control in the app) or Command Indigo (`activeColor="indigo"`, used for non-risk toggles like calendar notification settings), each with a matching glow.

### Status Lamp
- **Style:** a `status-pill` (rounded-full, translucent slate-800 background, hairline border) containing a small (8px) solid-color dot, an uppercase micro-label caption, and a bold mono value.
- **State:** `live` adds a 2.4s breathing pulse (`lampPulse` — the ring expands and fades, not the dot itself) to signal "this is happening right now" — connection online, market open. Non-live lamps (session tag, disconnected) hold steady. Five colors: emerald/red/amber/sky/slate, each with its own `--lamp-glow` value.

### Stat (readout module)
- **Style:** a small slate-900/60 tile — micro-label caption, an icon, a large tabular-mono value, optional sub-line.
- **Tone:** `up`/`down` apply the P&L readout color + glow; `flat` is plain slate; `neutral` (default) tints its icon indigo. This is the app's canonical "one number with context" unit — used for daily P&L and active-trade count in the header, and reused anywhere a single KPI needs to sit inside a denser layout.

### Tables
- **Header:** uppercase, 12px, slate-400, single hairline bottom border (`.table-header`).
- **Rows:** `.table-row` — near-invisible bottom hairline (5% alpha), subtle slate highlight on hover, last row has no border. Rows populate with `.animate-stagger` when a list first renders.
- **Numeric columns:** always `.num` (mono, right-aligned, no wrap); P&L cells swap to `.readout-up/-down` per row.

### Navigation
Two distinct navigation vocabularies, used for two distinct purposes — do not cross them:
- **Console tab rail** (`.tab-btn-active` / `.tab-btn-inactive`): top-level surface switching (Trading/Logs/Strategies/Calendar). Active state is an indigo gradient fill with border and command glow; inactive is transparent with a slate hover fill. 12px radius, min-height 44px on coarse pointers.
- **Segmented control** (`.filter-btn-active` / `.filter-btn-inactive`, wrapped in `.filter-group`): in-panel filtering and in-modal tab switching (period filters, impact filters, the Settings modal's General/Sessions/Mappings/Notifications/Credentials tabs). Smaller, 6px radius on the buttons inside an 8px-radius well, active state is the same indigo gradient at a smaller scale.

### Modal / Dropdown (signature overlay pattern)
- **Backdrop:** `rgba(2,6,23,0.7)` with 8px blur, fades in.
- **Container:** `#131c31 → #0c1424` gradient (opaque, unlike cards — overlays intentionally block the ground since they're meant to demand full attention), 16px radius, hairline border, overlay-ambient shadow, scales in from 96%.
- **Dropdown:** same family at 12px radius with a lighter, flatter fill (`#141d33`), slides down 6px while fading in.

## Do's and Don'ts

### Do:
- **Do** let `<body>` own the ground (slate-950 + etched 32px grid + indigo aura). Panels stay translucent (Surface Panel Top/Bottom, Surface Well) so it's always faintly visible underneath.
- **Do** use indigo exclusively for things the user can act on — buttons, active tab/filter state, focus rings, input focus, dropdown hover. Never give a semantic status color (emerald/red/amber/sky/violet) a hover or active interaction state.
- **Do** render every glanceable number through the mono role, right-aligned via `.num` where it's tabular, with directional color + glow via `.readout-up/-down/-flat` where it's P&L.
- **Do** reserve `.btn-kill` for panic-class actions only (flatten, cancel-all) — everything else destructive-but-routine uses `.btn-danger` behind a confirmation modal.
- **Do** snap major spacing to the 32px grid unit (desktop page padding, section rhythm, grid gutters) so panels align with the ground's etched grid.
- **Do** animate to report state, not to decorate: lamp pulse = live, flash-up/down = a value just changed, capped stagger = a list just populated. Cap list-entrance stagger at 280ms total (28ms/row via `min(i*28ms, 280ms)`) so long tables never feel slow.
- **Do** give coarse-pointer users 44px-minimum targets on every full-size button variant and tab button; keep dropdown items at their expanded `py-3` under `pointer: coarse`.
- **Do** render `EmptyState` as the sibling that replaces a panel's data region (table, list, or content column), sized with `flex-1` to fill the remaining panel height — this is the pattern `PositionsTable` and `AccountDetails` follow.

### Don't:
- **Don't** paint an opaque `bg-slate-*` fill on a full-viewport or full-panel container. It blocks the ground's grid and aura from showing through and breaks the "console modules on a lit rack" premise — panels are gradients and translucent wells, never flat opaque color.
- **Don't** nest `EmptyState` inside a scrolling data well or a table body (`<td>` inside `overflow-x-auto`, or a message list inside `overflow-y-auto`). It gets clipped or partially hidden by the scroll region instead of quietly replacing it.
- **Don't** introduce a radius value outside the five-step ladder (6px / 8px / 12px / 16px / full).
- **Don't** skip the hairline border + top-edge inset highlight on a new panel-level surface — that pairing is what reads as "console panel" instead of a flat rectangle.
- **Don't** give a button a neutral black/gray shadow. Command surfaces glow in their own semantic hue (indigo for primary/command, red for danger/kill-hover, emerald for armed) — see the Glow-as-Elevation Rule.
- **Don't** assume `prefers-reduced-motion` silences everything: it disables exactly twelve named keyframe animations (the entrance fades/scale/rise, row stagger, flash-up/down, skeleton shimmer, lamp pulse, and the modal/dropdown entrances). It does not touch `transition:`-based hover/focus effects (button lift, border-color fades, toggle-dot travel), and it deliberately does not silence `animate-spin` (the `Spinner` component, `Button`'s `loading` state) — a running spinner should never stop conveying "in progress," reduced motion or not.
