"""
Comprehensive seed data script for Truvia development database.
Runnable via: python -m scripts.seed_data (from truvia-backend/ directory)

Creates:
- 6 users (admin, officers, citizens)
- 180 scam reports across 8 categories with realistic Indian scam text
- Runs pipeline continuation on each report (threat scoring + entity extraction)
- 15 cases grouping related reports
- 20 knowledge base documents with chunked embeddings
"""
import asyncio
import sys
import os
import uuid
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.postgres_client import AsyncSessionLocal, check_and_create_tables
from app.models.report import Report, Entity, ReportEntity, Relationship, ThreatScore, Evidence
from app.models.user import User
from app.models.case import Case, CaseReport
from app.models.knowledge import KnowledgeBase, KnowledgeBaseChunk
from app.models.alert import Alert
from app.core.security import get_password_hash
from app.orchestration.pipeline import run_pipeline_continuation
from app.agents.investigation import investigation_agent
from app.data.vector_client import get_embedding
from sqlalchemy import select


# ============================================================================
# CONSTANTS
# ============================================================================

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata",
    "Pune", "Ahmedabad", "Jaipur", "Lucknow", "Chandigarh", "Kochi"
]

CATEGORIES = [
    "Digital Arrest", "UPI Fraud", "KYC Scam", "Job Scam",
    "Sextortion", "Loan Scam", "Electricity Scam", "Investment Fraud"
]


# ============================================================================
# SCAM TEXT TEMPLATES (3+ variations per category)
# ============================================================================

