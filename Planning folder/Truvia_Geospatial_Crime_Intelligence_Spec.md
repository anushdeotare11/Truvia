# Truvia — Module 6: Geospatial Crime Pattern Intelligence
## Consolidated Build Spec (PRD + TRD + Schema + UI in one document)

**Why one document, not six:** Same reasoning as the Live Scam Interceptor
spec — this is a single, well-scoped module being built with limited
remaining time, not a new foundational platform. This document has
everything Antigravity needs in one pass.

**Honest scoping note, addressing the earlier concern about this module:**
This module works at **city/district-level aggregation**, not street-level
mapping — because that's the actual granularity your existing seeded data
supports (`reports` are tied to a city/district field, not precise GPS
coordinates from the citizen's device). This is a legitimate, real
capability at that granularity — it answers "which cities/districts need
patrol/investigation priority right now," which is exactly what the
problem statement's "enforcement intelligence and prioritisation" language
asks for. It does **not** claim street-level precision it can't back up.
Framed honestly, this is a strength under Q&A, not a weakness — it's real
and defensible rather than an inflated claim.

---

## 1. What This Module Is

A new officer/admin-facing view that turns the complaint data you already
have into a **geographic priority signal**: which cities/districts have
the highest concentration of recent, severe fraud activity, so patrol and
investigation resources can be pointed somewhere specific instead of
worked case-by-case with no spatial context.

**What makes this a genuinely new capability (not a reskin of the
Complaint Table):** the Complaint Table already lets you filter by city,
but it doesn't rank or score locations against each other, and it doesn't
surface trend direction (is this district getting worse or better) at a
glance. This module adds a real, explainable **Priority Score** per
location and a simple visual density view — a materially different
question ("where should we focus") versus the Complaint Table's question
("show me these specific complaints").

**What it reuses (do not rebuild):** the existing `reports` /
`threat_scores` / `cases` tables and their existing city/category/severity/
timestamp fields, the existing officer dashboard's chart components, the
existing complaint-table filtering pattern, the existing auth/role-guard
pattern.

---

## 2. Build Priority — Backend First, Frontend Is Wiring Only

Same team-wide decision as the previous module: **all remaining time goes
to backend correctness first.** For this module:

- The backend must produce real, correctly-computed priority scores and
  real aggregated geographic data — nothing hardcoded, nothing simplified
  to a fake placeholder ranking.
- Frontend work is feature-addition only: one new screen needs to *exist
  and function* so the backend is reachable and testable, but it should
  reuse existing components as directly as possible with zero time spent
  on layout refinement, visual tuning, or map-styling polish.
- If a full interactive map component is time-expensive to get right
  visually, a **simple ranked table/list view with a basic bar-style
  intensity indicator is an acceptable, even preferable, first cut** —
  it's faster to build correctly, less likely to introduce new frontend
  bugs, and communicates the same real data. An actual map visualization
  can be added in the later polish pass if time allows, but is explicitly
  not required for this pass to be considered complete.

---

## 3. Scope — What's In, What's Explicitly Out

**In scope:**
- Backend aggregation: real complaint counts, severity-weighted scoring,
  and recency weighting, grouped by city/district, computed from actual
  stored data.
- A `GET` endpoint returning ranked location data with the score
  breakdown (not just a final number — the breakdown itself is what makes
  this explainable/defensible).
- A `GET` endpoint returning time-series trend data per location (is this
  location's complaint volume rising or falling over recent weeks).
- A frontend view (table/list, map optional per §2) showing ranked
  locations with their scores and trend direction, filterable by category
  and date range using the existing filter components.
- Drill-through: clicking a location filters the existing Complaint Table
  to that city (reuse the existing `?city=` query param pattern already
  established for cross-module navigation).

**Explicitly out of scope for this pass:**
- Actual GPS/lat-long precision mapping of individual complaints (not
  supported by the underlying data — would require new citizen-side
  location capture, which isn't part of the existing Fraud Shield flow
  and isn't worth adding now).
- Satellite/tile-based interactive map rendering (Leaflet/Mapbox
  integration) unless time genuinely allows after the backend and basic
  view are done — see §2's note on this being optional.
- Any predictive forecasting of future hotspots — this pass is descriptive
  (what's happening now/recently), not predictive.

---

## 4. Data Model — No New Tables Needed

This module deliberately requires **zero schema changes.** All of the data
it needs already exists in `reports` (city field, created_at),
`threat_scores` (severity_band, is_current), and `cases` (status). This is
by design — it keeps this module low-risk and fast to build, since it's
purely a new aggregation/query layer over existing, already-correct data.

If `reports` does not currently have a normalized `city` field (check this
first — it may be embedded in a JSON metadata field or free-text instead),
that is the one thing worth confirming before starting, since the scoring
logic below depends on being able to `GROUP BY` a clean city value.

---

## 5. API Contract

New endpoints, officer/admin role only, following the existing `/api/v1/*`
convention:

| Method & Path | Purpose | Response |
|---|---|---|
| `GET /api/v1/geo/priority?category=&days=` | Ranked location list with score breakdown | `[{city, priority_score, complaint_count, avg_severity_weight, recency_weight, trend: "rising"\|"falling"\|"stable", dominant_category}]` |
| `GET /api/v1/geo/priority/{city}/trend?weeks=` | Time-series complaint volume for one location | `{city, series: [{week_start, complaint_count, avg_severity}]}` |

---

## 6. Priority Score Logic — Real, Explainable, No Black Box

Per city/district, compute:

1. **Complaint density:** raw count of complaints in the selected window
   (default last 30 days).
2. **Severity weight:** average severity across those complaints, mapped
   to a numeric weight (e.g. low=1, moderate=2, high=3, critical=4) —
   reuses the existing severity-band values already stored on
   `threat_scores`, no new classification needed.
3. **Recency weight:** more recent complaints count more — e.g. a simple
   half-life decay (a complaint from today counts fully, a complaint from
   29 days ago counts at a reduced fraction), rather than treating a
   30-day-old complaint identically to one from this morning.
4. **Priority Score formula (explicit, not hidden):**
   `priority_score = complaint_density * avg_severity_weight * recency_factor`,
   normalized to a 0–100 scale across all locations in the current result
   set (so scores are comparable to each other, not just absolute
   counts). Store/return the three input components alongside the final
   score so the UI (and a judge, if asked) can see exactly what drove a
   location's ranking — this is the same "never just declare, always
   explain" principle already used in the Threat Detection agent.
5. **Trend direction:** compare this window's complaint count to the
   equivalent prior window (e.g. this 30 days vs. the previous 30 days)
   — "rising" if up more than a small threshold (e.g. +15%), "falling" if
   down more than that threshold, "stable" otherwise. Simple, explicit,
   no smoothing model needed.

This entire computation can run as a single SQL aggregation query (or a
small set of them) — no new agent, no LLM call needed for this module,
since it's pure statistical aggregation over existing structured data.

---

## 7. Frontend Wiring Spec (functional only — no design polish)

Per §2: minimum needed to reach and test the backend.

- One new screen (or a new tab/section on the existing Officer Dashboard,
  whichever is faster to wire) listing locations ranked by priority score,
  each row showing: city name, priority score, trend arrow/label,
  dominant category, complaint count — reuse the existing table component
  from the Complaint Table if it fits directly.
- Clicking a row/city name navigates to the existing Complaint Table
  pre-filtered to that city (reuse the existing cross-module navigation
  pattern already built for Emerging Trends).
- Optional (only if time allows, not required): a basic map visualization
  showing relative intensity per city — if attempted, use a simple,
  low-effort library integration rather than a custom-built rendering.
- Basic loading indicator and basic error message — nothing beyond that
  for this pass.

---

## 8. Build Task Breakdown

| Task | Owner | Est. Hours |
|---|---|---|
| Confirm `reports.city` is a clean, groupable field (or normalize it if not) | Dev A | 0.5–2 (depends on what's found) |
| Priority score aggregation query + endpoint | Dev A | 2.5 |
| Trend time-series endpoint | Dev A | 1.5 |
| Ranked location list screen/tab, wired to real data | Dev B | 2 |
| Drill-through to Complaint Table filtered by city | Dev B | 0.5 |
| (Optional, only if time remains) basic map visualization | Dev B | 2–3 |
| End-to-end test with real seeded data | Both | 1 |

**Total (core, without optional map): ~8–9 hours.**

---

## 9. Testing Checklist

- [ ] Priority scores are actually different across cities, reflecting
      real differences in the underlying data (not all showing the same
      number)
- [ ] A city with more recent, more severe complaints ranks above a city
      with more total but older/lower-severity complaints — confirms the
      weighting is actually doing something, not just counting rows
- [ ] Trend direction correctly reflects a real increase/decrease when
      tested against a deliberately constructed before/after data change
- [ ] Clicking a city correctly pre-filters the real Complaint Table
- [ ] A city with genuinely zero complaints in the window doesn't break
      the ranking (either excluded cleanly or shown at the bottom with a
      zero score, not a crash or NaN)

---

*Ready to hand to Antigravity. Say the word and I'll generate the build
prompt next, same lean, shell-safe style as the previous two modules.*
