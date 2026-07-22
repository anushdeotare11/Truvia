# Truvia — The Simple, Plain-Language Walkthrough

This is a companion guide to `PROJECT_UNDERSTANDING.md`, written for people who
have never touched code. If you can use a phone and a website, you can follow
this. It walks through the app one screen at a time and, for each screen, says
what you see, what each button does, and why a real person would use it.

A quick promise about honesty: where a button is on the screen but does not
actually do anything yet, this guide says so plainly. And where the app is
currently using a "backup brain" instead of its smartest option, it says that
too (more on that at the end).

---

## 1. Overview — What This App Is, In One Paragraph

Truvia is a fraud-fighting website. Everyday people (called **citizens** here)
can send in a suspicious message, screenshot, or voice recording and instantly
get a clear answer: "Is this a scam, how dangerous is it, and what should I do?"
Behind the scenes, the app also quietly pulls out the useful details from each
report — like phone numbers and payment IDs — and remembers them. When the same
phone number or payment ID keeps showing up across many different people's
reports, the app connects those reports together and shows the police that a
whole **gang** (the app calls it a "fraud ring") is behind them. So there are
really three kinds of people who use Truvia: **citizens** who want to protect
themselves, **police officers** who investigate fraud, and **admins** who keep
the system running. One sentence to remember it by: *Truvia protects the next
victim by learning from the last one.*

---

## 2. The Citizen Side

This is the part ordinary members of the public use. When a citizen logs in,
the app takes them straight to the **Fraud Shield** screen.

### 2.1 The Landing Page (the public "welcome" page, before you log in)

This is the first page anyone sees when they visit the website without logging
in. It is a marketing/welcome page — like the front cover of a brochure.

What's on it:
- A big headline: *"See the fraud before it sees you."*
- A **"Get started"** button (top right) and two large buttons, **"Launch
  Citizen Shield"** and **"Agency Access."** All three of these simply take you
  to the login/sign-up page. That's their only job.
- A row of menu words at the top — **Modules**, **Capabilities**, **Protocol.**
  Clicking one just scrolls you down the same page to that section. They don't
  open anything new.
- A fancy animated "live console" panel with numbers like *"Active Signals
  1,284"* and *"Rings Detected 37,"* plus a little bar chart. **Important honesty
  note:** these numbers are decorative — they are fixed display numbers to make
  the page look alive, not real live data from the system. The same is true for
  the big statistics band lower down ("150K+ reports analyzed," "0.8s average
  speed," "99.9%"). Think of them like the sample photos on a product box.
- Three cards describing the app's three parts (for citizens, for police, for
  analysts), then a list of feature cards, then a simple "how it works in 3
  steps" strip. These are all just descriptive text.
- A closing **"Enroll in Citizen Shield"** / **"Request Agency Demo"** — again,
  both just go to the login page.
- A footer with the words **PRIVACY** and **TERMS.** These look like links but
  they don't currently go anywhere — they're just styled text.
- There's also a thin bar at the very top saying the app is live for the
  hackathon, with an **X** to close that bar (that X works).

Why a person uses it: to understand what the app is and to click through to sign
up or log in.

### 2.2 The Login / Sign-Up Page

This is where everyone enters the app. It's a single card in the middle of the
screen.

What's on it and what each part does:
- **Two tabs at the top: "Login" and "Sign Up."** Clicking switches between
  logging into an existing account and creating a new one.
- **A "Citizen / Agency" toggle.** "Citizen" is for the general public.
  "Agency" is for police officers and admins. Regular people leave it on
  "Citizen."
- **Email and Password boxes.** You type your details here.
- On Sign Up as a citizen, you also get a **Full Name** box and an optional
  **Phone** box.
- **The main button** says "Secure Login" or "Create Account" depending on the
  tab. Clicking it logs you in (or makes your account and then logs you in) and
  sends you to your home screen.
- **Important rule that's built in:** if someone picks "Agency" and tries to
  sign up, the app politely refuses and says agency accounts are created by an
  administrator, not self-signup. This is intentional — only real staff get
  officer/admin accounts.
- **Two "Demo Access" buttons at the bottom: "Citizen Demo" and "Officer
  Demo."** Clicking one auto-fills the email and password for a ready-made test
  account, so someone showing off the app doesn't have to type credentials. You
  still press the login button after.