SCAM_TEMPLATES = {
    "Digital Arrest": [
        "Sir, I am calling from the CBI Mumbai office. Your Aadhaar number 5678-XXXX is linked to money laundering. FIR number CBI/2026/4521 has been filed. Transfer Rs 50,000 to UPI ID: cbi.verification@ybl or face immediate arrest. Contact officer at +91 9876543210. IFSC: SBIN0001234.",
        "This is Inspector Rajesh from Delhi Cyber Crime Cell. We intercepted a parcel from China in your name containing 500g MDMA and 3 fake passports. Case number DL-CYB/2026/891. You are under digital arrest. Do not disconnect this video call. Transfer Rs 1,25,000 security deposit to customs.clearance@okicici or we will send police to your location. Call +91 8765432198 to verify.",
        "Madam, NCB Narcotics Control Bureau here. Your bank account HDFC-XXXX7834 received Rs 48 lakh from a hawala network. Under PMLA Section 3, your assets are being frozen. To avoid arrest, transfer Rs 2,00,000 compliance bond to upi: ncb.bond2026@axl. Ref officer badge NB-4419. Call +91 7654321098. IFSC: HDFC0002341.",
        "I am DSP Verma from CBI Anti-Corruption Unit. A money laundering case CBI/ACU/2026/112 has been registered. Your PAN card ABCDE1234F is flagged. Transfer Rs 75,000 to secure wallet cbi.secure@paytm or arrest warrant will be issued within 2 hours. Contact +91 9988776655.",
    ],
    "UPI Fraud": [
        "Congratulations! You won Rs 5,00,000 in Amazon Lucky Draw. To claim, send Rs 999 processing fee to amazon.prize@paytm. Call 8765432109 for details. Offer valid today only. Reference: AMZN-WIN-2026-7781.",
        "Dear customer, your Flipkart order #FK2026891 refund of Rs 2,499 failed. To receive refund immediately, accept the UPI collect request from flipkart.refund@ybl. Do not share PIN with anyone except our automated system. Support: +91 9123456780.",
        "PhonePe cashback of Rs 1,500 credited to your account! To activate, scan QR code and enter UPI PIN. Amount will reflect in 24hrs. For issues call +91 8899776655 or pay Re 1 to verify at phonepe.bonus@axl. Ref: PP-CB-20261.",
        "Your Google Pay reward of Rs 10,000 is pending. Complete verification by sending Rs 50 registration fee to gpay.rewards@oksbi. Call helpline +91 7788996644. IFSC: SBIN0003456. Limited time offer expires tonight.",
    ],
    "KYC Scam": [
        "ALERT: Your SBI account will be blocked in 24 hours due to incomplete KYC. Click link https://sbi-kyc-update.com or call +91 9876501234 immediately. Share Aadhaar OTP to verify. Failure to comply will freeze your account permanently. UPI: sbi.kyc@ybl.",
        "Dear HDFC customer, your account ending 7823 KYC has expired. Update now or lose access to netbanking and UPI. Call our KYC desk at +91 8765409876. Share your debit card number and CVV for instant verification. Ref: HDFC-KYC-2026. IFSC: HDFC0001789.",
        "Paytm KYC verification required urgently. Your wallet will be suspended and Rs 45,000 balance frozen if not completed by tonight. Visit https://paytm-kyc-verify.in or call +91 7654321876. Transfer Rs 10 verification charge to paytm.kyc@axl.",
        "ICICI Bank: Your account is flagged for KYC non-compliance under RBI circular 2026/04. Call +91 9988001122 within 1 hour to avoid permanent deactivation. Share OTP received on registered mobile. UPI: icici.kycdesk@okicici. IFSC: ICIC0004567.",
    ],
    "Job Scam": [
        "Congratulations! You are selected for Data Entry work from home. Earn Rs 15,000-45,000/month. Pay Rs 2,500 registration fee to start immediately. UPI: hiring.desk@paytm. Call HR at +91 9876234567. Company: Global Tech Solutions Pvt Ltd. IFSC: UTIB0001234.",
        "Amazon is hiring! Part-time product review job. Salary Rs 8,000/week. No experience needed. Pay Rs 1,000 security deposit to amazon.careers@ybl for ID card processing. WhatsApp +91 8765123456 for joining link. Limited 50 positions only.",
        "Dear candidate, your resume matched for Senior Manager position at Infosys. CTC 25 LPA. Pay Rs 5,000 background verification fee to infosys.hr@okaxis. Contact recruitment head +91 7654098765. Offer letter will be emailed within 2 hours. Ref: INFY-REC-2026.",
        "Urgent hiring for government data entry operator. Monthly salary Rs 35,000 + benefits. Registration fee Rs 3,500 via UPI govt.recruitment@oksbi. Call +91 9876567890. Last date today. IFSC: SBIN0005678.",
    ],
    "Sextortion": [
        "I have your video from the WhatsApp call last night. If you don't transfer Rs 50,000 to this UPI ID blackmail.payment@ybl within 2 hours, I will upload it to YouTube and send to all your Facebook friends. Contact +91 9871234560 to negotiate.",
        "Your compromising photos from Instagram DMs are with me. Pay Rs 25,000 to secret.keeper@paytm or they go viral on social media. I have screenshots of everything. No police can help you. WhatsApp +91 8765098712 for proof.",
        "Hello, remember our video chat on dating app? I recorded everything. Transfer Rs 1,00,000 to privacy.protect@okaxis within 24 hours or the video goes to your employer and family WhatsApp groups. Call +91 7650981234. I am serious.",
        "I hacked your phone camera and have intimate recordings. Pay Rs 75,000 in Bitcoin or UPI to hacker.anon@ybl. Don't try going to cyber cell, I will leak instantly. Contact +91 9988123456 if you want to verify. You have 6 hours.",
    ],
    "Loan Scam": [
        "Pre-approved personal loan of Rs 10,00,000 at 0% interest! No documents needed. Pay Rs 5,000 processing fee to instant.loan@paytm to activate. Call +91 9876789012. Offer from RBI-approved NBFC. IFSC: KKBK0001234. Limited period.",
        "Dear customer, your CIBIL score qualifies for Rs 5,00,000 instant loan. Processing charges Rs 3,000 only. Transfer to loan.process@ybl and get money in 30 minutes. No guarantor required. Call +91 8765678901 for EMI details.",
        "Congratulations! Bajaj Finance approved your loan of Rs 8,00,000. To disburse, pay Rs 7,500 insurance + stamp duty to bajaj.disburse@okaxis. Call branch manager +91 7654567890. IFSC: UTIB0002345. Amount credited within 4 hours.",
        "Emergency loan available! Rs 2,00,000 in just 10 minutes. Aadhaar-based instant approval. Pay Rs 2,000 verification fee to quick.cash@oksbi. No credit check. Call +91 9123456789. App download: https://quick-loan-app.com.",
    ],
    "Electricity Scam": [
        "Your electricity connection will be disconnected in 2 hours due to pending bill of Rs 8,750. Pay immediately to avoid disconnection. UPI: electricity.pay@paytm. Call customer care +91 9876098765. Bill ref: EB/2026/Mumbai/4412. IFSC: SBIN0006789.",
        "URGENT: MSEDCL notice - your meter reading shows tampering. Fine of Rs 15,000 must be paid today or FIR will be filed. Transfer to msedcl.fine@ybl. Contact officer +91 8765987654. Your consumer number: MH2026-445512.",
        "Dear consumer, your electricity bill overdue Rs 12,500. Last date expired. Disconnection team dispatched to your address. Pay now to cancel: UPI power.bill@okaxis or call +91 7654876543. Reference: TNEBLR/2026/8891.",
        "Final notice: Rs 6,200 electricity dues pending for 3 months. Connection will be permanently terminated tonight. Immediate payment to elec.clearance@oksbi. Helpline +91 9988765432. IFSC: HDFC0007890. Consumer ID: KA-BLR-20261234.",
    ],
    "Investment Fraud": [
        "Join our exclusive trading WhatsApp group! Guaranteed 30% monthly returns on stock market investments. Minimum investment Rs 25,000 via UPI: trading.guru@paytm. Call mentor +91 9876345678. Already 500+ members earning lakhs. IFSC: ICIC0008901.",
        "Crypto investment opportunity! Double your money in 7 days. Send Rs 50,000 to crypto.invest@ybl and receive Rs 1,00,000 back guaranteed. Limited slots. WhatsApp +91 8765234567. Company: Digital Gold Mining Ltd.",
        "Dear investor, our AI trading bot generates 5% daily profit. Invest Rs 1,00,000 minimum through UPI ai.trader@okaxis. Withdrawal anytime. Call account manager +91 7654123456. 100% capital protection guarantee. SEBI registration pending.",
        "Earn Rs 5,000 daily from IPO grey market! No risk involved. Register with Rs 10,000 to ipo.booking@oksbi. Our team handles everything. Call +91 9123987654. Last 3 IPOs gave 200%+ listing gains. Join 1000+ happy investors.",
    ],
}


