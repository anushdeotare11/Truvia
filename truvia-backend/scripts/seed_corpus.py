"""Realistic scam-text corpus generator for demo seeding.

Produces distinct, realistic scam message/call-transcript TEXT samples that are
submitted through the REAL Fraud Shield ingestion endpoint (POST /api/v1/reports/
submit). This module only *generates text + metadata*; it never touches the DB.

Design goals (calibrated to real reported-scam distribution):
  * Category mix: Banking/UPI ~37%, Digital Arrest ~17%, Delivery/parcel ~15%,
    Job/investment ~15%, KYC ~10%, remainder mixed/low-risk.
  * Every sample embeds at least one regex-extractable identifier (UPI handle,
    10-digit phone, http URL, IFSC, org keyword) so Agent 4 actually creates
    entities — the existing corpus left 180/205 reports entity-less.
  * A dedicated CORRELATED sub-batch reuses a small fixed set of fake UPI IDs /
    phone numbers / URLs across multiple complaints, so Louvain finds real
    multi-complaint rings instead of isolated single-report cliques.
  * Genuine severity variation, including low-risk/ambiguous messages.
  * Weighted city distribution (metros heavier) and a created_at spread over the
    last ~45 days.

All identifiers are INVENTED, plausible-format fakes (never real people's data).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

# Deterministic corpus for reproducibility across runs.
RNG = random.Random(20260721)

# ---------------------------------------------------------------------------
# City weighting — metros heavier, matching existing city spellings in the DB.
# ---------------------------------------------------------------------------
CITY_WEIGHTS = [
    ("Mumbai", 20), ("Delhi", 18), ("Bangalore", 16),
    ("Hyderabad", 11), ("Chennai", 10), ("Kolkata", 9), ("Pune", 9),
    ("Ahmedabad", 6), ("Jaipur", 5), ("Lucknow", 5),
    ("Chandigarh", 4), ("Kochi", 4),
]
_CITIES = [c for c, _ in CITY_WEIGHTS]
_CITY_W = [w for _, w in CITY_WEIGHTS]

# UPI handles that the extractor treats as UPI (letters-only, no dot).
UPI_HANDLES = ["okhdfc", "oksbi", "okaxis", "okicici", "ybl", "paytm", "axl", "ibl"]
BANK_ORGS = ["SBI", "HDFC", "ICICI", "Axis Bank", "PNB"]
FAKE_FIRST = ["Rahul", "Priya", "Amit", "Sneha", "Vikram", "Neha", "Arjun",
              "Kavya", "Rohan", "Anjali", "Sanjay", "Pooja", "Karan", "Divya"]
IFSC_PREFIX = ["SBIN", "HDFC", "ICIC", "UTIB", "PUNB", "KKBK"]


def _fake_phone() -> str:
    """Invented plausible Indian mobile (+91, starts 6-9), 10 digits."""
    return "+91 " + str(RNG.choice([6, 7, 8, 9])) + "".join(str(RNG.randint(0, 9)) for _ in range(9))


def _fake_upi() -> str:
    local = RNG.choice(FAKE_FIRST).lower() + str(RNG.randint(100, 9999))
    return f"{local}@{RNG.choice(UPI_HANDLES)}"


def _fake_url(word: str) -> str:
    tld = RNG.choice(["top", "xyz", "info", "online", "cc", "live"])
    return f"http://{word}-{RNG.randint(10, 999)}.{tld}"


def _fake_ifsc() -> str:
    return f"{RNG.choice(IFSC_PREFIX)}0{RNG.randint(100000, 999999)}"


def _amt() -> str:
    return f"{RNG.choice([1999, 2999, 4999, 5000, 9999, 14500, 25000, 49999, 75000, 125000]):,}"


@dataclass
class Sample:
    text: str
    category: str          # our label (for reporting; pipeline computes its own)
    severity_hint: str     # low | moderate | high | critical (expected-ish)
    city: str
    created_at: datetime
    correlation_group: Optional[str] = None  # ring id if part of correlated batch
    tags: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Date spread: last ~45 days, weighted toward more recent, correlated rings
# clustered into tight campaign windows.
# ---------------------------------------------------------------------------
_NOW = datetime(2026, 7, 21, 1, 30, tzinfo=timezone.utc)


def _spread_date() -> datetime:
    # Triangular so recent days are a bit heavier (realistic reporting curve).
    days_ago = int(RNG.triangular(0, 45, 8))
    secs = RNG.randint(0, 86399)
    return _NOW - timedelta(days=days_ago, seconds=secs)


def _campaign_date(center_days_ago: int, window: int) -> datetime:
    d = center_days_ago + RNG.randint(-window, window)
    d = max(0, d)
    return _NOW - timedelta(days=d, seconds=RNG.randint(0, 86399))


def _city() -> str:
    return RNG.choices(_CITIES, weights=_CITY_W, k=1)[0]


# ===========================================================================
# VARIED (non-correlated) sample builders — unique identifiers per sample.
# ===========================================================================
def _banking_upi() -> Sample:
    """Banking/UPI scams — including the real 'collect request' reversal trick."""
    upi, phone, amt = _fake_upi(), _fake_phone(), _amt()
    templates = [
        # The classic UPI collect-request reversal ("accept to receive") pattern.
        (f"Congratulations! You have received a refund of Rs {amt}. To credit the amount "
         f"to your account, please ACCEPT the collect request sent to your UPI app and "
         f"enter your UPI PIN. Sender ID: {upi}. For help call {phone}.", "critical"),
        (f"Your OLX buyer has sent Rs {amt} via UPI. Approve the payment request on your "
         f"GPay/PhonePe by entering your PIN to receive the money. Confirm at {upi} or call {phone}.",
         "high"),
        (f"SBI Alert: A cashback of Rs {amt} is pending. Accept the request from {upi} "
         f"and enter UPI PIN to claim. Assistance: {phone}.", "high"),
        (f"Sir I sent Rs {amt} to wrong number by mistake, please accept the request I sent "
         f"to {upi} and put your pin so it comes back to me. Calling from {phone}.", "high"),
        (f"Your electricity bill payment failed. Pay Rs {amt} immediately to {upi} to avoid "
         f"disconnection tonight. Helpline {phone}.", "moderate"),
    ]
    text, sev = RNG.choice(templates)
    return Sample(text, "Banking/UPI", sev, _city(), _spread_date(), tags=["upi", "phone"])


def _digital_arrest() -> Sample:
    org = RNG.choice(["CBI", "ED (Enforcement Directorate)", "Mumbai Police Cyber Cell",
                      "Customs Department", "Narcotics Control Bureau"])
    phone, upi, amt = _fake_phone(), _fake_upi(), _amt()
    templates = [
        (f"This is Officer from {org}. A parcel in your name containing illegal items and "
         f"MDMA has been seized. An FIR is registered. You are under DIGITAL ARREST and must "
         f"stay on this video call. Do not contact anyone. Transfer Rs {amt} to {upi} to clear "
         f"your name or a warrant will be issued. Case officer: {phone}.", "critical"),
        (f"{org} calling. Your Aadhaar is linked to a money laundering case. To avoid immediate "
         f"arrest, remain on the call and transfer verification deposit of Rs {amt} to {upi}. "
         f"Contact {phone}.", "critical"),
        (f"Namaste, {org} se baat kar raha hoon. Aapke naam ka ek parcel customs me pakda gaya "
         f"hai. Aap digital arrest me hmain, kisi ko mat bataiye. Rs {amt} {upi} par bhejiye "
         f"warna aaj arrest hoga. Call {phone}.", "critical"),
    ]
    text, sev = RNG.choice(templates)
    return Sample(text, "Digital Arrest", sev, _city(), _spread_date(), tags=["upi", "phone", "org"])


def _delivery() -> Sample:
    phone, url, amt = _fake_phone(), _fake_url(RNG.choice(["indiapost-redeliver", "fedex-track",
                                                           "dtdc-parcel", "bluedart-kyc"])), _amt()
    templates = [
        (f"[India Post] Your parcel is held at the warehouse due to incomplete address. "
         f"Pay a redelivery fee of Rs {RNG.choice([25,49,99])} and update details at {url}. "
         f"Support: {phone}.", "high"),
        (f"FedEx: Shipment suspended pending customs clearance charge of Rs {amt}. Complete "
         f"payment within 12 hours at {url} or the package will be returned. Call {phone}.",
         "moderate"),
        (f"Your Amazon order could not be delivered. Reschedule delivery by verifying at {url}. "
         f"Contact courier {phone}.", "moderate"),
    ]
    text, sev = RNG.choice(templates)
    return Sample(text, "Delivery/Parcel", sev, _city(), _spread_date(), tags=["url", "phone"])


def _job_investment() -> Sample:
    phone, upi, url = _fake_phone(), _fake_upi(), _fake_url(RNG.choice(["earn-daily", "task-rewards",
                                                                        "crypto-double", "wfh-jobs"]))
    templates = [
        (f"Work from home opportunity! Earn Rs 5000/day by liking YouTube videos and completing "
         f"Telegram tasks. Register with a refundable deposit of Rs {RNG.choice([1000,2000,5000])} "
         f"to {upi}. Join: {url}. WhatsApp {phone}.", "high"),
        (f"Your investment in our trading plan has grown 300%! Deposit more via {upi} to unlock "
         f"withdrawal of your profit. Dashboard: {url}. Advisor {phone}.", "high"),
        (f"Part-time job selected for your profile. Prepaid task fee Rs {RNG.choice([500,1500])} "
         f"required to activate account at {url}. Commission paid daily. Contact {phone}.", "moderate"),
    ]
    text, sev = RNG.choice(templates)
    return Sample(text, "Job/Investment", sev, _city(), _spread_date(), tags=["upi", "phone", "url"])


def _kyc() -> Sample:
    org = RNG.choice(BANK_ORGS)
    url, phone = _fake_url(RNG.choice(["kyc-update", "netbanking-verify", "acct-reactivate"])), _fake_phone()
    templates = [
        (f"Dear customer, your {org} account will be BLOCKED today as your KYC is expired. "
         f"Update immediately by clicking {url}. For help call {phone}.", "critical"),
        (f"{org} NetBanking: Your PAN card is not updated. Verify now at {url} to avoid account "
         f"suspension. Helpline {phone}.", "high"),
        (f"Your bank account has been temporarily deactivated pending re-verification. Complete "
         f"KYC at {url}. Support {phone}.", "high"),
    ]
    text, sev = RNG.choice(templates)
    return Sample(text, "KYC/Verification", sev, _city(), _spread_date(), tags=["url", "phone", "org"])


def _low_risk() -> Sample:
    """Genuinely low-risk / ambiguous messages (still carry an entity for the graph)."""
    phone, upi = _fake_phone(), _fake_upi()
    templates = [
        (f"Hi, this is {RNG.choice(FAKE_FIRST)} from the apartment viewing. Can we reschedule to "
         f"5 PM tomorrow? Call me at {phone}.", "low"),
        (f"Reminder: your monthly gym membership renews next week. Questions? Reach us at {phone}.",
         "low"),
        (f"Thanks for splitting the dinner bill! You can send my share to {upi} whenever convenient.",
         "low"),
        (f"Your OTP for login is 4471. Do not share it with anyone. - Support {phone}.", "low"),
        (f"Team, the project sync moved to Thursday 11am. Ping me at {phone} if that clashes.",
         "low"),
        (f"Your food order #{RNG.randint(1000,9999)} is out for delivery. Rider contact {phone}.",
         "low"),
    ]
    text, sev = RNG.choice(templates)
    return Sample(text, "Low-risk/Other", sev, _city(), _spread_date(), tags=["phone"])


# ===========================================================================
# CORRELATED sub-batch — fixed reused identifiers => real Louvain rings.
# Each ring's complaints share a tight identifier clique (UPI+phone+URL/org),
# so the entities co-occur repeatedly and form a dense, separable community.
# ===========================================================================
RINGS = {
    "RING_CBI_ARREST": {
        "upi": "cbicase.settle@okaxis",
        "phone": "+91 9812345670",
        "url": "http://cbi-clearance-portal.top",
        "org": "CBI",
        "center_days_ago": 12, "window": 4,
        "templates": [
            "This is Inspector Rana from {org} Headquarters. A parcel with your Aadhaar was "
            "intercepted with narcotics. You are under digital arrest. Do NOT disconnect. "
            "Deposit the case settlement of Rs {amt} to {upi} now. Verify the notice at {url}. "
            "Case desk: {phone}.",
            "{org} FINAL WARNING: Your bank accounts are frozen in money-laundering case #DL-4471. "
            "Transfer Rs {amt} to the RBI-verified escrow {upi} to avoid arrest today. "
            "Official portal {url}. Officer line {phone}.",
            "Video call from {org} cyber unit. Stay on camera, contacting a lawyer is a crime. "
            "Clear your name by sending Rs {amt} to {upi}. Warrant copy at {url}. Call {phone}.",
            "Madam, {org} customs division. Your KYC is used in illegal transactions. Digital arrest "
            "issued. Settlement Rs {amt} via {upi}. Details: {url}. Helpline {phone}.",
            "{org} notice: appear virtually or be arrested. Pay refundable security Rs {amt} to "
            "{upi}. Upload ID at {url}. Duty officer {phone}.",
        ],
    },
    "RING_UPI_REFUND": {
        "upi": "instantrefund.help@okhdfc",
        "phone": "+91 9701234567",
        "url": "http://refund-claim-desk.xyz",
        "org": "HDFC",
        "center_days_ago": 20, "window": 5,
        "templates": [
            "{org} Refund Dept: A reversal of Rs {amt} is pending for your failed transaction. "
            "ACCEPT the collect request from {upi} and enter UPI PIN to receive it. Track: {url}. "
            "Care {phone}.",
            "Your recharge of Rs {amt} failed. To get an instant refund, approve the request from "
            "{upi} with your PIN. Status at {url}. Support {phone}.",
            "Sir aapka Rs {amt} ka refund atka hai. {upi} se aayi request accept karke pin daaliye, "
            "paisa turant wapas aayega. Link {url}. Call {phone}.",
            "Cashback of Rs {amt} approved! Accept the UPI request from {upi} to credit your wallet. "
            "Claim page {url}. Helpline {phone}.",
            "Refund processing: enter UPI PIN after accepting request from {upi} to receive Rs {amt}. "
            "Verify {url}. Agent {phone}.",
        ],
    },
    "RING_PARCEL_CUSTOMS": {
        "upi": "parcel.customs@ybl",
        "phone": "+91 8890011223",
        "url": "http://indiapost-customs-fee.online",
        "org": "Customs",
        "center_days_ago": 7, "window": 3,
        "templates": [
            "India Post {org}: Your international parcel is held. Pay clearance fee Rs {amt} to "
            "{upi} and confirm at {url}. Enquiry {phone}.",
            "{org} Dept: Package with gifts detained, duty of Rs {amt} pending. Settle to {upi}. "
            "Redelivery form {url}. Call {phone}.",
            "Your courier is stuck at {org}. Pay Rs {amt} handling charge via {upi} within 6 hours "
            "or it returns. Details {url}. Support {phone}.",
            "Parcel notice: {org} requires Rs {amt} tax to release your shipment. UPI {upi}. "
            "Track {url}. Helpline {phone}.",
        ],
    },
    "RING_TASK_JOB": {
        "upi": "taskrewards.pay@paytm",
        "phone": "+91 9600112233",
        "url": "http://daily-task-earn.live",
        "center_days_ago": 28, "window": 5,
        "templates": [
            "Congrats! You are shortlisted for a work-from-home job. Pay activation Rs {amt} to "
            "{upi} and start earning. Register {url}. WhatsApp {phone}.",
            "Complete 3 Telegram tasks and earn Rs 6000 daily. Refundable deposit Rs {amt} to {upi}. "
            "Join {url}. Coordinator {phone}.",
            "Your trading account profit is Rs {amt}. Add same amount to {upi} to withdraw. "
            "Dashboard {url}. Advisor {phone}.",
            "Part-time selected. Prepaid task fee Rs {amt} to {upi} to unlock salary. Portal {url}. "
            "HR {phone}.",
        ],
    },
}


def _build_correlated() -> list[Sample]:
    out: list[Sample] = []
    for ring_id, cfg in RINGS.items():
        for tmpl in cfg["templates"]:
            text = tmpl.format(
                org=cfg.get("org", ""),
                upi=cfg["upi"],
                phone=cfg["phone"],
                url=cfg["url"],
                amt=_amt(),
            )
            cat = ("Digital Arrest" if "ARREST" in ring_id else
                   "Banking/UPI" if "REFUND" in ring_id else
                   "Delivery/Parcel" if "PARCEL" in ring_id else "Job/Investment")
            out.append(Sample(
                text=text,
                category=cat,
                severity_hint="critical",
                city=_city(),
                created_at=_campaign_date(cfg["center_days_ago"], cfg["window"]),
                correlation_group=ring_id,
                tags=["correlated", "upi", "phone", "url"],
            ))
    return out


def build_corpus(varied_count: int = 130) -> list[Sample]:
    """Return the full corpus: `varied_count` varied samples + correlated batch.

    Category mix across the varied set (approx): UPI 37%, Digital Arrest 17%,
    Delivery 15%, Job/Investment 15%, KYC 10%, Low-risk/other ~6%.
    """
    builders_weighted = [
        (_banking_upi, 0.37),
        (_digital_arrest, 0.17),
        (_delivery, 0.15),
        (_job_investment, 0.15),
        (_kyc, 0.10),
        (_low_risk, 0.06),
    ]
    builders = [b for b, _ in builders_weighted]
    weights = [w for _, w in builders_weighted]

    varied: list[Sample] = []
    seen_text: set[str] = set()
    attempts = 0
    while len(varied) < varied_count and attempts < varied_count * 20:
        attempts += 1
        b = RNG.choices(builders, weights=weights, k=1)[0]
        s = b()
        if s.text in seen_text:
            continue
        seen_text.add(s.text)
        varied.append(s)

    correlated = _build_correlated()
    corpus = varied + correlated
    RNG.shuffle(corpus)
    return corpus


if __name__ == "__main__":
    # Quick self-check / preview.
    from collections import Counter
    corpus = build_corpus()
    print(f"Total samples: {len(corpus)}")
    print("Category mix:", dict(Counter(s.category for s in corpus)))
    print("Severity hint:", dict(Counter(s.severity_hint for s in corpus)))
    print("Correlated:", sum(1 for s in corpus if s.correlation_group))
    print("Ring groups:", dict(Counter(s.correlation_group for s in corpus if s.correlation_group)))
    print("City mix:", dict(Counter(s.city for s in corpus)))
    print("\n--- 3 sample previews ---")
    for s in corpus[:3]:
        print(f"[{s.category}/{s.severity_hint}/{s.city}/{s.created_at.date()}] {s.text[:120]}...")
