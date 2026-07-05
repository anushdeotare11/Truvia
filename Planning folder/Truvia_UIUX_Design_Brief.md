# Truvia
## UI/UX Design Brief
### v1.0 — Figma-Ready Specification

**Prepared by:** Principal Product Design
**Companion to:** Truvia PRD v1.0, TRD v1.0, App Flow v1.0
**Audience:** Visual/product designers building the Figma file, frontend engineers implementing the design system
**Scope note:** This document describes *look, feel, and behavior only*. Feature logic, API contracts, and data models are intentionally out of scope — see the PRD/TRD/App Flow docs for those.

---

## Table of Contents

1. Design Philosophy & Brand Personality
2. Visual Identity System
3. Design Tokens
4. Typography System
5. Spacing & Grid System
6. Component Library
7. Charts & Data Visualization
8. Graph Visualization (Threat Intelligence Engine)
9. Motion & Animation Guidelines
10. Loading, Error, and Empty States
11. Dark Mode / Light Mode Specification
12. Accessibility Rules
13. Responsive Behavior (Desktop / Tablet / Mobile)
14. Module 1 — Citizen Fraud Shield (Design Spec)
15. Module 2 — Law Enforcement Dashboard (Design Spec)
16. Module 3 — Threat Intelligence Engine (Design Spec)
17. Navigation, Header, Sidebar, Search, Filters
18. Dialogs, Drawers, Toasts
19. Component Hierarchy (Figma File Structure)
20. Design Inspiration References

---

## 1. Design Philosophy & Brand Personality

### 1.1 The Core Tension Truvia Must Resolve

Truvia is one product with two emotional registers, and the design has to hold both without feeling like two different products glued together:

- **Module 1 (Citizen Fraud Shield)** is used by someone in genuine distress — mid-scam-call, adrenaline up, possibly seconds from making an irreversible transfer. The UI's job is to feel like a calm, competent hand on the shoulder: fast, unambiguous, zero cognitive tax.
- **Modules 2 & 3 (Officer Dashboard, Threat Intelligence Engine)** are used by a trained analyst doing sustained, detail-dense work across an 8-hour shift. The UI's job is to feel like a precision instrument: dense, fast to scan, low-glare, built for hours of use — not a "wow" moment, a *trust* moment.

One brand, two postures. Same DNA (color system, type, iconography, motion) expressed at two different densities and two different default themes.

### 1.2 Design Philosophy — Five Principles

1. **Explain, never just declare.** Every AI output — a threat score, a risk tier, a cluster — must show its reasoning inline, not behind a tooltip nobody clicks. If a number appears, its "why" is visually adjacent, not one click away.
2. **Calm under pressure.** No red alarms flashing for their own sake. Severity is communicated through a disciplined, consistent color/badge vocabulary — never through panic-inducing motion or oversized alert chrome.
3. **Density with air.** Officer-facing screens are information-dense by necessity, but density is not clutter. Generous internal padding inside dense components (tables, cards) keeps dense screens scannable rather than overwhelming.
4. **Evidence-grade, not consumer-cute.** No mascots, no illustrated empty-state characters, no playful micro-copy. Truvia is closer in spirit to a court exhibit than a mobile app — every visual choice should survive being shown to a judge, a police commissioner, or a hackathon panel without feeling frivolous.
5. **One system, worn two ways.** A component built once (a Card, a Badge, a Button) must work in both the light citizen theme and the dark analyst theme without being redesigned — only re-skinned via tokens.

### 1.3 Brand Personality (as a person)

If Truvia were a person, they'd be: **a former intelligence analyst who now runs citizen literacy workshops.** Precise, unflashy, deeply competent, speaks in plain language when talking to a scared citizen and in structured shorthand when talking to another analyst — but it's recognizably the same person in both rooms. Not corporate-friendly (no chatbot cuteness), not cold-bureaucratic (no Kafkaesque government-portal energy). The tone is: **"We see this clearly. Here's exactly what's happening, and here's what to do."**

**Brand personality is NOT:** playful, gamified, startup-hype, mascot-driven, or alarmist.
**Brand personality IS:** precise, calm, evidentiary, quietly confident, citizen-respectful.

---

## 2. Visual Identity System

### 2.1 Logo & Mark Direction (guidance for whoever builds the mark)

- Wordmark: "Truvia" set in the heading typeface (Inter Semibold), tight tracking, sentence case — not all-caps, not a gimmick logotype. All-caps reads too governmental-cold; Truvia should read *precise but human*.
- Mark concept direction: a simple geometric form suggesting a **verified path/route** (a checkmark fused with a directional arrow, or a single unbroken line resolving into a checkmark) — reinforcing "the path to truth," not a shield or padlock cliché (avoid generic "cybersecurity shield" icons; every fraud/security product uses a shield, Truvia should not).
- The mark should work as a single-color glyph (for favicon, dark-mode nav) and should never require a gradient to read correctly.

### 2.2 Color Palette

Truvia's palette is a **single source of truth** carried into both themes via tokens (see §3). The palette below is the canonical set; do not introduce new hues in Figma without adding them here first.

| Role | Token Name | Hex | Usage |
|---|---|---|---|
| Primary — Trust Navy | `color.brand.navy` | `#0B1E39` | Primary nav chrome, dark-theme surfaces, citizen-theme header |
| Secondary — Intelligence Blue | `color.brand.blue` | `#1959B8` | Primary buttons, links, active nav states, focus rings |
| Blue — Hover/Active | `color.brand.blue.dark` | `#134A96` | Hover/pressed states on blue elements |
| Critical | `color.severity.critical` | `#D6303C` | Critical threat score, destructive actions |
| High | `color.severity.high` | `#E8703D` | High severity band (distinct from Critical *and* Amber — see §2.3) |
| Moderate/Warning | `color.severity.moderate` | `#E8A33D` | Moderate severity band, warning banners |
| Low/Safe | `color.severity.low` | `#1F9D6B` | Low-risk, verified, success states |
| Info | `color.info` | `#3B82C4` | Informational banners, non-severity data highlights |
| Neutral Surface (light) | `color.surface.light` | `#F5F7FA` | Citizen theme background |
| Neutral Surface (dark) | `color.surface.dark` | `#0F1621` | Officer/Intel theme background |
| Elevated Surface (light) | `color.surface.light.raised` | `#FFFFFF` | Cards, panels on light theme |
| Elevated Surface (dark) | `color.surface.dark.raised` | `#161F2E` | Cards, panels on dark theme |
| Elevated Surface (dark, level 2) | `color.surface.dark.raised2` | `#1D2839` | Nested cards, hover states on dark surfaces |
| Border (light) | `color.border.light` | `#E2E8F0` | Dividers, card outlines on light theme |
| Border (dark) | `color.border.dark` | `#28374D` | Dividers, card outlines on dark theme |
| Text Primary (light) | `color.text.light.primary` | `#111827` | Body copy on light theme |
| Text Secondary (light) | `color.text.light.secondary` | `#5B6472` | Captions, metadata on light theme |
| Text Primary (dark) | `color.text.dark.primary` | `#E5E7EB` | Body copy on dark theme |
| Text Secondary (dark) | `color.text.dark.secondary` | `#8B97A8` | Captions, metadata on dark theme |
| Entity/Data Accent | `color.data.mono` | `#5B8DEF` | Monospace entity values (phone/UPI/hash) accent tint |