# ============================================================================
# KNOWLEDGE BASE DOCUMENTS
# ============================================================================

KNOWLEDGE_DOCS = [
    # RBI (5 docs)
    {
        "source": "RBI",
        "title": "How banks never ask for OTP",
        "content": "The Reserve Bank of India categorically states that no bank, financial institution, or RBI official will ever call or message you asking for your OTP, PIN, CVV, or full card number. Any person requesting these credentials over phone, SMS, email, or WhatsApp is a fraudster. Banks use secure portals for verification and never conduct KYC over phone calls. If you receive such a call, disconnect immediately and report to your bank's official helpline. Legitimate OTPs are generated only when YOU initiate a transaction. Never share OTP with anyone, even if they claim to be from the bank's fraud department.",
    },
    {
        "source": "RBI",
        "title": "UPI safety guidelines",
        "content": "UPI (Unified Payments Interface) is designed for secure transactions but requires user vigilance. Key safety rules: 1) Never share your UPI PIN with anyone. 2) You do NOT need to enter PIN to RECEIVE money — if someone asks you to enter PIN to receive, it is a scam. 3) Always verify the recipient name before confirming payment. 4) Be cautious of QR codes sent via messaging apps — scanning and entering PIN always DEBITS money. 5) Set transaction limits on your UPI app. 6) Enable notifications for every transaction. 7) Only use official UPI apps from Google Play Store or Apple App Store. Report unauthorized transactions to your bank within 24 hours.",
    },
    {
        "source": "RBI",
        "title": "Digital payment fraud indicators",
        "content": "Common indicators of digital payment fraud include: urgency tactics pressuring immediate transfer, threats of account blocking or legal action, unsolicited calls claiming refunds or rewards, requests to install screen-sharing apps like AnyDesk or TeamViewer, collect requests from unknown UPI IDs, promises of unrealistic returns on investments, requests to transfer money to verify account, and fake customer care numbers found through Google search instead of official bank websites. Always verify through official channels before making any payment.",
    },
    {
        "source": "RBI",
        "title": "RBI says never share card CVV",
        "content": "Your card CVV (Card Verification Value) is a 3-digit security code on the back of your debit or credit card. RBI guidelines mandate that this number should NEVER be shared with anyone including bank officials. The CVV is required only for online transactions initiated by the cardholder. No legitimate entity will ever ask for your full card number plus CVV plus expiry date over phone. If someone has these three details, they can make unauthorized online purchases. Cover your CVV with tape for physical safety. Report card compromise to your bank immediately for blocking.",
    },
    {
        "source": "RBI",
        "title": "KYC update process — official RBI guide",
        "content": "Know Your Customer (KYC) updates are conducted ONLY through official bank branches or verified digital banking portals. RBI clarifies: 1) Banks will never send links via SMS or WhatsApp for KYC updates. 2) KYC does not require sharing OTP or PIN. 3) Your account will not be blocked on the same day for KYC non-compliance — banks provide 30+ days notice via registered post. 4) Video KYC is done only through the bank's official app. 5) No fee is charged for KYC updates. If you receive KYC-related messages with links or phone numbers, they are fraudulent.",
    },
    # CERT-In (5 docs)
    {
        "source": "CERT-In",
        "title": "Phishing attack identification",
        "content": "Phishing attacks attempt to steal sensitive information by impersonating trusted entities. Identification markers: 1) Check sender email carefully — fraudsters use slight misspellings like support@hdfc-bank.com instead of support@hdfcbank.com. 2) Hover over links before clicking to see actual URL. 3) Look for generic greetings like Dear Customer instead of your name. 4) Grammar and spelling errors indicate fraud. 5) Legitimate organizations never ask for passwords via email. 6) Urgency and fear tactics are key indicators. 7) Verify by contacting the organization through their official website directly.",
    },
    {
        "source": "CERT-In",
        "title": "Digital arrest scam modus operandi",
        "content": "Digital arrest is a sophisticated scam where fraudsters impersonate law enforcement (CBI, Police, Customs, NCB) via video calls. Modus operandi: 1) Victim receives call claiming illegal parcel intercepted in their name. 2) Transferred to fake senior officer on video call with fake uniform and background. 3) Told they are under digital arrest and cannot disconnect. 4) Threatened with immediate physical arrest if they don't cooperate. 5) Asked to transfer large sums as security deposit or bail. 6) Made to stay on video call for hours under psychological pressure. NO LAW ENFORCEMENT AGENCY conducts arrests over video calls or demands money.",
    },
    {
        "source": "CERT-In",
        "title": "Fake website identification",
        "content": "Fake websites are designed to steal credentials and payment information. How to identify: 1) Check URL carefully — look for misspellings, extra characters, or different domains (e.g., sbi-online.com vs onlinesbi.sbi). 2) Look for HTTPS and valid SSL certificate — but note that even scam sites may have HTTPS. 3) Check the domain age using WHOIS lookup — newly registered domains are suspicious. 4) Verify through official app or bookmark. 5) Never enter banking credentials on links received via SMS/email. 6) Check for contact information and physical address. 7) Use official bank mobile apps instead of browser banking when possible.",
    },
    {
        "source": "CERT-In",
        "title": "Social engineering attack patterns",
        "content": "Social engineering exploits human psychology rather than technical vulnerabilities. Common patterns in India: 1) Pretexting — creating fake scenarios (your son is in police custody). 2) Baiting — offering free gifts, lottery wins, or cashback. 3) Quid pro quo — offering help in exchange for information (fake tech support). 4) Tailgating — using authority figures to gain trust. 5) Vishing — voice phishing using VoIP numbers that appear local. Defense: Never make decisions under pressure, verify independently through official channels, establish family code words for emergency verification, and remember that real urgency never requires immediate payment.",
    },
    {
        "source": "CERT-In",
        "title": "Ransomware prevention",
        "content": "Ransomware encrypts your files and demands payment for decryption. Prevention guidelines from CERT-In: 1) Keep operating systems and software updated with latest patches. 2) Do not open email attachments from unknown senders. 3) Maintain offline backups of important data regularly. 4) Use reputable antivirus software with real-time protection. 5) Disable macros in Microsoft Office files from untrusted sources. 6) Do not download software from unofficial sources. 7) If infected, do NOT pay the ransom — report to CERT-In and local cyber cell. 8) Segment networks to limit spread of infection.",
    },
    # MHA (5 docs)
    {
        "source": "MHA",
        "title": "Cyber crime reporting process",
        "content": "The Ministry of Home Affairs has established multiple channels for reporting cyber crimes in India: 1) National Cyber Crime Reporting Portal: https://cybercrime.gov.in — File detailed complaints with evidence. 2) Helpline 1930: Available 24x7 for immediate reporting of financial fraud — calling within golden hour (first 2 hours) increases recovery chances. 3) Local Police Station: File FIR under IT Act sections. 4) Bank: Immediately inform your bank to freeze the fraudulent transaction. Steps: Report on 1930 first, then file detailed complaint on portal, then visit nearest cyber cell with evidence. Preserve all screenshots, call recordings, and transaction details as evidence.",
    },
    {
        "source": "MHA",
        "title": "Digital arrest — how government actually contacts citizens",
        "content": "Important clarification from MHA regarding legitimate government communication: 1) No government agency conducts arrests via phone or video call. 2) Arrest requires physical presence of police with valid warrant. 3) CBI/Police will NEVER ask for money over phone. 4) Court proceedings are NEVER conducted on Skype or WhatsApp. 5) No officer will ask you to stay on video call. 6) Government notices come via registered post or official email with verifiable digital signatures. 7) You can always verify by visiting the nearest police station in person. 8) If someone claims to be police on call, ask for their name and station — verify independently.",
    },
    {
        "source": "MHA",
        "title": "1930 helpline usage guide",
        "content": "The 1930 Cyber Crime Helpline is India's emergency number for financial fraud. How to use effectively: 1) Call immediately after discovering unauthorized transaction — golden hour is critical. 2) Provide: your bank name, account number, transaction amount, recipient details if known. 3) The operator will coordinate with your bank to freeze the fraudulent account. 4) Note down the complaint number provided. 5) Follow up by filing detailed complaint on cybercrime.gov.in within 24 hours. 6) The helpline operates 24 hours, 7 days a week. 7) Available in Hindi and English. 8) For non-financial cyber crimes, file directly on the portal. Success rate is highest when reported within 30 minutes of fraud.",
    },
    {
        "source": "MHA",
        "title": "NCRP portal filing procedure",
        "content": "National Cyber Crime Reporting Portal (NCRP) filing procedure: 1) Visit https://cybercrime.gov.in. 2) Select Report Cyber Crime or Report Financial Fraud. 3) Enter your mobile number for OTP verification. 4) Fill victim details — name, address, ID proof. 5) Select crime category — financial fraud, social media, hacking, etc. 6) Describe incident in detail with timeline. 7) Upload evidence — screenshots, bank statements, call recordings (max 10MB each). 8) Submit and note acknowledgment number. 9) Track status using Track Your Complaint section. 10) Police from the relevant jurisdiction will contact you within 7 working days.",
    },
    {
        "source": "MHA",
        "title": "Common impersonation scams",
        "content": "Fraudsters commonly impersonate these entities: 1) Police/CBI/NCB — threatening arrest for fake cases. 2) Bank officials — claiming account issues requiring OTP. 3) Telecom companies (TRAI) — threatening SIM disconnection. 4) Income Tax Department — claiming tax refunds or dues. 5) Electricity boards — threatening disconnection. 6) E-commerce companies — fake refunds and delivery issues. 7) Insurance companies — claiming bonus maturity. 8) Government scheme officers — PM Kisan, Ayushman Bharat fake benefits. Remember: No government body demands money over phone, threatens immediate action without written notice, or asks for personal banking credentials.",
    },
    # NPCI (5 docs)
    {
        "source": "NPCI",
        "title": "UPI PIN safety",
        "content": "Your UPI PIN is the gateway to your bank account. Critical safety guidelines from NPCI: 1) UPI PIN is ONLY needed when SENDING money or making payments — never for receiving. 2) Never enter UPI PIN on request from unknown persons. 3) Change UPI PIN regularly (every 90 days recommended). 4) Do not use birth dates, anniversaries, or sequential numbers as PIN. 5) Never share UPI PIN over phone, chat, or in person. 6) If you suspect PIN compromise, change it immediately in your UPI app. 7) UPI PIN is NOT required for checking balance in most apps. 8) Legitimate companies never call asking for UPI PIN verification.",
    },
    {
        "source": "NPCI",
        "title": "QR code fraud prevention",
        "content": "QR code frauds are rapidly increasing in India. NPCI safety advisory: 1) Scanning a QR code ALWAYS debits money from your account — it is NEVER used for receiving payments. 2) If someone says scan QR to receive money, it is 100% fraud. 3) Verify merchant name displayed after scanning before entering PIN. 4) Do not scan QR codes received via WhatsApp or SMS from unknown numbers. 5) Physical QR codes at shops can be tampered — verify the merchant name matches the store. 6) Never scan QR codes from classified ad sellers claiming to send advance payment. 7) If you accidentally scan a fraudulent QR, do NOT enter your PIN — simply close the app.",
    },
    {
        "source": "NPCI",
        "title": "Authorized UPI collect requests",
        "content": "UPI collect requests can be misused by fraudsters. How to stay safe: 1) Only accept collect requests from known contacts and verified merchants. 2) Read the collect request message carefully — fraudsters add misleading notes like Refund of Rs 5000. 3) Entering PIN on a collect request ALWAYS sends money FROM your account. 4) Block and report unknown UPI IDs sending repeated collect requests. 5) Legitimate refunds are credited directly — they never require you to accept a collect request. 6) Enable auto-decline for collect requests from non-contacts in app settings. 7) Report suspicious UPI IDs through your UPI app's report function.",
    },
    {
        "source": "NPCI",
        "title": "How to identify fake UPI apps",
        "content": "Fake UPI apps are designed to show fake payment confirmation screens. Identification guide: 1) Only download UPI apps from Google Play Store or Apple App Store. 2) Check developer name — official apps show the bank or NPCI-authorized company. 3) Verify app permissions — fake apps often request unnecessary access. 4) Fake payment screenshots show inconsistencies in font, spacing, or transaction ID format. 5) Always verify payment received through your own bank app or SMS, not the payer's screen. 6) Legitimate UPI apps show RBI/NPCI authorization marks. 7) If in doubt, check NPCI's official website for list of authorized UPI apps. 8) Report fake apps to Google Play Store and local cyber police.",
    },
    {
        "source": "NPCI",
        "title": "UPI complaint filing",
        "content": "If you face issues with UPI transactions, follow this resolution process: 1) First contact your UPI app's customer support through the app itself. 2) If unresolved in 48 hours, file complaint on your bank's grievance portal. 3) For unauthorized transactions, immediately call 1930 and then your bank. 4) Raise dispute through UPI app: Go to transaction history > select transaction > Raise dispute. 5) NPCI escalation: If bank doesn't resolve in 30 days, escalate to NPCI at npci.org.in. 6) Banking Ombudsman: Final recourse through RBI's Ombudsman scheme. 7) Keep transaction reference number, UTR number, and screenshots for all complaints. Resolution timelines: 7 days for bank, 30 days for NPCI escalation.",
    },
]


