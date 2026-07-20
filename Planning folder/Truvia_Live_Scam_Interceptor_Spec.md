# Truvia — Module 5: Live Scam Interceptor
## Consolidated Build Spec (PRD + TRD + Schema + UI in one document)

**Why one document, not six:** Module 1 got the full six-document treatment because
it was the entire platform's foundation, built over 18 days. This module is a
single, well-scoped add-on being built with roughly a day of remaining time. A
full PRD/TRD/App-Flow/Design-Brief/Schema/Roadmap set here would cost more time
to write and read than the feature itself takes to build. This document has
everything Antigravity needs in one pass: what it is, why, the data model, the
API contract, the scoring logic, the UI spec, and a task breakdown.

---

## 1. What This Module Is

Every other Truvia module analyzes a scam **after the fact** — a citizen uploads
a finished screenshot, a completed transcript, a completed recording. Live Scam
Interceptor analyzes a scam **while it's still happening**. A citizen who is
mid-call or mid-chat with a suspected scammer opens a live session screen and,
turn by turn, types in what the other person just said. After every new turn,
the system re-evaluates the *entire conversation so far as an escalating
sequence* and returns an updated risk level — and once risk crosses a
threshold, it proactively surfaces specific guidance mid-conversation, not just
a number.

This directly answers the hackathon problem statement's own language: *"flags
active scam sessions... before financial transfer occurs."*

**What makes this a genuinely different capability from Fraud Shield (not a
reskin):** Fraud Shield is stateless — one submission in, one verdict out.
This module is stateful — it tracks a conversation's turns over time and its
risk trajectory (is it escalating turn-over-turn, plateauing, or de-escalating),
which is a different problem shape entirely (session/state management +
incremental re-scoring vs. one-shot classification).

**What it reuses from Fraud Shield (do not rebuild):** the underlying
rule-based + LLM threat-reasoning approach from Agent 2 (Threat Detection), the
scam-category taxonomy, the severity-band system, the existing design tokens/
component library, the existing auth system.

---

## 2. Build Priority — Backend First, Frontend Is Wiring Only

Per current team decision: **all remaining time goes to backend strength
first.** UI polish is explicitly deferred to a final pass across the whole
app, once every module (including this one) is functionally complete. For
this module specifically, that means:

- The backend must be fully real end-to-end: real turn-by-turn scoring,
  real cumulative/trajectory logic, real escalation, real PDF generation,
  real persistence — nothing mocked, nothing simplified "for now."
- The frontend work here is **feature-addition only, not design work**: a
  new entry-point button, a new session screen, and a new summary screen
  must *exist and function* so the backend is actually reachable and
  testable — but they should reuse existing components as directly as
  possible (the same Card, Button, Badge, chart components already in the
  codebase) with zero time spent on layout refinement, spacing, animation,
  or visual tuning. Functional-but-plain is the correct bar right now, not
  polished. A dedicated UI polish pass will cover this screen along with
  every other screen at the end — do not polish it early.