**Severity Band System — the single most important visual convention in the product.** It must render identically across all three modules:

| Band | Color | Badge background | Badge text |
|---|---|---|---|
| Critical | `#D6303C` | 12% opacity fill of `#D6303C` | `#D6303C` (light) / `#FF6B74` (dark, lightened for contrast) |
| High | `#E8703D` | 12% opacity fill | `#E8703D` (light) / `#FF9868` (dark) |
| Moderate | `#E8A33D` | 12% opacity fill | `#B8791E` (light, darkened for AA contrast on white) / `#F0B860` (dark) |
| Low | `#1F9D6B` | 12% opacity fill | `#1F9D6B` (light) / `#4CC490` (dark) |

Note the dark-theme text colors are deliberately lightened/shifted versions of the base hue, not the raw base hex — this is required to hit WCAG AA contrast against the dark surface tokens (see §12).

### 2.3 Why Four Severity Colors, Not Three

The PRD specifies Low/Moderate/High/Critical (four bands). Resist the temptation to reuse Amber for both Moderate and High — a distinct High (burnt orange, `#E8703D`) sitting visually between Amber and Red is essential so an officer scanning a table of badges can distinguish High from Critical at a glance without reading the text.

### 2.4 Iconography

- **Icon set:** Line icons only, 1.5px stroke weight, rounded joins — no filled/solid icon style, no duotone, no gradient icons. (Recommend building on **Phosphor Icons** or **Lucide** as a base set — both are line-first, MIT-licensed, and have the coverage this product needs: shield, graph-node, magnifier, flag, gauge, etc.)
- **No mascots, no illustrated characters, anywhere in the product** — this includes empty states (§10.3).
- Entity-type icons (phone, UPI, email, domain, device, IP) form a small dedicated icon subset used consistently across Module 2 and Module 3 — each entity type gets exactly one icon, used identically in tables, graph nodes, and detail panels.
- Icon sizing scale: 16px (inline/dense table contexts), 20px (default UI, buttons, nav), 24px (section headers, empty states), 32px (feature/marketing contexts only).

---

## 3. Design Tokens

Tokens are structured in three tiers: **Primitive → Semantic → Component**. Figma should mirror this as Variable Collections: `Primitives`, `Semantic/Light`, `Semantic/Dark`, with component-level tokens referencing semantic tokens only (never primitives directly) so theme-switching is a single variable-mode toggle.

### 3.1 Primitive Tokens (raw values, theme-agnostic)

```
color.primitive.navy.900   #0B1E39
color.primitive.navy.700   #16294A
color.primitive.blue.600   #1959B8
color.primitive.blue.700   #134A96
color.primitive.red.600    #D6303C
color.primitive.orange.500 #E8703D
color.primitive.amber.500  #E8A33D
color.primitive.green.600  #1F9D6B
color.primitive.gray.50    #F5F7FA
color.primitive.gray.100   #E2E8F0
color.primitive.gray.400   #8B97A8
color.primitive.gray.700   #5B6472
color.primitive.gray.900   #111827
color.primitive.slate.950  #0F1621
color.primitive.slate.900  #161F2E
color.primitive.slate.800  #1D2839
color.primitive.slate.700  #28374D

font.family.heading    "Inter"
font.family.body       "Inter"
font.family.mono       "JetBrains Mono"

radius.xs   4px
radius.sm   6px
radius.md   8px
radius.lg   12px
radius.xl   16px
radius.full 9999px

space.0   0px    space.1  4px    space.2  8px
space.3   12px   space.4  16px   space.5  20px
space.6   24px   space.8  32px   space.10 40px
space.12  48px   space.16 64px   space.20 80px

shadow.sm   0 1px 2px rgba(11,30,57,0.06)
shadow.md   0 4px 12px rgba(11,30,57,0.10)
shadow.lg   0 12px 32px rgba(11,30,57,0.16)
shadow.focus 0 0 0 3px rgba(25,89,184,0.35)
```

### 3.2 Semantic Tokens — Light Theme (Citizen Fraud Shield default)

```
bg.canvas          → primitive.gray.50
bg.surface         → #FFFFFF
bg.surface.hover   → primitive.gray.50
border.default     → primitive.gray.100
text.primary       → primitive.gray.900
text.secondary     → primitive.gray.700
text.on-brand      → #FFFFFF
brand.primary      → primitive.blue.600
brand.primary.hover→ primitive.blue.700
nav.bg             → primitive.navy.900
nav.text           → #FFFFFF
nav.text.muted     → rgba(255,255,255,0.65)
```

### 3.3 Semantic Tokens — Dark Theme (Officer / Intelligence default)

```
bg.canvas          → primitive.slate.950
bg.surface         → primitive.slate.900
bg.surface.hover   → primitive.slate.800
bg.surface.sunken  → #0A1119
border.default     → primitive.slate.700
text.primary       → #E5E7EB
text.secondary     → primitive.gray.400
text.on-brand      → #FFFFFF
brand.primary      → primitive.blue.600
brand.primary.hover→ #2E6BD1  (lightened for dark-surface hover legibility)
nav.bg             → #08111F  (deeper than canvas — nav should recede)
nav.text           → #E5E7EB
nav.text.muted     → rgba(229,231,235,0.55)
```

### 3.4 Component Tokens (examples — pattern to follow for all components)