# ============================================================================
# USER DEFINITIONS
# ============================================================================

USERS = [
    {
        "email": "admin@truvia.ai",
        "role": "admin",
        "name": "Admin Truvia",
        "password": "admin123",
        "phone": "+91 9000000001",
        "officer_badge_id": None,
    },
    {
        "email": "officer1@truvia.ai",
        "role": "officer",
        "name": "Inspector Priya Sharma",
        "password": "officer123",
        "phone": "+91 9000000002",
        "officer_badge_id": "BADGE-OFC-001",
    },
    {
        "email": "officer2@truvia.ai",
        "role": "officer",
        "name": "SI Arjun Mehta",
        "password": "officer123",
        "phone": "+91 9000000003",
        "officer_badge_id": "BADGE-OFC-002",
    },
    {
        "email": "citizen1@truvia.ai",
        "role": "citizen",
        "name": "Rahul Verma",
        "password": "citizen123",
        "phone": "+91 9000000004",
        "officer_badge_id": None,
    },
    {
        "email": "citizen2@truvia.ai",
        "role": "citizen",
        "name": "Sneha Patel",
        "password": "citizen123",
        "phone": "+91 9000000005",
        "officer_badge_id": None,
    },
    {
        "email": "citizen3@truvia.ai",
        "role": "citizen",
        "name": "Ankit Gupta",
        "password": "citizen123",
        "phone": "+91 9000000006",
        "officer_badge_id": None,
    },
]