- Do not spend time on responsive/mobile refinement, motion/transition
  polish, or extra visual states beyond the minimum needed to verify data
  is flowing correctly (a basic loading indicator and a basic error
  message are enough — they don't need to match final design polish).

## 3. Scope — What's In, What's Explicitly Out (given the time budget)

**In scope (build this):**
- A new "Live Shield" screen where a citizen starts a session and adds turns
  one at a time (typed text only — not live audio transcription; that's a
  reuse of Agent 1's ASR path and is explicitly deferred, see below).
- Turn-by-turn re-scoring producing an escalating/de-escalating risk
  trajectory, not just a final score.
- A proactive intervention banner that appears once risk crosses a threshold,
  with specific, category-appropriate guidance (reusing Fraud Shield's
  existing "Recommended Actions" content where the category matches).
- Session persistence: a citizen can end a session and it's saved (reusing
  the same escalation-to-officer pathway Fraud Shield already has, so a live
  session can also become a real case).
- A simple end-of-session summary screen (reusing the existing Result screen
  layout/components as much as possible — this is explicitly a "wire, don't
  redesign" situation).

**Explicitly out of scope for this pass (defer if time runs out):**
- Live audio capture/transcription mid-call — typed-turn input only. Voice
  input would require reusing Agent 1's ASR per-turn, which adds real latency
  risk during a live conversation; not worth the risk in the time remaining.
- WhatsApp/IVR multi-channel delivery (PDF's "multi-channel" language) — web
  only, consistent with how Fraud Shield itself was scoped.
- Multi-language support beyond what Fraud Shield's LLM calls already handle
  incidentally.
- Any officer-side "watch a live session in real time" view — the officer
  only sees it after the fact, as a normal escalated case, identical to how
  Fraud Shield escalation already works.

---

## 4. User Flow

1. Citizen navigates to a new "Live Shield" entry point from the Fraud Shield
   home screen (a second card/button alongside the existing upload options —
   this is the one new piece of UI on an existing screen).
2. Citizen taps "Start Live Session." A new session is created
   (`live_sessions` row, status `active`).
3. A simple turn-input UI appears: a text box + "Add what they just said"
   button, and a running list of turns already added, each shown with a
   small per-turn risk indicator (color-coded dot, not a full badge — keep
   this lightweight since it updates frequently).
4. After each turn is added, the backend re-scores the full conversation
   so far and returns: overall trajectory score, severity band, whether this
   is an escalation from the previous turn, and (if threshold crossed) an
   intervention message.
5. If the intervention threshold is crossed, a prominent banner appears
   above the turn list: category-specific guidance (e.g., "They just claimed
   to be from CBI over video call — real police never conduct arrests over
   video call. Ask for a written order and hang up."), with a "End Session &
   Report" button directly in the banner.
6. Citizen can keep adding turns (session continues) or end the session at
   any point.
7. On end: a summary screen shows the full turn timeline with the risk
   trajectory as a simple line/step chart (reuse Recharts, already in the
   stack), the final severity assessment, and the same "Download Report" /
   "Report to Police" actions Fraud Shield already has — escalation creates
   a real `cases` row exactly like a normal Fraud Shield escalation does.

---

## 5. Data Model Additions (Postgres)

Two new tables, following the exact conventions already established in
Truvia_Backend_Schema.md (UUID PKs, `timestamptz`, soft deletes where
applicable, `CHECK` constraints instead of native enums).

### 4.1 `live_sessions`

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `user_id` | `uuid` | No | — | FK → `users.id`, `ON DELETE RESTRICT` |
| `status` | `text` | No | `'active'` | `CHECK (status IN ('active','ended','escalated'))` |
| `current_severity_band` | `text` | No | `'low'` | `CHECK (current_severity_band IN ('low','moderate','high','critical'))` — updated after every turn, denormalized for fast list queries |
| `current_score` | `smallint` | No | `0` | `CHECK (current_score BETWEEN 0 AND 100)` |
| `scam_category` | `text` | Yes | `NULL` | set once confidently classified, may start `NULL` |
| `intervention_shown_at` | `timestamptz` | Yes | `NULL` | first time the threshold was crossed |
| `linked_case_id` | `uuid` | Yes | `NULL` | FK → `cases.id`, `ON DELETE SET NULL` — set if escalated |
| `created_at` | `timestamptz` | No | `now()` | |
| `ended_at` | `timestamptz` | Yes | `NULL` | |

**Indexes:** `idx_live_sessions_user_id`; `idx_live_sessions_status` (partial
`WHERE status = 'active'`, for "resume active session" lookups).

### 4.2 `live_session_turns`

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `session_id` | `uuid` | No | — | FK → `live_sessions.id`, `ON DELETE CASCADE` (a turn has no meaning without its session — intentional exception, same rationale as `sessions`/`knowledge_base_chunks` elsewhere in the schema) |
| `turn_index` | `integer` | No | — | ordinal position in the conversation |
| `raw_text` | `text` | No | — | what the citizen typed for this turn |
| `turn_score` | `smallint` | No | — | this turn's individual contribution/signal, `CHECK (turn_score BETWEEN 0 AND 100)` |
| `cumulative_score` | `smallint` | No | — | the running trajectory score *as of* this turn — this is what gets charted |
| `flagged_phrases_json` | `jsonb` | Yes | `NULL` | same explainability shape as `threat_scores.reasoning_json`, reused |
| `created_at` | `timestamptz` | No | `now()` | |

**Constraints:** `UNIQUE (session_id, turn_index)`.
**Indexes:** `idx_live_session_turns_session_id` (btree, the query behind
rendering the full turn timeline).

**No new Neo4j or vector-store schema needed.** This module only needs
Postgres — entity/graph correlation is deliberately deferred; an escalated
live session becomes a normal case, which already flows into the existing
graph pipeline once escalated (reuse, don't duplicate).

---

## 6. API Contract

New endpoints, following the existing `/api/v1/*` convention and existing
auth middleware (citizen role only, except escalation which reuses the exact
existing escalation logic):

| Method & Path | Purpose | Request | Response |
|---|---|---|---|
| `POST /api/v1/live-sessions` | Start a new session | `{}` | `{session_id, status: "active"}` |
| `POST /api/v1/live-sessions/{id}/turns` | Add a turn, get updated assessment | `{raw_text: string}` | `{turn_index, turn_score, cumulative_score, severity_band, scam_category, is_escalating: bool, intervention: {shown: bool, message: string, category: string} | null, flagged_phrases: [...]}` |
| `GET /api/v1/live-sessions/{id}` | Get full session + turn history | — | `{session, turns: [...]}` — used to render the summary screen |
| `POST /api/v1/live-sessions/{id}/end` | End a session | `{}` | `{status: "ended"}` |
| `POST /api/v1/live-sessions/{id}/escalate` | Escalate to a real case | `{}` | `{case_id}` — **reuse the existing `POST /reports/{id}/escalate` logic/pattern exactly**, just pointed at a session instead of a report |
| `GET /api/v1/live-sessions/{id}/report` | Download session summary as PDF | — | file stream — **reuse the existing report-generation code path**, don't build a second PDF renderer |

---

## 7. Scoring Logic — How Turn-by-Turn Escalation Actually Works

This is the one genuinely new piece of logic (everything else is reuse):

1. **Per-turn scoring:** each new turn's raw text is run through the *same*
   rule-based red-flag extractor already built for Agent 2 (urgency language,
   OTP/UPI requests, authority impersonation, threat-of-arrest language,
   etc.) — this reuses existing code, just called per-turn instead of once
   on a full document.
2. **Cumulative/trajectory scoring:** the cumulative score is not simply the
   average or max of individual turn scores — it should weight *recent* turns
   more heavily and explicitly boost the score when consecutive turns show
   escalating severity (e.g., turn 1 = generic urgency, turn 2 = impersonation
   claim, turn 3 = payment request → this specific escalating pattern across
   turns is itself a strong signal, stronger than any single turn alone).
   A simple, explainable formula is preferred over a black box: e.g.
   `cumulative_score = 0.4 * previous_cumulative_score + 0.6 * turn_score`,
   with an additional flat bonus (e.g. +15, capped at 100) applied when three
   consecutive turns each individually exceed the "moderate" threshold —
   this rewards sustained escalation without needing a trained sequence
   model, which there is no time to build.
3. **LLM pass (optional per turn, cost-aware):** rather than calling the LLM
   on every single turn (latency + cost), only invoke the full LLM
   structured-reasoning pass (reusing Agent 2's existing LLM call) when the
   rule-based cumulative score crosses into "moderate" or above — below that,
   rule-based scoring alone is sufficient and keeps the live interaction fast.
4. **Intervention threshold:** fire the intervention banner the first time
   `cumulative_score` crosses into "high" (not "critical" — earlier is
   better for a live-prevention use case, this is a deliberate product
   choice, not a bug) — and only fire it once per session per severity-band
   crossing, not on every subsequent turn, to avoid banner spam.

---

## 8. Frontend Wiring Spec (functional only — no design polish)

Per §2: this is the minimum frontend needed to reach and exercise the
backend, nothing more. Do not spend build time on layout, spacing, motion,
or visual refinement here — that happens in the final cross-app polish
pass, not now.

- **Three screens/elements needed, functional only:**
  1. One new entry-point button on the existing Fraud Shield home screen
     ("Start a Live Session") — reuse the existing Button component as-is,
     any placement/variant that doesn't require new layout work is fine.
  2. One new screen for the active session: a turn list, a text input +
     submit control, and the intervention banner. Build this with
     whatever existing Card/Input/Button components get it working
     fastest — do not design a new layout, just stack existing components
     in a working order.
  3. One summary screen on session end — reuse the existing Result screen
     component/layout wholesale if at all possible (pass it session data
     instead of report data) rather than building a new screen from
     scratch.
- **Component reuse over new patterns, but only insofar as it's faster:**
  if the existing warning-banner component can be reused directly for the
  intervention message, use it. If the existing severity-badge component
  can be reused directly for the per-turn risk indicator, use it. The
  goal is minimum frontend effort, not visual consistency for its own
  sake at this stage — consistency gets enforced in the final polish pass.
- **Minimum viable states only:** a basic loading indicator while a turn
  is scoring, and a basic error message if a request fails — enough to
  confirm the backend is actually responding correctly during testing.
  Do not build out full empty-state copy, animation, or responsive
  behavior for this screen right now.

---

## 9. Build Task Breakdown (roughly one day, 2 developers)

| Task | Owner | Est. Hours |
|---|---|---|
| `live_sessions` / `live_session_turns` migration | Dev A | 1 |
| Turn-scoring logic (reusing Agent 2's rule-based extractor + cumulative formula) | Dev A | 3 |
| Conditional LLM-call-on-threshold logic | Dev A | 1 |
| All 6 API endpoints | Dev A | 2.5 |
| Escalation + PDF report reuse-wiring (point existing logic at a session) | Dev A | 1 |
| New entry-point button on Fraud Shield home | Dev B | 0.5 |
| Active session screen (turn list, input, per-turn risk dot) | Dev B | 3 |
| Intervention banner component (reusing existing warning-banner styling) | Dev B | 1 |
| Session summary screen (reusing Result screen layout + trajectory chart) | Dev B | 2.5 |
| End-to-end test: a scripted escalating fake conversation triggers the banner at the right turn, escalates to a real case | Both | 1 |

**Total: ~16–17 hours across both developers — fits within roughly one day
if run in parallel, matching your stated timeline.**

---

## 10. Testing Checklist

- [ ] A conversation with early payment/OTP requests scores high quickly (not
      waiting for many turns)
- [ ] A conversation that starts alarming but the "caller" backs off shows
      the trajectory score plateau/decline, not stay artificially high
- [ ] Intervention banner fires exactly once per severity crossing, not on
      every turn after
- [ ] Ending a session with zero turns doesn't crash the summary screen
      (genuine empty state)
- [ ] Escalating a live session creates a real `cases` row identical in
      shape to a normal Fraud Shield escalation, correctly linked via
      `live_sessions.linked_case_id`
- [ ] Downloaded PDF report reflects the actual turn history and final
      assessment, not a placeholder

---

*This spec is intentionally scoped to be buildable in the time you have.
Ready to hand to Antigravity as context — say the word and I'll generate the
actual build prompt next, in the same lean, shell-safe style as the previous
module prompts.*