```
button.primary.bg           → semantic.brand.primary
button.primary.bg.hover     → semantic.brand.primary.hover
button.primary.text         → semantic.text.on-brand
button.primary.radius       → radius.md
card.bg                     → semantic.bg.surface
card.border                 → semantic.border.default
card.radius                 → radius.lg
card.padding                → space.6
card.shadow                 → shadow.sm (light theme only; dark theme uses border, not shadow — see §11)
badge.critical.bg           → rgba(214,48,60,0.12)
badge.critical.text         → color.severity.critical (theme-adjusted per §2.2)
```

---

## 4. Typography System

### 4.1 Typefaces

- **Headings & UI:** Inter — Semibold (600) for headings, Medium (500) for UI labels/buttons, Regular (400) for body.
- **Data/Entity/Monospace:** JetBrains Mono — used *exclusively* for entity values (phone numbers, UPI IDs, hashes, IP addresses, case IDs). This is a deliberate forensic cue: the moment text switches to monospace, the user's eye reads it as "this is a raw data value, not prose." Never use JetBrains Mono for body copy or headings.

### 4.2 Type Scale (desktop base — 1rem = 16px)

| Token | Size / Line-height | Weight | Usage |
|---|---|---|---|
| `type.display` | 36px / 44px | Semibold | Module landing hero (Citizen home only) |
| `type.h1` | 28px / 36px | Semibold | Page titles |
| `type.h2` | 22px / 30px | Semibold | Section headers |
| `type.h3` | 18px / 26px | Semibold | Card titles, panel headers |
| `type.h4` | 15px / 22px | Medium | Sub-section labels, table column headers (uppercase, letter-spacing 0.02em) |
| `type.body` | 15px / 24px | Regular | Default body copy |
| `type.body-sm` | 13px / 20px | Regular | Secondary/dense body copy (officer tables) |
| `type.caption` | 12px / 16px | Regular | Timestamps, metadata, helper text |
| `type.mono` | 13px / 20px | Regular (JetBrains Mono) | Entity values, IDs, hashes |
| `type.mono-lg` | 16px / 24px | Medium (JetBrains Mono) | Entity value as a hero element (Entity Explorer header) |

### 4.3 Density Variants

Officer/Intelligence screens (dense tables, graph panels) use `type.body-sm` as their *default* body size, not `type.body`; Citizen screens use `type.body` as default. This one-step size difference is intentional and is the primary lever for expressing the "calm consumer surface" vs. "dense professional tool" distinction — not a different typeface, just a different comfortable reading density.

### 4.4 Mobile Type Scale Adjustments

On mobile (Citizen Fraud Shield only — see §13), reduce `type.display` to 28px/36px and `type.h1` to 24px/32px; all other sizes remain constant, since 15px body text is already comfortable at mobile viewing distance.

---

## 5. Spacing & Grid System

### 5.1 Base Unit

8px base grid, with a 4px half-step available for icon/text micro-alignment only (never for macro layout spacing). All component padding, gaps, and margins should resolve to values in the `space.*` token scale (§3.1).

### 5.2 Grid — Desktop (≥1280px)

- 12-column grid, 24px gutters, max content width 1440px, centered, with a minimum 32px outer margin.
- Officer/Intelligence dashboards use the full 12 columns for dense layouts (e.g., KPI row = 4 cards × 3 columns each, or 5 cards using a 12-col grid with asymmetric spans).
- Citizen Fraud Shield content is capped at an 8-column-equivalent reading width (~800px) even inside the 12-col grid, centered — because it is a linear, single-task flow, not a dashboard, and should never stretch full-width on large monitors.

### 5.3 Grid — Tablet (768–1279px)

- 8-column grid, 20px gutters, 24px outer margin.
- Officer dashboard KPI row reflows from 4/5-across to 2-across; sidebar collapses to icon-only rail (see §17.2).

### 5.4 Grid — Mobile (<768px)

- 4-column grid, 16px gutters, 16px outer margin.
- Single-column stacking for all card/KPI rows.
- Citizen Fraud Shield is designed mobile-first at 375px base width, scaling up — not a shrunk desktop layout.

### 5.5 Layout Regions (Officer/Intelligence shell)

Standard three-region desktop shell: **Sidebar (fixed 240px expanded / 72px collapsed) + Header (fixed 64px height) + Content Canvas (fluid, scrollable, 32px padding)**. This shell is identical across `/officer/*` and `/intelligence/*` route groups — only the content canvas changes — so switching modules never feels like switching apps.

---

## 6. Component Library

Below: visual and behavioral spec for every core component. Each entry is Figma-buildable as a component with the listed variants.

### 6.1 Buttons

**Variants:** Primary, Secondary, Tertiary/Ghost, Destructive, Icon-only.
**Sizes:** Small (32px height), Medium (40px height, default), Large (48px height — Citizen Fraud Shield primary CTAs only).

| Variant | Background | Text | Border | Use |
|---|---|---|---|---|
| Primary | `brand.primary` | white | none | One per screen/section — the single most important action |
| Secondary | transparent | `brand.primary` | 1px `brand.primary` | Secondary actions alongside a Primary |
| Tertiary/Ghost | transparent | `text.secondary` | none | Low-emphasis actions (Cancel, Dismiss) |
| Destructive | `severity.critical` | white | none | Suspend, Remove, Delete — always paired with a confirmation dialog (§18) |
| Icon-only | transparent | `text.secondary` | none, circular hover bg | Table row actions, header icons |