# ============================================================================
# TASK 12.1: SEED USERS AND REPORTS
# ============================================================================

async def seed_users(session) -> list:
    """Create 6 users and return their DB objects."""
    created_users = []
    for user_def in USERS:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.email == user_def["email"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"  User {user_def['email']} already exists, skipping.")
            created_users.append(existing)
            continue

        user = User(
            id=uuid.uuid4(),
            email=user_def["email"],
            role=user_def["role"],
            name=user_def["name"],
            password_hash=get_password_hash(user_def["password"]),
            phone=user_def["phone"],
            officer_badge_id=user_def["officer_badge_id"],
            status="active",
        )
        session.add(user)
        created_users.append(user)

    await session.flush()
    print(f"Created {len(created_users)} users.")
    return created_users


async def seed_reports(session, users: list) -> list:
    """Generate 180 reports distributed across categories."""
    citizen_users = [u for u in users if u.role == "citizen"]
    if not citizen_users:
        print("ERROR: No citizen users found. Cannot create reports.")
        return []

    reports = []
    reports_per_category = 180 // len(CATEGORIES)  # 22-23 each
    remainder = 180 - (reports_per_category * len(CATEGORIES))
    base_time = datetime.utcnow() - timedelta(days=30)

    source_types = ["text"] * 7 + ["screenshot"] * 2 + ["audio"]  # 70% text, 20% screenshot, 10% audio

    report_index = 0
    for cat_idx, category in enumerate(CATEGORIES):
        templates = SCAM_TEMPLATES[category]
        count = reports_per_category + (1 if cat_idx < remainder else 0)

        for i in range(count):
            template_text = random.choice(templates)
            citizen = random.choice(citizen_users)
            city = random.choice(CITIES)
            source_type = random.choice(source_types)
            # Random timestamp over last 30 days
            random_offset = timedelta(
                days=random.randint(0, 29),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            created_at = base_time + random_offset

            report = Report(
                id=uuid.uuid4(),
                user_id=citizen.id,
                source_type=source_type,
                raw_input_ref="seed_data",
                cleaned_text=template_text,
                detected_language="en",
                input_confidence=0.95,
                low_confidence_flag=False,
                status="submitted",
                city=city,
                created_at=created_at,
            )
            session.add(report)
            reports.append(report)
            report_index += 1

            if report_index % 30 == 0:
                print(f"  Seeding report {report_index}/180...")

    await session.flush()
    print(f"Created {len(reports)} reports across {len(CATEGORIES)} categories.")
    return reports


# ============================================================================
# TASK 12.2: RUN PIPELINE AND CREATE CASES
# ============================================================================

async def run_pipelines(reports: list):
    """Run pipeline continuation on each report for scoring and entity extraction."""
    print(f"\nRunning pipeline continuation on {len(reports)} reports...")
    success_count = 0
    error_count = 0

    for idx, report in enumerate(reports):
        try:
            await run_pipeline_continuation(str(report.id))
            success_count += 1
        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"  WARNING: Pipeline failed for report {report.id}: {e}")

        if (idx + 1) % 20 == 0:
            print(f"  Pipeline progress: {idx + 1}/{len(reports)} (success={success_count}, errors={error_count})")

    print(f"Pipeline complete: {success_count} succeeded, {error_count} failed.")