- A **"Back to Home"** link returns to the landing page.
- The little "TLS 1.3 / AES-256 Encryption Active" text at the bottom is just a
  reassurance label; it's not a button.

A simple example: a citizen clicks "Sign Up," keeps the toggle on "Citizen,"
types their name, email, and a password, presses "Create Account," and a moment
later they land on the Fraud Shield screen, already logged in.

### 2.3 Fraud Shield — the Citizen's Home Screen (checking one message)

This is the heart of the citizen experience. It's where you submit something
suspicious and get a verdict. The screen is split into a left side (where you
put in evidence) and a right side (where the answer appears).

**Left side — "Evidence Capture":**
- **Three tabs: "text," "screenshot," and "audio."** You pick how you want to
  submit. "text" lets you paste a message. "screenshot" lets you upload a
  picture. "audio" lets you upload a voice recording of a suspicious call.
- If you pick **text**, you get a large box to paste the suspicious SMS or
  WhatsApp message into.
- If you pick **screenshot** or **audio**, you get an upload area — click it to
  browse and pick a file from your device.
- **"RUN AI ANALYSIS" button.** This is the big action button. Pressing it sends
  your evidence off to be analyzed. If you try to run it with almost nothing
  typed (fewer than 10 characters) or with no file chosen, it politely asks you
  to add more first.
- A small **"Data Privacy Protocol"** note reassures you the evidence is only
  used for this analysis.
- There's also a **"Start a Live Session"** link near the top that jumps you to
  the Live Scam Interceptor screen (covered below).