- Corner radius: `radius.md` (8px) across all button sizes — no pill-shaped buttons (reinforces the "instrument," not "app," register).
- All buttons: 150ms ease-out background/border transition on hover; 100ms on press (scale 0.98 + darken, no bounce).
- Disabled state: 40% opacity, no hover transition, cursor not-allowed.
- Loading state: label replaced by a 16px spinner (same color as label), button width does not reshrink (min-width locked to the label's natural width to avoid layout jump).

### 6.2 Cards

- Base card: `card.bg`, `card.border` 1px, `card.radius` 12px, `card.padding` 24px (desktop) / 16px (mobile).
- Light theme cards use `shadow.sm`; **dark theme cards use border-only, no shadow** — shadows read poorly on dark surfaces and a border-driven hierarchy is the SOC-dashboard convention (see §11.2).
- Card header pattern: title (`type.h3`) + optional metadata/badge on the right, 16px bottom margin before card body.
- **KPI Card** (Module 2 dashboard): large numeral (`type.display`, tabular figures), label below in `type.caption` uppercase, optional trend indicator (small arrow + percentage in severity-appropriate color) top-right.
- **Entity Card** (Module 3): entity-type icon + monospace value as header, risk-tier badge top-right, connection count + last-seen timestamp as metadata row.

### 6.3 Tables

- Row height: 48px (default/dense officer tables), 56px (Citizen History — slightly more breathing room).
- Header row: sticky on scroll, `type.h4` styling, sortable columns show a subtle chevron on hover, active sort shows a solid chevron in `brand.primary`.
- Zebra striping: **not used** — instead, a 1px `border.default` divider between rows and a hover-state background tint (`bg.surface.hover`) is the only row-differentiation mechanism. Zebra striping reads as "spreadsheet," Truvia should read as "application."
- Row selection (bulk actions): checkbox column, selected row gets a subtle `brand.primary` left-border accent (3px) plus tinted background.
- Cell content conventions: severity/status → Badge component (never plain colored text); entity values → monospace; dates → relative format on hover-reveal absolute (`"3 days ago"` with tooltip showing exact timestamp).
- Virtualized rendering required for Complaint Table (PRD specifies scale) — Figma should still spec the full visual row design; virtualization is an engineering concern, not a visual one, but empty/loading skeleton rows (§10.1) must match exact row height to avoid scroll-jump.

### 6.4 Forms & Inputs

- Input height: 40px default, 48px for Citizen Fraud Shield primary inputs (paste-text box).
- Border: 1px `border.default`, `radius.md`; focus state: border becomes `brand.primary` + `shadow.focus` ring (3px, 35% opacity) — never rely on border-color-change alone for focus (accessibility, §12).
- Label above input, `type.h4` weight, always visible (no placeholder-as-label pattern — placeholders disappear on input and hurt usability, especially for a stressed citizen user).
- Helper text below input in `type.caption`, `text.secondary`.
- Inline validation error: border becomes `severity.critical`, error message below in `severity.critical` text with a small error icon, appears on blur/submit — never live-validates on every keystroke (that reads as nagging, especially bad for an anxious user).
- **Dropzone (multi-modal upload, Citizen Fraud Shield):** large dashed-border zone (`border.default`, 2px dashed, `radius.lg`), centered icon + "Drop a screenshot, audio file, or paste text" copy, changes to solid `brand.primary` border + light blue tint background on drag-over.

### 6.5 Badges

- Shape: `radius.full` (pill), 4px vertical / 10px horizontal padding, `type.caption` weight Medium.
- **Severity badges** (Critical/High/Moderate/Low): colored text + 12%-opacity background fill of the same hue, small dot or icon prefix optional for extra scanability in dense tables.
- **Status badges** (Processing/Indexed/Escalated/Assigned): neutral gray fill unless the status has inherent severity meaning (e.g., "Failed" borrows the Critical treatment).
- **Confidence indicator:** a distinct visual treatment from severity badges — shown as a small horizontal bar/meter + percentage, not a colored pill, so it is never visually confused with a threat-severity badge (PRD explicitly requires these to be perceived as separate concepts).

### 6.6 Modals / Dialogs

See §18 for full behavioral spec. Visual: `radius.lg`, `shadow.lg`, max-width 480px (confirmation dialogs) or 640px (form dialogs like Invite/Add Document), centered, with a scrim at 60% `navy.900` opacity behind (both themes — the scrim does not change with theme, only the modal surface does).

### 6.7 Drawers

Right-side slide-in, full-height, 400px width (desktop) / 100vw (mobile), `shadow.lg` on the leading edge, `card.bg` surface. Used for the AI Chat Assistant (§18.9) and Investigation View tabs, when a full-page context switch would be disruptive.

---

## 7. Charts & Data Visualization

### 7.1 Charting Principles

- All charts are built for **scanning, not decoration** — no 3D effects, no drop-shadows on chart elements, no gratuitous gradients on bars/areas.
- Chart color always maps to the same semantic palette as the rest of the product — a Critical-severity data point is the same red everywhere, whether it's a badge, a bar, or a graph node.
- Every chart ships with an accessible data-table equivalent (toggle or adjacent) — required per PRD accessibility principle (§12).
- Recommended library: **Recharts** (already selected in tech stack) — themeable via the token system, SVG-based (crisp at any zoom), sufficient for all specified chart types.

### 7.2 Chart Types & Specs

| Chart | Used In | Visual Spec |
|---|---|---|
| Threat Score Gauge (radial) | Citizen Result screen | Semi-circular arc, 270°, needle or filled-arc style, band-colored (color shifts along the arc matching severity thresholds), large numeral in center |
| Complaint Trends (time-series) | Officer Dashboard | Line or smoothed-area chart, 2px stroke, subtle 8%-opacity area fill under the line, gridlines at 1px `border.default`, no gridline on the value axis (only horizontal reference lines) |
| Threat Score Distribution (histogram) | Officer Dashboard | Vertical bar histogram, bars colored by which severity band their bin falls into (not a single flat color) — this turns a plain histogram into an at-a-glance severity distribution |
| City/District Analysis (bar) | Officer Dashboard | Horizontal bar chart when >6 categories (easier label reading than vertical), sorted descending by value |
| Confidence Meter | Threat Assessment panel | Thin horizontal segmented bar (not circular), distinctly different shape from severity badges (see §6.5) |

### 7.3 Chart Empty/Loading States

Charts never render a blank canvas while loading — show a skeleton chart shape (flat-line placeholder bars/area at 40% height, shimmer animation) matching the eventual chart type, so layout doesn't jump when real data arrives.

---

## 8. Graph Visualization (Threat Intelligence Engine)

This is the product's centerpiece visual — it needs the most deliberate design attention.

### 8.1 Canvas & Node Design

- Full-bleed canvas, dark-theme background (`bg.canvas`, near-black navy) regardless of light/dark toggle state elsewhere — the graph canvas is *always* dark, even if a future setting allowed light-mode elsewhere in Module 3, because node/edge contrast and the "SOC command center" feel depend on a dark canvas.
- Nodes are circles, sized by connection-degree (more connections = larger node, within a capped min/max range so no node dominates the canvas).
- Node color = entity type (a fixed, distinct hue per type: phone, UPI, email, domain, device, IP — six distinguishable hues, colorblind-safe pairing verified against a simulator), with a **thin colored ring overlay** indicating risk tier (Critical/High/Moderate/Low ring color) — so entity-type and risk-tier are both visible at once without conflating them into one color channel.
- Edges are thin (1px) lines at low opacity (30–40%) by default, brightening to full opacity + slightly thicker on hover/selection of either connected node — this is essential for legibility once a graph has hundreds of nodes.
- Edge labels (relationship type: "same phone used in," "same UPI linked to") appear only on hover/selection, never rendered by default (would create unreadable clutter at scale).

### 8.2 Cluster / Fraud Ring Rendering

- Detected fraud rings render as a soft, low-opacity (10–15%) colored convex-hull/blob background behind the cluster's nodes — a "highlighter" effect, not a hard-bordered box — so multiple overlapping considerations (selection state, hover state) still read clearly on top.
- Each distinct ring gets a rotating color from a small fixed "cluster palette" (5–6 hues, separate from the entity-type and severity palettes, to avoid triple-encoding confusion) — cycling if there are more rings than palette colors.

### 8.3 Interaction Model

- Zoom/pan: standard scroll-to-zoom, drag-to-pan, with a reset-view button pinned to a canvas corner.
- Click a node → lightweight preview panel slides in from the right (§10.10 in App Flow — this is the "Entity Explorer Side Panel Overlay," distinct from the full drawer).
- Click-and-hold / double-click a node → expand its immediate neighbors (lazy-load pattern, per the PRD's performance risk mitigation) with a brief (300ms) expand animation so new nodes don't just pop in.
- A persistent **legend** (entity-type color key + risk-tier ring key) is pinned to a bottom-left canvas corner, collapsible.

### 8.4 Performance-Driven Visual Fallback

Per PRD risk mitigation (cap initial render to top-N highest-risk clusters): the **visual design must make this feel intentional, not limited** — a small persistent canvas label reading "Showing top 25 highest-risk clusters · Expand to explore further" communicates this as a deliberate triage feature, not a technical shortfall.

### 8.5 Investigation Timeline (graph-driven)

A horizontal timeline component beneath or beside the graph canvas for ring-activity reconstruction: a simple horizontal axis with dated event markers (dots sized by event significance), connecting lines to show sequence, rendered in the same dark canvas register as the graph itself — not a separate visual language.

---

## 9. Motion & Animation Guidelines

### 9.1 Motion Principles

- **Purposeful, never decorative.** Every animation should communicate a state change (something loaded, something opened, something succeeded) — never motion for its own sake.
- **Fast.** 120–250ms for most UI transitions; nothing in the core interaction loop should feel like it's "performing" for the user. This is an instrument, not a showcase.
- **No bounce/elastic easing anywhere** — use `ease-out` for entrances, `ease-in` for exits, `ease-in-out` for state toggles. Bounce easing reads as playful/consumer, wrong register for this product.

### 9.2 Timing Reference Table

| Interaction | Duration | Easing |
|---|---|---|
| Button hover/press | 100–150ms | ease-out |
| Card/panel hover elevation | 150ms | ease-out |
| Modal open/close | 200ms (scale 0.96→1 + fade) | ease-out (open) / ease-in (close) |
| Drawer slide-in/out | 250ms | ease-out (in) / ease-in (out) |
| Toast enter/exit | 200ms slide+fade | ease-out |
| Page/route transition | 150ms fade (content only, chrome stays static) | ease-in-out |
| Graph node expand | 300ms | ease-out |
| Skeleton shimmer loop | 1400ms loop | linear |
| Processing stepper stage transition | 400ms (checkmark draw-in) | ease-out |
| Threat gauge fill animation | 600ms, on result reveal only (not on every re-render) | ease-out |

### 9.3 The Processing Stepper — Special Motion Case

The Citizen Fraud Shield's live processing stepper ("Extracting text… → Analyzing threat patterns… → Cross-checking known fraud entities…") is the single most important motion moment in the citizen journey — it's what makes the product feel like "a real intelligence system working," not a spinner. Each stage should: appear with its icon in a neutral/pending state → transition to an active pulsing state (subtle opacity breathing, 1.5s loop, not distracting) while processing → resolve to a filled checkmark with a quick 400ms draw-in animation. Stages that complete stay visible (crossed off), not collapsed away — the citizen should see the full pipeline they just watched happen.

### 9.4 Reduced Motion

All animations must respect `prefers-reduced-motion` — reduce to instant/near-instant opacity crossfades only (no slides, no scales, no shimmer loops) when the OS setting is active. This is a hard accessibility requirement, not optional polish.

---

## 10. Loading, Error, and Empty States

### 10.1 Loading States (three-tier, per App Flow §3.1)

- **Skeleton state:** Gray placeholder blocks (`bg.surface.hover` tone) matching final content shape exactly — card skeletons match card dimensions, table skeletons match row height/column widths. Shimmer sweep animation, 1400ms loop, `linear` easing, moving left-to-right at 45°.
- **Background refetch:** A 2px progress bar pinned to the top edge of the content area (not the whole page), `brand.primary` color, indeterminate animation — existing content remains fully visible and interactive underneath.
- **Action-in-progress:** Triggering button only — inline spinner replaces label (§6.1), rest of the page stays interactive. Never dim/disable the entire screen for a single button's async action.

### 10.2 Error States

- **Inline field error:** Red border + icon + message directly below the field, `severity.critical` color, appears on blur/submit.
- **Request-failure banner:** Full-width banner at the top of the content area (below header, above content), `severity.critical`-tinted background (12% opacity) with a solid left border accent (4px), icon + message + "Retry" button inline on the right, dismissible via X.
- **Full-page error fallback:** Centered layout, icon (a simple broken-connection or alert-triangle line icon — no illustration), `type.h2` message ("Something went wrong"), `type.body` supporting text, single "Reload" primary button. Used only for uncaught render exceptions.
- **Degraded-mode indicator (OCR/ASR low-confidence, LLM fallback):** Not an error — an **amber informational banner**, inline within the result content (not a floating alert), phrased transparently per PRD philosophy ("the system knows when it's unsure" as a feature): "Some details in this result have lower confidence — [reason]." This is a distinct visual treatment from a true error state.

### 10.3 Empty States

- Structure: icon (24px, `text.secondary` color, line-style — never a large illustration or mascot) + one-line explanation (`type.body`, `text.secondary`) + primary CTA button where actionable.
- Example (Citizen History, empty): magnifier-with-checkmark icon + "You haven't submitted any reports yet" + "Check a suspicious message" primary button.
- Example (Complaint Table, filtered to zero results): filter-slash icon + "No complaints match these filters" + "Clear filters" secondary button (not primary — this is a recovery action, not a forward action).
- Example (Graph Home, no entities yet — cold-start demo edge case): a distinct "graph is empty" state should still look intentional, not broken — centered icon + short explanatory copy, never an empty dark canvas with no messaging.

---

## 11. Dark Mode / Light Mode Specification

### 11.1 Theme-to-Route Mapping (fixed, not user-toggleable per module)

Per the App Flow's route-group/theme mapping: `/fraud-shield/*` is **always light theme**; `/officer/*`, `/intelligence/*`, `/admin/*` are **always dark theme**; `/login`, `/register`, `/account/*` use a neutral theme that adapts to the logged-in user's role (or defaults light when logged out). **Do not build a global light/dark toggle for MVP** — theme is a function of which surface you're on, reinforcing the citizen-vs-analyst design posture split described in §1.1. (A future "officer prefers light mode" user-level override is a reasonable v2 item but is explicitly out of MVP scope, matching the PRD's RBAC/v2 deferral pattern.)

### 11.2 Dark Theme Construction Rules

- Dark theme surfaces are built with **layered flat tones**, not shadows: `bg.canvas` (deepest) → `bg.surface` (cards) → `bg.surface.hover`/`raised2` (nested elements, hover states) → each step roughly 4–6% lighter in luminance. Shadows are omitted entirely on dark surfaces (they render as muddy, low-contrast smudges on dark backgrounds); hierarchy comes from this luminance stepping plus 1px borders.
- Never use pure black (`#000000`) backgrounds — the deepest dark token is `#0F1621` (a near-black navy), which is easier on the eyes for sustained analyst use and keeps the brand's navy identity present even in dark mode.
- Text contrast: `#E5E7EB` primary text against `#0F1621`/`#161F2E` surfaces comfortably clears WCAG AA; never use pure white (`#FFFFFF`) body text on dark surfaces — it creates uncomfortable glare during long sessions.

### 11.3 Light Theme Construction Rules

- Light theme uses the inverse logic: white/near-white raised surfaces on a very light gray canvas (`#F5F7FA`), with `shadow.sm`/`shadow.md` doing the elevation work that borders/luminance-steps do in dark mode.
- Light theme should feel closer to a well-designed consumer fintech app (think a banking app's clarity) than to a government portal — approachable, whitespace-forward, not dense.

---

## 12. Accessibility Rules

- **Contrast:** WCAG AA minimum (4.5:1 body text, 3:1 large text/UI components) verified across every token pairing in both themes — this is why several severity-band text colors are theme-shifted (§2.2) rather than using one hex everywhere.
- **Never color-only encoding:** Every severity badge includes text, not just color. Every chart has an accessible data-table alternative. Graph node risk-tier uses a ring shape/color combination, and entity type uses distinct icons inside nodes at high enough zoom, not color alone.
- **Focus states:** Every interactive element has a visible focus ring (`shadow.focus` token — 3px, 35%-opacity brand-blue ring) distinguishable from hover state; never `outline: none` without a replacement.
- **Keyboard navigation:** The entire Citizen Fraud Shield flow — upload, view result, chat, download, escalate — must be fully operable via keyboard alone, per PRD's explicit callout that this matters for an anxious, possibly motor-impaired-by-stress user. Tab order follows visual reading order; the AI Chat drawer traps focus while open and returns focus to its trigger button on close.
- **Motion:** `prefers-reduced-motion` respected globally (§9.4).
- **Touch targets:** Minimum 44×44px tappable area on all mobile interactive elements, even where the visual element (e.g., an icon button) is smaller — achieved via padding, not by inflating the icon itself.
- **Screen reader labeling:** Icon-only buttons always carry an `aria-label`; severity badges announce as "Critical severity," not just the color; the graph canvas ships with an accessible list-view alternative for the entity/relationship data (a toggle: "Switch to list view") since a force-directed canvas is inherently screen-reader-hostile.

---

## 13. Responsive Behavior

### 13.1 Desktop (≥1280px)

- Full three-region shell (sidebar + header + canvas) for Modules 2/3.
- Citizen Fraud Shield: centered single-column content, max ~800px reading width, generous side margins — never stretches full-bleed.
- Graph canvas: full available canvas area, side panels overlay (not push) the canvas.

### 13.2 Tablet (768–1279px)

- Sidebar collapses to a 72px icon-only rail (icons + tooltips on hover), expandable via a toggle; content canvas reflows KPI rows from 4/5-across to 2-across.
- Citizen Fraud Shield reflows naturally (already narrow-content by design) — minimal change from desktop besides margin reduction.
- Complaint Table: lower-priority columns (e.g., "Assigned Officer") collapse behind a "More" overflow or become visible only on row-expand, to prevent horizontal scroll.
- Graph canvas: side panels shift from overlay to full-width bottom sheet on entity selection, to preserve horizontal canvas space.

### 13.3 Mobile (<768px)

- **Citizen Fraud Shield only** is required to be fully functional on mobile (PRD explicit scope) — designed mobile-first, not adapted-down.
  - Bottom-anchored primary CTA pattern for the upload flow (thumb-reachable).
  - Processing stepper becomes a compact horizontal progress bar with the current stage's label beneath it (full vertical stepper doesn't fit comfortably above the fold).
  - AI Chat drawer becomes a full-screen takeover (not a 400px side panel) with a clear back/close affordance.
  - Toasts anchor bottom-center instead of bottom-right.
- **Modules 2 & 3 are not required to be fully functional on mobile for MVP** (PRD explicit scope) — however, they should degrade gracefully rather than break: sidebar becomes a slide-out drawer triggered by a hamburger icon, KPI cards and tables stack single-column, and the graph canvas shows a "best viewed on a larger screen" notice with a simplified read-only entity list as a fallback, rather than attempting a full force-directed canvas on a small viewport.

---

## 14. Module 1 — Citizen Fraud Shield (Design Spec)

**Theme:** Light, mobile-first. **Emotional target:** calm, fast, trustworthy — never alarmist, never cutesy.

### 14.1 Home / Upload Screen

- Minimal header: Truvia wordmark left, a single "History" text-link or icon right — no dense nav bar; this screen should feel like an app's single purpose, not one of many tabs.
- Hero area: short reassuring headline ("Check a suspicious call, message, or screenshot in seconds") in `type.display`/`type.h1` (mobile), directly above the dropzone.
- Three input-mode tabs/segmented control (Screenshot / Audio / Paste Text) above a single unified dropzone that adapts its icon/copy per selected mode — not three separate dropzones stacked, which would feel cluttered.
- Below the fold: a lightweight "Recent Public Scam Alerts" card carousel (2–3 visible cards, horizontally scrollable on mobile) — reassures the citizen this is an active, populated system, not a lonely tool.

### 14.2 Processing State

Full-width card replaces the dropzone in place (no page navigation yet) showing the live stepper (§9.3). Calm, confident copy per stage — present tense, active voice ("Extracting text from your screenshot…"), never technical jargon ("Running OCR pipeline" — no).

### 14.3 Result Screen

- Top: Threat Score Gauge (§7.2) as the clear focal point, severity badge and scam-category label directly beside/beneath it — the citizen should understand the verdict in under 2 seconds without reading anything.
- Confidence meter (§6.5) shown as a secondary, visually subordinate element beneath the main score — clearly a "how sure are we" signal, not competing with the primary verdict.
- Explainability panel: an accordion, default-expanded on first view (this is the product's core trust-building moment, don't hide it behind a click), each flagged phrase/pattern shown as a highlighted excerpt with a one-line plain-language reason beside it.
- Recommended Actions: a vertical checklist of action cards, each with an icon + short imperative instruction ("Do not share your OTP") — check-off interaction optional/cosmetic (helps an anxious user feel a sense of control and progress).
- Sticky bottom action bar (mobile) / inline button row (desktop): "Download Report" (secondary) + "Report to Police" (primary) — primary action always visually dominant.
- "Ask the AI Assistant" entry point as a persistent floating action button (bottom-right, mobile-safe-area-aware) opening the chat drawer.

### 14.4 AI Chat Assistant Drawer

Right-side drawer (desktop) / full-screen (mobile). Each assistant response that cites a regulation shows a small citation chip inline (e.g., "RBI Guideline ⓘ") — tapping/hovering reveals the source name, never a bare unExplained claim (core philosophy §1.2 principle 1).

### 14.5 History & Alerts Screens

Simple card-list or table (responsive card-to-row collapse per breakpoint), status badges matching the severity system exactly. Alerts feed uses a card-grid, each card showing scam category, a short pattern description, and a relative "trending" indicator (e.g., a small up-arrow + "+40% this week") — never showing personally identifying details of other citizens' reports (aggregated/anonymized per PRD).

---

## 15. Module 2 — Law Enforcement Dashboard (Design Spec)

**Theme:** Dark, desktop-first, tablet-responsive. **Emotional target:** command-center clarity, built for hours of scanning.

### 15.1 Dashboard Home

- KPI card row across the top (Total Complaints / Active Cases / High-Risk Entities / Fraud Rings Detected / Avg. Threat Score Trend) — each card per §6.2's KPI Card spec, trend arrows colored by whether the trend is favorable or concerning (a rising "Active Cases" count is neutral-to-concerning amber, a rising "Fraud Rings Detected" is informational blue, not necessarily red — trend color should reflect actual meaning, not a blanket "up = bad" assumption).
- Below KPIs: two-column layout (desktop) — Complaint Trends time-series chart (left, wider) + Emerging Scam Trends panel (right, narrower, a ranked list with small sparkline trend indicators per pattern).
- Recent Reports feed beneath, as a compact list (not full table) — links out to the full Complaint Table.

### 15.2 Complaint Table Screen

- Persistent filter bar above the table: category, city, score-range slider, date-range picker, status — filters render as removable chips once applied, so the active filter state is always visible at a glance, not buried in a collapsed filter panel.
- Search field is prominent, top-left of the filter bar, with a magnifier icon and clear placeholder ("Search by phone, UPI ID, complaint ID…").
- Table per §6.3 spec; severity and status columns always use Badge components.

### 15.3 Investigation View

- Two-panel layout: left = tabbed detail panel (Summary / Entities / Evidence / Timeline per App Flow), right = a persistent slim context rail showing key metadata (Case ID in monospace, assigned officer, status, quick-links to "View in Graph").
- AI Summary tab: prose summary card with the same citation-chip convention as the citizen chat (§14.4) — consistency here reinforces "one system" even across very different-looking modules.
- "Generate Intelligence Package" as a prominent primary button pinned near the top of the panel, not buried at the bottom of a long scroll.

### 15.4 Charts (City/District, Score Distribution)

Rendered per §7.2 specs, placed in a secondary "Analytics" tab or lower section of the dashboard home, not competing for primary above-the-fold attention with the KPI/trends/emerging-patterns trio (which is the officer's actual daily triage view).

---

## 16. Module 3 — Threat Intelligence Engine (Design Spec)

**Theme:** Dark, desktop-first. **Emotional target:** the product's "wow, this is real intelligence software" centerpiece.

### 16.1 Graph Home

Full-bleed canvas per §8. A slim top toolbar overlays the canvas (not a separate header region) with: search field (entity lookup), a view-mode toggle (Graph / List), and the legend toggle. This keeps the canvas maximally large — the graph is the screen's entire reason for existing.

### 16.2 Entity Explorer

Full-page layout when navigated directly (vs. the lightweight preview panel from graph clicks, §8.3): header with entity-type icon + monospace value as a large `type.mono-lg` heading + risk-tier badge, then tabs (Overview / Connections / Complaints / Risk History). Connections tab embeds a small local subgraph view (the entity centered, immediate neighbors only) — a "mini" version of the main graph canvas, same visual language, smaller scale.

### 16.3 Fraud Ring List & Detail

Ring List: card-grid, each card showing ring size (entity count), linked-complaint count, dominant scam category, and a small color swatch matching its cluster-palette color from the graph view (§8.2) — so a ring looks the same whether seen as a card or as a highlighted cluster on the canvas.
Ring Detail: the graph canvas pre-filtered/zoomed to just that ring's subgraph, plus a side panel listing correlated complaints (ranked by relevance) and the "Generate Intelligence Package" action.

### 16.4 Package Generation Preview Modal

Per App Flow §10.3 — a modal showing a structured preview (entity count, complaint count, evidence count) before generation; visually this should look like a condensed "table of contents" for the resulting document — small icon rows, each with a count, giving the officer confidence about what they're about to generate before committing.

---

## 17. Navigation, Header, Sidebar, Search, Filters

### 17.1 Header (Officer/Intelligence/Admin shell)

- 64px height, `nav.bg` background, fixed/sticky.
- Left: Truvia wordmark (compact lockup) + current module label.
- Center-right: global search (entity/case quick-lookup) — a single unified search that can resolve to a complaint, an entity, or a ring, with a typeahead dropdown grouping results by type.
- Right: notification bell (system alerts — new emerging trend, package ready), account menu (avatar + role badge + dropdown: Profile / Security / Log out).

### 17.2 Sidebar (Officer/Intelligence/Admin shell)

- 240px expanded, collapsible to 72px icon-rail (toggle pinned at sidebar bottom).
- Top-level items grouped by module: Dashboard, Complaints, My Cases (Officer surface) — Graph, Entities, Rings (Intelligence surface) — Users, Knowledge Base, System Health (Admin surface, shown only to Admin role).
- Active item: `brand.primary`-tinted background + left-border accent (3px), matching the table row-selection convention (§6.3) for visual consistency.
- Admin's cross-surface oversight access (§2.5 in App Flow) is reflected by Admin seeing *all* groups in one sidebar, with a subtle section divider between "My Console" (Admin-specific) and "Oversight" (Officer/Intelligence sections) so it's clear these aren't the Admin's primary daily-use screens.

### 17.3 Citizen Fraud Shield Navigation

Deliberately minimal — no sidebar, no persistent nav bar beyond the compact header described in §14.1. This is the single clearest visual signal that Module 1 is a *task*, not a *dashboard*.

### 17.4 Search & Filters — General Pattern

- Search fields: 40px height, icon-left, `radius.md`, appears as a first-class element in any list/table screen's toolbar — never an icon that expands into a field on click (adds friction for a core, frequently-used action in officer workflows).
- Filters: chip-based active-filter display (removable ×) above any filtered table/list, with an "Add filter" affordance opening a lightweight popover (not a full-page filter form) for adding new filter dimensions.

---

## 18. Dialogs, Drawers, Toasts

### 18.1 Modal Dialogs — Visual Spec

Per §6.6: `radius.lg`, `shadow.lg`, centered, scrim behind. Header (`type.h3` title + close X top-right), body content, footer button row right-aligned (Cancel/secondary left of Confirm/primary, standard convention — Cancel always the visually quieter option so the primary path is unambiguous).

### 18.2 Destructive Confirmations

(Suspend Account, Remove Knowledge Base Document) — the confirm button uses the Destructive button variant (§6.1), and the modal may optionally include a small warning-triangle icon beside the message — but never full-modal red styling (that would feel alarmist for what is often a routine admin action).

### 18.3 Toasts

Per App Flow §3.4/§10.11: bottom-right (desktop) / bottom-center (mobile), 4s auto-dismiss, `radius.md`, `shadow.md`, colored left-border accent (4px) indicating type (success/info/error/warning) rather than a fully-colored toast body — keeps toasts legible and non-jarring even when several might stack.

### 18.4 The AI Chat Drawer (special case)

Distinct from other drawers: includes a persistent input field pinned to the drawer's bottom edge (chat-app convention), message bubbles left-aligned (assistant, `bg.surface.hover` background) vs. right-aligned (user, `brand.primary`-tinted background) — the one place in the product that's allowed to feel slightly more "conversational app" in register, since it is literally a chat interface, but citation chips (§14.4) keep it grounded in the product's evidentiary tone rather than feeling like a generic chatbot.

---

## 19. Component Hierarchy (Figma File Structure)

Recommended Figma file organization for the designer building this out:

```
📁 Truvia Design System
 ├── 📄 Cover / Changelog
 ├── 📄 Foundations
 │    ├── Color (primitive + semantic variables, both modes)
 │    ├── Typography
 │    ├── Spacing & Grid
 │    ├── Iconography
 │    └── Elevation & Radius
 ├── 📄 Components — Core
 │    ├── Buttons (all variants/sizes/states)
 │    ├── Badges (severity, status, confidence meter)
 │    ├── Inputs & Forms
 │    ├── Cards (base, KPI, entity)
 │    ├── Tables
 │    ├── Modals & Dialogs
 │    ├── Drawers
 │    ├── Toasts
 │    └── Navigation (header, sidebar, tabs)
 ├── 📄 Components — Data Viz
 │    ├── Charts (gauge, line/area, histogram, bar)
 │    ├── Graph node/edge/cluster primitives
 │    └── Skeleton/loading variants of each
 ├── 📄 Patterns
 │    ├── Loading states
 │    ├── Empty states
 │    ├── Error states
 │    └── Processing stepper
 ├── 📄 Module 1 — Citizen Fraud Shield (screens, light theme)
 ├── 📄 Module 2 — Officer Dashboard (screens, dark theme)
 ├── 📄 Module 3 — Threat Intelligence Engine (screens, dark theme)
 ├── 📄 Admin Console (screens, dark theme)
 └── 📄 Shared (auth, account, error pages — neutral/adaptive theme)
```

Variable modes: set up `Theme = Light/Dark` as a Figma variable mode at the top of the Foundations page so every component automatically re-skins when a frame's mode is switched — this is what makes the "one system, two postures" principle (§1.1) actually maintainable in the file, not just in prose.

---

## 20. Design Inspiration References

For the designer's calibration — not for direct copying, but as reference points for register and quality bar:

- **Linear** — for the disciplined use of a single accent color, restrained motion, and dense-but-calm information hierarchy (relevant to Officer Dashboard density).
- **Stripe Dashboard** — for how a data-dense financial/security tool keeps tables and KPI cards legible without feeling like a spreadsheet; also a good reference for the light-theme citizen surface's trustworthy-fintech register.
- **Datadog / Grafana** — for dark-theme SOC/NOC dashboard conventions: dense KPI rows, time-series-forward layouts, alert/severity badge vocabulary at scale.
- **Maltego / Neo4j Bloom** — the closest direct analogues for the force-directed graph visualization register (entity nodes, relationship edges, cluster highlighting) in Module 3.
- **Palantir Gotham/Foundry (public marketing materials only)** — for the general "serious intelligence software" visual register this product should evoke: no playfulness, heavy reliance on typographic hierarchy and restrained color to convey authority.
- **Notion / Superhuman** — for the citizen-facing light theme's calm, uncluttered, single-task-focused screen composition (Module 1 home/result screens).
- **Revolut / Monzo (fraud/security alert screens specifically)** — for how consumer fintech apps communicate "something is wrong" to an anxious user without inducing panic — directly relevant to the Citizen Result screen's tone.

---

*End of Design Brief. This document, together with the Truvia PRD, TRD, and App Flow specification, should give a Figma designer everything needed to build the full component library and screen set without further clarification on visual intent.*