async def seed_cases(session, reports: list, users: list) -> list:
    """Create 15+ cases grouped by scam category, linking 3-5 reports each."""
    officer_users = [u for u in users if u.role == "officer"]
    if not officer_users:
        print("WARNING: No officer users found. Cases will be unassigned.")

    # Group reports by category (inferred from text content)
    category_reports = {cat: [] for cat in CATEGORIES}
    for report in reports:
        text_lower = (report.cleaned_text or "").lower()
        assigned = False
        for cat in CATEGORIES:
            # Simple keyword matching to bucket reports
            keywords = cat.lower().split()
            if any(kw in text_lower for kw in keywords):
                category_reports[cat].append(report)
                assigned = True
                break
        if not assigned:
            # Fallback: assign to a random category
            random_cat = random.choice(CATEGORIES)
            category_reports[random_cat].append(report)

    cases = []
    case_counter = 1

    for category, cat_reports in category_reports.items():
        if not cat_reports:
            continue

        # Create 2 cases per category (total ~16 cases)
        num_cases_for_cat = min(2, max(1, len(cat_reports) // 4))
        random.shuffle(cat_reports)

        for case_idx in range(num_cases_for_cat):
            case_number = f"CASE-2026-{case_counter:04d}"
            officer = random.choice(officer_users) if officer_users else None
            priority = random.choice(["high", "urgent", "medium"])
            status = random.choice(["open", "in_review", "open", "escalated"])

            case = Case(
                id=uuid.uuid4(),
                case_number=case_number,
                case_type="ring_level" if len(cat_reports) > 5 else "single_report",
                assigned_officer_id=officer.id if officer else None,
                status=status,
                priority=priority,
            )
            session.add(case)
            await session.flush()

            # Link 3-5 reports to this case
            num_to_link = min(random.randint(3, 5), len(cat_reports))
            start_idx = case_idx * num_to_link
            linked_reports = cat_reports[start_idx:start_idx + num_to_link]

            for report in linked_reports:
                case_report = CaseReport(
                    case_id=case.id,
                    report_id=report.id,
                    linked_reason=f"Automated clustering: shared {category} pattern",
                )
                session.add(case_report)

            cases.append(case)
            case_counter += 1

    await session.commit()
    print(f"Created {len(cases)} cases with linked reports.")
    return cases


async def summarize_cases(cases: list):
    """Run investigation agent summarization on each case."""
    print(f"\nSummarizing {len(cases)} cases with investigation agent...")
    for idx, case in enumerate(cases):
        try:
            await investigation_agent.summarize_case(str(case.id))
        except Exception as e:
            print(f"  WARNING: Case summarization failed for {case.case_number}: {e}")

        if (idx + 1) % 5 == 0:
            print(f"  Case summarization progress: {idx + 1}/{len(cases)}")

    print("Case summarization complete.")


# ============================================================================
# TASK 12.3: SEED KNOWLEDGE BASE
# ============================================================================

async def seed_knowledge_base(session, admin_user):
    """Insert 20 knowledge base documents with chunked embeddings."""
    print(f"\nSeeding {len(KNOWLEDGE_DOCS)} knowledge base documents...")

    for idx, doc in enumerate(KNOWLEDGE_DOCS):
        # Check if already exists
        result = await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.title == doc["title"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"  Skipping '{doc['title']}' (already exists)")
            continue

        kb_entry = KnowledgeBase(
            id=uuid.uuid4(),
            source=doc["source"],
            title=doc["title"],
            content=doc["content"],
            source_url=f"https://www.{doc['source'].lower()}.gov.in/advisory",
            added_by=admin_user.id,
            status="indexed",
            version=1,
        )
        session.add(kb_entry)
        await session.flush()

        # Chunk content into 2-3 pieces (~300-500 chars each)
        content = doc["content"]
        chunk_size = 400
        # Split at sentence boundaries near chunk_size
        chunks = []
        start = 0
        while start < len(content):
            end = start + chunk_size
            if end >= len(content):
                chunks.append(content[start:])
                break
            # Find nearest sentence end (period followed by space)
            search_window = content[end - 50:end + 50]
            period_pos = search_window.rfind(". ")
            if period_pos != -1:
                actual_end = end - 50 + period_pos + 2
            else:
                actual_end = end
            chunks.append(content[start:actual_end])
            start = actual_end

        for chunk_idx, chunk_text in enumerate(chunks):
            embedding = await get_embedding(chunk_text)
            chunk_entry = KnowledgeBaseChunk(
                id=uuid.uuid4(),
                knowledge_base_id=kb_entry.id,
                chunk_index=chunk_idx,
                chunk_text=chunk_text,
                embedding=embedding,
                embedding_model_version="local-deterministic-v1",
                token_count=len(chunk_text.split()),
            )
            session.add(chunk_entry)

        if (idx + 1) % 5 == 0:
            print(f"  Knowledge base progress: {idx + 1}/{len(KNOWLEDGE_DOCS)}")

    await session.commit()
    print(f"Knowledge base seeded with {len(KNOWLEDGE_DOCS)} documents.")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main seed function orchestrating all data creation."""
    print("=" * 60)
    print("TRUVIA SEED DATA SCRIPT")
    print("=" * 60)
    print()

    # Ensure database tables exist
    print("Ensuring database schema is ready...")
    await check_and_create_tables()
    print("Database schema verified.\n")

    try:
        # TASK 12.1: Users and Reports
        print("-" * 40)
        print("PHASE 1: Seeding Users and Reports")
        print("-" * 40)

        async with AsyncSessionLocal() as session:
            users = await seed_users(session)
            await session.commit()

        async with AsyncSessionLocal() as session:
            # Re-fetch users for fresh session
            result = await session.execute(select(User))
            users = result.scalars().all()
            reports = await seed_reports(session, users)
            await session.commit()

        print(f"\nPhase 1 complete: {len(users)} users, {len(reports)} reports.\n")

        # TASK 12.2: Pipeline and Cases
        print("-" * 40)
        print("PHASE 2: Running Pipeline & Creating Cases")
        print("-" * 40)

        await run_pipelines(reports)

        async with AsyncSessionLocal() as session:
            # Re-fetch reports for fresh session
            result = await session.execute(select(Report).where(Report.raw_input_ref == "seed_data"))
            reports = result.scalars().all()
            result = await session.execute(select(User))
            users = result.scalars().all()
            cases = await seed_cases(session, reports, users)

        await summarize_cases(cases)

        print(f"\nPhase 2 complete: pipeline ran, {len(cases)} cases created.\n")

        # TASK 12.3: Knowledge Base
        print("-" * 40)
        print("PHASE 3: Seeding Knowledge Base")
        print("-" * 40)

        async with AsyncSessionLocal() as session:
            # Get admin user for knowledge base ownership
            result = await session.execute(
                select(User).where(User.role == "admin")
            )
            admin_user = result.scalars().first()
            if not admin_user:
                print("ERROR: No admin user found. Cannot seed knowledge base.")
            else:
                await seed_knowledge_base(session, admin_user)

        print()
        print("=" * 60)
        print("SEED DATA COMPLETE!")
        print("=" * 60)
        print()
        print("Summary:")
        print(f"  - Users: 6 (1 admin, 2 officers, 3 citizens)")
        print(f"  - Reports: 180 across 8 scam categories")
        print(f"  - Cases: {len(cases)} with linked reports")
        print(f"  - Knowledge Base: {len(KNOWLEDGE_DOCS)} documents")
        print()
        print("You can now start the backend with: python -m uvicorn app.main:app --reload")

    except Exception as e:
        print(f"\nERROR: Seed data failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