**The live processing screen (what you see while it's thinking):**
- After you press "Run AI Analysis," a row of little icons appears showing the
  steps the app is going through, one lighting up at a time: **Submitting
  Report → Extracting Text → Evaluating Threats → Extracting Entities →
  Indexing Graph → Analysis Complete.** A short label underneath tells you which
  step is happening right now. This is just to reassure you it's working; you
  don't click anything here.

**Right side — the Result (the verdict):**
- Before you submit anything, this side just says "Awaiting Evidence."
- After analysis, it shows:
  - A **round risk dial** with a score from 0 to 100 and a word like **LOW,
    MODERATE, HIGH,** or **CRITICAL.**
  - A **Confidence** percentage (how sure the app is) and a **Category** (what
    type of scam it looks like, e.g. "Digital Arrest Scam").
  - **"Detected Red Flags"** — a list of the specific warning signs the app
    found (like "threats of arrest" or "asking for a payment").
  - **"Recommended Response"** — a list of what you should actually do (like
    "don't share your OTP," "hang up and call the official number").
  - If the app couldn't read your upload clearly, a gentle note appears saying
    the text may be incomplete and you might want to re-submit.
- **Three action buttons at the bottom:**
  - **"Report to Cyber Cell"** — sends your report to the police queue. Before
    it does, a pop-up asks you to confirm ("this will submit your report and
    evidence to the police complaint queue — continue?"). After you confirm, it
    shows you a case reference number. This is how a citizen escalates something
    serious to real investigators.
  - **"Export Report"** — downloads a PDF copy of the verdict to your device, so
    you have a record.
  - **"Mark as Reviewed"** — closes the report out on your side (for something
    you've read and dealt with). You can't do this if it's already been sent to
    the police.

**Bottom of the screen — two more panels:**
- **"Vigil AI Assistant"** — a chat box. You can type any question about scams
  (like "someone says they're from the CBI and I'll be arrested — what do I
  do?") and it answers using official government/bank guidance, and shows you
  which official source it's quoting. You press Enter or the send arrow to ask.
- **"Recent Scans"** — a small table of your past reports. Each row shows the
  date, type, score, and status. Clicking a row re-opens that report's verdict
  on the right.

A simple example, step by step: A citizen gets a scary WhatsApp message claiming
to be from the police. They open Fraud Shield, leave it on the "text" tab, paste
the message, and press **"Run AI Analysis."** The little step icons light up one
by one for a few seconds. Then the right side fills in: the dial swings up to
**85 — HIGH**, the category says **"Digital Arrest Scam,"** the red flags list
"impersonating law enforcement" and "threats of arrest," and the recommended
actions say "government officials never arrest you over a video call — hang up
and call 1930." The citizen feels reassured, presses **"Report to Cyber Cell,"**
confirms the pop-up, and gets a case number. Done.

### 2.4 Live Scam Interceptor — "Live Shield" (help *during* a scam call)

This screen is for when a scam is happening *right now* — you're on a call or
chat with a suspected scammer and want help in the moment, before you lose any
money. Instead of submitting one finished message, you type in what the other
person says, line by line, as they say it, and the app keeps re-judging how
dangerous the whole conversation is getting.

It has three stages:

**Stage 1 — Start (idle):**
- You see a short explanation and a **"START LIVE SESSION"** button. Press it to
  begin.

**Stage 2 — Active (during the "call"):**
- A text box where you type **"what they just said"** and press **"Add what they
  just said."** Each thing you add becomes a line in a list.
- Each line gets its own little danger label, and a big **risk dial** on the
  right climbs or falls as the conversation develops. So you can literally watch
  the danger level rise turn by turn.
- If the danger crosses into "high," a bright **warning banner** pops up with
  specific advice for that exact scam type (for example, "no genuine refund ever
  needs your UPI PIN — stop now"). This is the whole point: a warning *in the
  moment*, before money moves.
- Two buttons: **"End Session"** (stop and see a summary) and, inside the
  warning banner, **"End Session & Report"** (stop and send it to police).

**Stage 3 — Summary (after you end):**
- A **line graph** showing how the risk climbed across the conversation, with a
  dashed line marking the "high risk" level.
- A list of all the lines you entered, and a final verdict dial and category.
- Three buttons: **"Report to Cyber Cell"** (send to police, with a confirm
  pop-up), **"Download Report"** (save a PDF), and **"Start Another Session."**

Honest note: you type in what the scammer says — the app is not secretly
listening to your phone call. It reacts to what you type.

A simple example: Someone calls claiming to be from your bank. You open Live
Shield, press start, and type "I'm calling from your bank's fraud department."
Low risk. They say "your account is compromised" — you type that, risk ticks up.
They say "share the OTP I just sent to secure it" — you type that, and the dial
jumps into the red and a banner appears: *"Banks never ask for your OTP — do not
share it, hang up."* You end the session and report it.

### 2.5 The Alerts Center (public safety warnings)

Citizens (and officers) can open the **Alerts Center** to see current scam
warnings.

What's on it for a citizen:
- A live feed titled **"Public Safety Advisories"** — a scrolling list of
  current fraud warnings, each with a severity color, a title, a short
  description, and a date. These are read-only notices to keep the public
  informed. There are no buttons to press; you just read them.
- If the feed is empty, it shows a friendly "no trending alerts right now"
  message.

(Officers see extra things on this same screen — described in the officer
section.)

Why a citizen uses it: to stay aware of scams doing the rounds right now.

### 2.6 Settings (citizen view)

Every logged-in person has a **Settings** screen with tabs across the top.
Citizens see three of them:
- **User Profile** — shows your name, role, email, account status, and join
  date. These are display-only; a note explains your profile is managed by an
  administrator, so you can't edit them here.
- **Security** — an informational panel telling you your session is encrypted.
  The "ACTIVE" badge is just a status label, not a button.
- **Preferences** — three on/off switches for what notifications you'd like
  (security alerts, weekly summaries, public advisories). **Honest note:** these
  switches remember your choice only inside your own browser — they're a
  personal preference saved locally, not something sent to a server that
  actually changes what emails you get.

---

## 3. The Officer Side

Officers are the police/investigators. When an officer logs in, they land on the
**Dashboard.** They also get a menu down the left side (the sidebar) with links
to Dashboard, Investigations, My Cases, Threat Intel, Geo Priority, Alerts
Center, Reports Feed, and Settings.

A note on the top bar and sidebar (seen on every officer/admin screen):
- The **left sidebar** shows the app logo, your name and role, the menu links,
  and a big **"New Case"** button at the bottom (it opens the Investigations
  list). The menu link for the screen you're on is highlighted.
- The **top bar** has a search box and a bell icon. **Honest note:** that top-bar
  search box and the notification bell are decorative right now — they're on the
  screen but not wired to do anything. (The real search boxes are the ones
  *inside* each screen, like on the Reports and Investigations pages.) The top
  bar also has your name with a dropdown that contains a working **"Sign Out"**
  button (it asks you to confirm before logging out).

### 3.1 The Officer Dashboard (the "command center")

This is a big overview screen full of live numbers and charts. It answers "what's
happening across the whole system right now?"

What's on it:
- **Four big number cards** at the top: **Total Complaints, Active
  Investigations, Critical Threats,** and **High-Risk Entities.** These count up
  with a little animation and show real totals from the system.
- **A "Complaint Trend" chart** — a line/area graph of how many complaints came
  in over recent days.
- **A "Scam Vector Distribution" panel** — bars showing which scam types are most
  common lately, as percentages.
- **A "Recent Incidents" table** — the latest reports, each with an ID, a short
  title, a threat level, a status, and a time. A **"View All"** link takes you to
  the full Reports Feed.
- **A "Neural Analysis" daily brief** — a short written summary of the biggest
  emerging trend (for example, "a 40% surge in KYC scams over the last
  fortnight").
- **A "Priority Alerts" panel** — a live list of surging scam types. Each one is
  **clickable**: clicking jumps you to the Reports Feed already filtered to that
  scam category.
- **Three analytics panels at the bottom:** a **City Distribution** list (which
  cities have the most complaints), a **Threat Score Distribution** ring (the
  average danger score), and a **Threat Timeline** (a running list of recent
  scored reports).
- **A "VIEW INVESTIGATIONS" button** near the title jumps to the case list.

Why an officer uses it: to get the big picture at a glance — how much fraud is
coming in, what kinds, where, and what's spiking — before diving into individual
cases.

### 3.2 The Reports Feed (the full complaint list)

Reached from the sidebar ("Reports Feed") or the dashboard's "View All." This is
a searchable, filterable table of every report in the system.

What's on it:
- **A search box** to find reports by their message text or keywords.
- **A "Type" dropdown** to show only text, screenshot, or audio reports.
- **A row of status buttons** (All Status, submitted, processing, scored,
  escalated, dismissed, failed) to filter by where the report is in its life.
- If you arrived here by clicking a category or a city elsewhere, a little
  removable **filter chip** shows that filter, with an **X** to clear it.
- **The table itself:** each row shows an ID, the incident title, the type (with
  an icon), the status, the date, the threat level (a colored dot), and an
  **Action** button — a small **PDF icon** that downloads that report as a PDF.
- **"Export CSV" button** (top right) — downloads the *currently filtered* list
  as a spreadsheet file. So if you filtered to "KYC scams in Mumbai," the
  spreadsheet contains exactly those.
- **"Sync Data" button** — refreshes the list.
- **Previous/Next arrows** at the bottom to page through if there are many
  reports.

A simple example: An officer wants every high-danger report from one city. They
click into the Reports Feed, and (having arrived from the map with a city filter
already applied) they see only that city's reports, press **"Export CSV,"** and
open the downloaded spreadsheet in Excel to work through them.

### 3.3 Investigations — the Case List

Reached from the sidebar ("Investigations"). A **case** is an investigation file
that groups related reports together.

What's on it:
- **A search box** to find a case by its number or summary text.
- **A grid of case cards.** Each card shows the case number, its type (single
  report or a whole ring), a priority tag, a short AI-written summary, its
  status, and when it was opened. Clicking a card opens the full case.

Why an officer uses it: to browse and pick which investigation to work on.

### 3.4 The Investigation View (one case, in detail) — with its sections

This is where an officer actually works a case. It's a busy screen with three
columns.

**Left column:**
- **"Case Assignment"** box: shows Priority, Status, and who it's assigned to,
  plus an **"Assign to Me"** button. Pressing it makes the officer the owner of
  the case (and it records who did it and when). If it's already yours, the
  button reads "Assigned to You."
- **"Case Metadata"** box: quick counts (how many reports, entities, and activity
  events) and the AI summary of the case.

**Center column:**
- **"Evidence & Activity Timeline"** — a vertical timeline mixing together the
  reports that were linked and the actions officers took, newest first.
- **"Linked Evidence"** — the actual reports attached to this case, each with a
  short transcript preview.
- **"Correlated Complaints"** — *other* reports that aren't in this case yet but
  share a phone number or payment ID with it. Each shows how many details it
  shares. This is the "connect the dots" feature: it surfaces likely-related
  victims the officer hasn't linked yet.

**Right column:**
- **"Extracted Entities"** — the list of phone numbers, payment IDs, websites,
  etc. pulled from the case's reports. Each has a danger score. Clicking one
  opens that entity's full profile in the Threat Intelligence section.
- **"View in Threat Intelligence Engine"** button — jumps to the network graph,
  centered on the highest-risk detail in this case.
- **"Officer Activity Log"** — a record of actions taken on this case.

**Top of the screen:**
- **"Intelligence Package"** button — compiles everything about the case into a
  formal, court-style PDF dossier and downloads it. This is the officer's
  one-click "prepare the evidence file" button.

A simple example: An officer opens a case about a fake-loan scam. They read the
AI summary, click **"Assign to Me,"** notice in "Correlated Complaints" that
three other victims reported the same payment ID, click one of those to review
it, then press **"Intelligence Package"** to download a tidy PDF dossier they can
attach to the official case file.

### 3.5 My Cases (an officer's personal workload)

Reached from the sidebar ("My Cases"). Shows only the cases assigned to *you.*

What's on it:
- **A "Table / Kanban" toggle** to switch how you view your cases.
- **Table view:** a straightforward list with case number, type, priority,
  status, summary, and open date.
- **Kanban view:** three columns — **New, In Progress, Resolved** — with your
  cases sorted into them as cards. (Note: the cards are clickable to open a case,
  but you don't drag them between columns; they move automatically based on each
  case's status.)
- If you have no cases, it shows a friendly empty message with a **"Browse all
  complaints"** button that takes you to the Investigations list.

Why an officer uses it: to focus on just their own assigned work.

### 3.6 Geo Priority — the "where should we focus?" screen

Reached from the sidebar ("Geo Priority"). This ranks cities by how much recent,
serious fraud is happening in them, so police know where to put resources.

What's on it:
- **A "Window" dropdown** (last 7, 14, 30, 60, or 90 days) to choose the time
  span.
- **A "Category" box** to focus on one scam type, or leave blank for all.
- **A "Table / Map" toggle.**
- **Table view:** cities ranked, each row showing rank, city name, a **Priority
  Score** with a little bar, a **trend arrow** (rising / falling / stable), the
  most common scam type there, and the complaint count. Clicking a city row jumps
  to the Reports Feed filtered to that city.
- **Map view:** the same information shown as dots on a map of the cities. Clicking
  a city does the same drill-through.

Why an officer uses it: to decide where patrols and investigators are most
needed right now, and to jump straight into the complaints from a hotspot city.

A simple example: An officer sets the window to "Last 30 days," sees that one
city has the highest Priority Score with a red "rising" arrow, clicks it, and is
taken to that city's list of complaints to start assigning them.

### 3.7 The Threat Intelligence Engine (the network map) — officer view

This is the most visual officer feature. Reached from the sidebar ("Threat
Intel"). It shows fraud as a **web of connected dots** — each dot is a detail
(a phone number, payment ID, website, etc.), and lines connect details that
appeared together in reports. Clusters of connected dots are suspected gangs.

**Graph Home (the main map):**
- A big dark canvas full of colored dots and connecting lines.
- **A floating stats pill** at the top showing counts of Nodes (dots), Clusters
  (groups), and Edges (lines).
- **A "Controls" panel** (top-left) with:
  - **A search box** to find a specific entity (phone/UPI/etc.). Results drop
    down; clicking one opens its info panel.
  - **A "View Fraud Rings" button** that goes to the ring list (below).
  - **A color legend** explaining what the dot colors mean (high-risk, hub,
    individual, phone).
- **Two small round buttons** (bottom-left): one recenters the view, one
  refreshes the graph.
- **Clicking any dot** opens a **side panel** on the right with that entity's
  danger level, how many connections and reports it has, whether it's part of a
  ring, a timeline of the complaints it appeared in, and a **"View Full Profile"**
  button.

**Fraud Rings list** (from "View Fraud Rings"):
- A grid of cards, each a detected gang, showing its risk level, its main scam
  type, and counts of members, complaints, and risk. **Sort buttons** (Risk,
  Size, Recency) reorder them. Clicking a card opens the ring detail.

**Ring Detail (one gang):**
- Top tiles: member count, complaints, aggregate risk, last activity.
- A **network graph** of just that gang's members.
- **"Members / Entities"** list and **"Linked Complaints"** list (clicking a
  complaint opens that case).
- **Two action buttons:** **"Export Intelligence Package"** (creates a formal,
  tamper-evident PDF evidence bundle for the whole ring and gives it a version
  number) and **"Export Evidence Bundle"** (downloads the raw connection data as
  a file).

**Entity Explorer (one detail, e.g. one phone number):**
- The entity's identity, danger dial, and counts.
- A **"Risk Network"** graph with **Depth 1/2/3 buttons** to show connections one,
  two, or three steps out.
- **"Contributing Factors"** (why it's risky), **"Linked Reports/Complaints,"**
  **"Linked Identifiers"** (its direct connections, clickable), and **"Risk
  History."**
- An **"Export Intelligence Package"** button — but this one only works if the
  entity is part of a detected ring; otherwise it's greyed out with a note
  explaining why.

Why an officer uses it: to see the bigger criminal network behind a single clue,
identify the whole gang, and generate court-ready evidence about them.

A simple example: From a case, an officer clicks a suspicious payment ID. The
Entity Explorer opens showing it's connected to 8 other details and is "In fraud
ring." They open the ring, see it links 22 details across 14 complaints, and
press **"Export Intelligence Package"** to produce a versioned PDF they can hand
to prosecutors.

### 3.8 Alerts Center (officer extras)

On the same Alerts screen citizens use, officers additionally see:
- **A "Predictive Threat Feed"** — surging scam types with how fast they're
  growing.
- **A "High-Risk Blocklist"** — the most dangerous phone numbers/payment IDs
  right now, each with a danger score, plus a count of how many fraud rings have
  been detected.

---

## 4. The Admin Side

Admins keep the platform healthy. When an admin logs in, they land on **User
Management.** Admins can also visit the officer screens (when they do, a small
"Admin View" badge appears in the top bar to remind them they're looking at an
officer area).

### 4.1 User Management (the master list of accounts)

What's on it:
- **A search box** and **Role / Status dropdowns** to filter the list of accounts
  (citizens, officers, admins; active, suspended, pending).
- **A table** of everyone, showing name, email, role, status, and join date.
  Clicking a row opens that person's detail page.
- **A small action button on each row** to **suspend** (block) or **reactivate**
  an account. Suspending asks for confirmation first.
- **An "Invite Officer/Admin" button** — opens a small pop-up form to create a
  new officer or admin account. Because the app has no email service connected,
  it instead gives you a **one-time setup link** to copy and share with the new
  person directly. (Honest, practical detail: no email actually gets sent — you
  hand over the link yourself.)
- **Previous/Next** paging at the bottom.

A simple example: A new officer joins the unit. The admin clicks **"Invite
Officer/Admin,"** enters the officer's name and email, picks "Officer," and gets
a setup link, which they paste into a message to the officer so they can set
their password.

### 4.2 User Detail (managing one person)

Opened by clicking a row in User Management.

What's on it:
- **An editable profile** — Name, Phone, and Role can be changed; Email is
  read-only. A **"Save changes"** button applies edits.
- **A "Suspend account" / "Reactivate account" button** (suspending confirms
  first).
- **A "Reset password" button** — generates a one-time reset link to share with
  the person (again, no email is sent; you copy the link).
- **An "Activity" panel** — shows the person's status, how many cases they're
  assigned, and their recent login sessions.

### 4.3 Knowledge Base (the AI assistant's library)

This is where admins manage the official documents that the citizen chat
assistant ("Vigil") quotes from. Think of it as the assistant's reference
bookshelf of real RBI / CERT-In / MHA / NPCI fraud guidance.

What's on it:
- **Source and Status dropdowns** to filter the document list.
- **A table** of documents, each with its source (like "RBI"), title, date added,
  and status (indexed = ready to use, processing, or failed). Clicking a row
  opens the document.
- **Per-row buttons:** a **refresh icon** to "re-index" (re-file) a document, and
  a **trash icon** to remove it (with confirmation, warning that the assistant
  will stop quoting it).
- **An "Add Document" button** — opens a form to paste in a new piece of guidance
  (source, title, content, optional web link). Saving it files the document so
  the assistant can start quoting it. This "filing" is the same process that
  makes chat answers accurate.

### 4.4 Document Detail (one reference document)

Opened by clicking a document row.

What's on it:
- The document's title, source, and status.
- **Count tiles:** how many pieces it was split into ("Chunks"), how many times
  it's been quoted in chat, its version, and when it was added.
- **The full raw text** of the document.
- **"Re-index" and "Remove" buttons** at the top (same as in the list).

Why an admin uses it: to check exactly what guidance the assistant is drawing
from, and to refresh or remove it.

### 4.5 System Health (is everything running?)

A live status console for the whole platform.

What's on it:
- **Agent cards** — one card per "worker" in the system (the text-reader, the
  scam-scorer, the chat assistant, etc.), each showing whether it's healthy,
  which brain it's currently using, how fast it's responding, how many times it
  ran in the last hour, and how many errors it hit. **This is the honest window
  into whether the app is using its smart AI brain or its backup — see Section 7
  of `PROJECT_UNDERSTANDING.md`.**
- **A "Task Queue" panel** — how much work is waiting or in progress.
- **A "Recent Failed Tasks" panel** — anything that went wrong, each with a
  **"Retry"** button to run it again.
- **An "Auto-refresh (10s)" checkbox** and a manual refresh button.

A simple example: An admin notices citizen results feel slow. They open System
Health, glance at the agent cards to see response times and error counts, and
check the queue and failed-tasks list to spot any pile-up, retrying anything
that failed.

---

## 5. The "Behind the Scenes" Explanation, In Plain Words

Here's what actually happens after a citizen presses **"Run AI Analysis"** — told
as a short story, not a diagram.

First, the app **reads the words out of your evidence, like a person reading it
aloud.** If you uploaded a screenshot, it looks at the picture and types out the
text it can see. If you uploaded a voice recording, it listens and writes down
what was said. If you pasted text, it just uses that. If it can't make out much
(a blurry photo, a muffled recording), it makes a note that it's unsure rather
than pretending.

Next, it **checks that text against a list of known scam warning signs, a bit
like a spell-checker but for scams.** It looks for tell-tale phrases — threats of
arrest, demands for an OTP or PIN, "your account will be blocked," links to click,
promises of prize money — and adds up a danger score out of 100. It also decides
which *kind* of scam it most looks like.

Then, when the smart-AI brain is switched on, it **double-checks with an AI that
understands context, like asking a very well-read friend what they think** — the
friend explains, in plain words, why it's risky and what you should do. (Right
now, that "friend" is unavailable because of an expired access key, so the app
falls back to the reliable warning-sign checklist above. The final answer is
still real and useful — see Section 6.)

After scoring, the app **pulls out the useful details from the message** — phone
numbers, payment IDs (UPI), email addresses, websites, bank account numbers. It
tidies each one into a standard form (for example, a phone number always trimmed
to its last 10 digits) so the same number always looks the same to the app.

Now the clever part: **the app remembers if it has seen these same details
before, and connects the dots between different people's reports — exactly like a
detective noticing the same name turn up in different case files.** If your scam
used a payment ID that showed up in forty other victims' reports, the app already
knows they're probably all the same operation. It keeps a growing web of these
connections.

Finally, if your report is dangerous enough, the app **automatically raises a flag
for the police,** and it quietly files your report's details into that big web so
future reports can be matched against it. Separately, every so often the app runs
a "find the clusters" pass over the whole web — it groups tightly-connected
details into suspected **gangs (fraud rings)** and works out how big each one is,
what it mostly does, and how dangerous it is. That's what powers the officers'
network map and their court-ready evidence packages.

So one message from one worried citizen does two jobs at once: it gets that
person a fast, clear answer, and it makes the whole system a little smarter for
everyone who reports next.

---

## 6. What Happens When Something Goes Wrong (In Plain Words)

The app is built to stay useful and honest even when things aren't perfect.

**If your photo is blurry or hard to read:** the app reads whatever it can and
then adds a gentle note on the result saying "the extracted text may be
incomplete — consider re-submitting as clearer text." It still gives you its best
verdict; it just tells you it wasn't fully sure. If a picture or recording has no
readable content at all, instead of inventing an answer it honestly says it
couldn't get enough to analyze and asks you to try again or paste the text — it
will not make up a fake result.

**If the internet or one of the app's helpers is temporarily down:** the app
leans on backups instead of breaking. If its main memory bank is unreachable, it
uses a local backup store. If the special "network map" database is offline, the
graph still works because the app can rebuild the connections from its main
records. If the smart-AI brain can't be reached, it falls back to the reliable
warning-sign checklist. In short, a piece going down turns off a nice-to-have,
not the whole app.

**If there isn't enough information to answer confidently:** the chat assistant
("Vigil") will say so plainly rather than guess. If you ask about something its
official documents don't cover, it replies with something like "I don't have an
official advisory that directly answers that — but if you think you're facing
fraud, call 1930 or visit cybercrime.gov.in," instead of making up advice. This
honesty is deliberate: a truthful "I'm not sure" is safer than a confident wrong
answer.

**One current, honest caveat worth knowing for a demo:** the app's smartest AI
brain (a large AI model) is switched off right now because its access key is
blocked. So the threat scores, the chat answers, and the case summaries are
currently produced by the app's dependable backup methods (the warning-sign
checklist and quoting official documents directly). Everything still works
end-to-end and the answers are real — they're just coming from the backup brain,
not the fanciest one. If a fresh access key is added, the same screens
automatically get richer answers with no other changes.

---

## 7. Quick Glossary (Plain-Language Only)

- **Citizen** — an ordinary member of the public using the app to check
  suspicious messages.
- **Officer** — a police/investigator user who works fraud cases.
- **Admin** — a user who manages accounts, the reference library, and system
  health.
- **Fraud Shield** — the citizen screen for checking one message, screenshot, or
  recording and getting a verdict.
- **Live Scam Interceptor / Live Shield** — the citizen screen that judges a scam
  conversation line by line, live, and warns you before you lose money.
- **Verdict** — the app's answer about a message: a danger score, a scam type, the
  warning signs it found, and what to do.
- **Threat score** — a danger rating from 0 (safe) to 100 (definitely a scam).
- **Severity / severity band** — the word bucket for that score: low, moderate,
  high, or critical.
- **Scam category** — the type of scam (for example "Digital Arrest Scam" or "UPI
  Refund Scam").
- **Red flags** — the specific warning signs the app spotted in a message.
- **Escalate / Report to Cyber Cell** — sending a report to the police queue so
  investigators can act on it.
- **Case** — an investigation file that groups related reports together.
- **Dossier / Intelligence Package** — a formal PDF evidence file the app builds
  for a case or a gang, suitable for handing to prosecutors.
- **Entity** — a single useful detail pulled from a report: a phone number,
  payment ID (UPI), email, website, or bank account.
- **UPI** — India's instant phone-based payment system; a "UPI ID" is like an
  address money is sent to.
- **OTP** — the one-time code your bank texts you; scammers try to trick you into
  sharing it.
- **KYC** — the "confirm your identity" process banks use; a common scam pretends
  your KYC needs urgent updating.
- **Connecting the dots / correlation** — noticing that the same detail (like one
  phone number) appears in several different people's reports, which links them.
- **Fraud ring** — a gang: a cluster of details and reports the app has connected
  together as one operation.
- **The network map / graph** — the visual web of dots (details) and lines
  (connections) officers explore.
- **Node** — one dot on that map (one detail). **Edge** — one line between two
  dots (a connection). **Cluster** — a group of tightly-connected dots.
- **Vigil** — the name of the citizen chat assistant that answers scam questions
  using official guidance.
- **Knowledge base** — the assistant's library of official fraud-guidance
  documents it quotes from.
- **Indexing / re-indexing a document** — filing a document into the library so
  the assistant can find and quote it.
- **Priority Score (Geo)** — a 0–100 rank of how much recent, serious fraud a city
  has, telling police where to focus.
- **Trend (rising / falling / stable)** — whether a city's or scam type's activity
  is going up, down, or staying flat.
- **Backup / degraded mode** — when the app uses a dependable fallback method
  because a fancier service (like the big AI brain) is unavailable.
- **Insufficient content** — the honest verdict the app gives when it genuinely
  couldn't read enough from an upload to judge it.
- **Escalation queue / Cyber Cell** — the pile of reports sent onward for police
  investigation.
- **System Health** — the admin screen showing whether each part of the app is
  running well.
