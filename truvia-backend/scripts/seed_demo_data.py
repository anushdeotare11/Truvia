import asyncio
import os
import sys
import uuid
import random
from datetime import datetime, timedelta

# Add parent directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.data.postgres_client import AsyncSessionLocal, check_and_create_tables
from app.models.user import User
from app.models.report import Report, Entity, ReportEntity, ThreatScore, Relationship
from app.models.case import Case, CaseReport
from sqlalchemy import select

# Seed constants
CITIZEN_ID = "00000000-0000-0000-0000-000000000002"
OFFICER_ID = "00000000-0000-0000-0000-000000000003"

SCAM_CATEGORIES = [
    {"category": "Digital Arrest Fraud", "severity": "critical", "template": "Delhi Customs seized courier in your name containing narcotics. Keep WhatsApp video call open. Settle security deposit of INR 95000 immediately to UPI {} or call {}."},
    {"category": "UPI Collect Refund Scam", "severity": "high", "template": "You won lottery of Rs 25,000 from KBC! Scan this QR code or click payment link to claim refund via UPI address {} or contact support at {}."},
    {"category": "KYC Update Phishing", "severity": "moderate", "template": "Your bank account will be suspended today. Please update KYC immediately by visiting website {} or call helpline {}."},
    {"category": "Electricity Bill Threat", "severity": "high", "template": "Your electricity connection will be disconnected tonight. Contact authority immediately at phone {} and transfer pending due to UPI {}."}
]

# Generate sets of sharing entities to ensure graph links
MOCK_PHONES = [f"+9198765{i:05d}" for i in range(12)]
MOCK_UPIS = [f"refundsafe{i}@okaxis" for i in range(10)]
MOCK_DOMAINS = [f"secure-banking-alert{i}.com" for i in range(8)]
MOCK_EMAILS = [f"alert-support{i}@domain.com" for i in range(8)]

async def seed_demo():
    print("Initializing Database and Bootstrapping Tables...")
    await check_and_create_tables()

    async with AsyncSessionLocal() as session:
        # 1. Ensure basic Users exist
        citizen_uuid = uuid.UUID(CITIZEN_ID)
        officer_uuid = uuid.UUID(OFFICER_ID)

        # Check citizen
        cit_check = await session.execute(select(User).where(User.id == citizen_uuid))
        if not cit_check.scalar_one_or_none():
            from app.core.security import get_password_hash
            citizen_user = User(
                id=citizen_uuid,
                role="citizen",
                email="citizen@truvia.org",
                password_hash=get_password_hash("password"),
                name="Rahul Sharma",
                status="active"
            )
            session.add(citizen_user)

        # Check officer
        off_check = await session.execute(select(User).where(User.id == officer_uuid))
        if not off_check.scalar_one_or_none():
            from app.core.security import get_password_hash
            officer_user = User(
                id=officer_uuid,
                role="officer",
                email="officer@truvia.org",
                password_hash=get_password_hash("password"),
                name="Inspector Amit Kumar",
                officer_badge_id="BADGE-9942",
                status="active"
            )
            session.add(officer_user)
            
        await session.commit()
        print("Ensured standard Citizen and Officer user accounts exist.")

        # 2. Pre-create Entities in DB
        entities_pool = []
        for phone in MOCK_PHONES:
            ent = Entity(
                type="phone",
                raw_value=phone,
                normalized_value=phone,
                risk_score=random.randint(45, 95),
                risk_tier="high" if random.random() > 0.4 else "critical",
                occurrence_count=0
            )
            session.add(ent)
            entities_pool.append(ent)

        for upi in MOCK_UPIS:
            ent = Entity(
                type="upi",
                raw_value=upi,
                normalized_value=upi,
                risk_score=random.randint(55, 98),
                risk_tier="critical" if random.random() > 0.3 else "high",
                occurrence_count=0
            )
            session.add(ent)
            entities_pool.append(ent)

        for dom in MOCK_DOMAINS:
            ent = Entity(
                type="domain",
                raw_value=dom,
                normalized_value=dom,
                risk_score=random.randint(35, 80),
                risk_tier="moderate" if random.random() > 0.5 else "high",
                occurrence_count=0
            )
            session.add(ent)
            entities_pool.append(ent)

        for email in MOCK_EMAILS:
            ent = Entity(
                type="email",
                raw_value=email,
                normalized_value=email,
                risk_score=random.randint(30, 75),
                risk_tier="moderate" if random.random() > 0.5 else "high",
                occurrence_count=0
            )
            session.add(ent)
            entities_pool.append(ent)

        await session.flush()
        print(f"Generated a pool of {len(entities_pool)} high-fidelity threat entities.")

        # 3. Create 150 Reports
        reports_created = []
        base_time = datetime.now() - timedelta(days=15)
        
        print("Ingesting 150 complaint reports...")
        for i in range(155):
            cat = random.choice(SCAM_CATEGORIES)
            
            # Select random entities from pool to associate
            report_entities = random.sample(entities_pool, random.randint(2, 3))
            
            # Interpolate raw text
            vals = [e.raw_value for e in report_entities]
            # Ensure we have enough parameters for formatting template
            if len(vals) < 2:
                vals.append("+919999999999")
            raw_text = cat["template"].format(vals[0], vals[1])

            rep = Report(
                user_id=citizen_uuid,
                source_type=random.choice(["text", "screenshot", "audio"]),
                raw_input_ref="demo_files/evidence.bin",
                cleaned_text=raw_text,
                detected_language="en" if random.random() > 0.3 else "hinglish",
                input_confidence=0.95,
                low_confidence_flag=False,
                status="scored",
                created_at=base_time + timedelta(hours=i*2)
            )
            session.add(rep)
            reports_created.append((rep, report_entities, cat))

        await session.flush()

        # 4. Attach Threat Scores and Link Entities
        print("Computing threat scores and entity bindings...")
        for rep, ent_list, cat in reports_created:
            # Threat score
            t_score = ThreatScore(
                report_id=rep.id,
                threat_score=random.randint(40, 95) if cat["severity"] == "high" else random.randint(65, 99) if cat["severity"] == "critical" else random.randint(20, 55),
                severity_band=cat["severity"],
                scam_category=cat["category"],
                confidence_score=0.90,
                reasoning_json={
                    "key_indicators": ["Demands immediate bank transfers", "Posing as law enforcement"],
                    "victim_instructions": ["Disconnect call immediately", "Do not share UPI details"],
                    "risk_explanation": "Extracted text showcases high threat profiles."
                },
                degraded_mode=False,
                model_version="custom-local-fallback",
                is_current=True
            )
            session.add(t_score)

            # ReportEntity joins
            for ent in ent_list:
                re = ReportEntity(
                    report_id=rep.id,
                    entity_id=ent.id,
                    extraction_confidence=0.95
                )
                session.add(re)
                ent.occurrence_count += 1

        await session.flush()

        # 5. Create 4 main fraud cases (Delhi, Mumbai, UPI, KYC Rings) and group reports
        print("Provisioning 5 scam rings/cases...")
        cases_pool = []
        case_types = ["Digital Arrest Ring", "UPI Collect Fraud", "Phishing Campaign", "Bill Redirection Fraud", "Mock Alert Group"]
        for j, ctype in enumerate(case_types):
            new_case = Case(
                case_number=f"CASE-2026-{2040 + j}",
                case_type="ring_level",
                status="under_investigation" if j < 3 else "open",
                priority="high" if j < 2 else "medium",
                assigned_officer_id=officer_uuid if j < 3 else None,
                ai_summary=f"Automated intelligence dossier tracking a high-velocity {ctype} operation. Includes overlapping UPI gateways and burner calls."
            )
            session.add(new_case)
            cases_pool.append(new_case)
            
        await session.flush()

        # Link reports to cases
        for idx, (rep, _, _) in enumerate(reports_created):
            case_target = cases_pool[idx % len(cases_pool)]
            link = CaseReport(
                case_id=case_target.id,
                report_id=rep.id,
                linked_reason="Automated clustering of co-occurring entity nodes"
            )
            session.add(link)

        # 6. Generate pairwise SQL Relationships
        print("Generating pairwise relationships...")
        # To make it simple, we link entities that frequently co-occur in the reports
        for rep, ent_list, _ in reports_created:
            for x in range(len(ent_list)):
                for y in range(x + 1, len(ent_list)):
                    # Check if relationship already exists in DB
                    rel_check = await session.execute(
                        select(Relationship).where(
                            ((Relationship.entity_id_a == ent_list[x].id) & (Relationship.entity_id_b == ent_list[y].id)) |
                            ((Relationship.entity_id_a == ent_list[y].id) & (Relationship.entity_id_b == ent_list[x].id))
                        )
                    )
                    existing_rel = rel_check.scalar_one_or_none()
                    if existing_rel:
                        if isinstance(existing_rel.strength, float):
                            existing_rel.strength += 0.1
                        else:
                            from decimal import Decimal
                            existing_rel.strength += Decimal("0.1")
                    else:
                        new_rel = Relationship(
                            entity_id_a=ent_list[x].id,
                            entity_id_b=ent_list[y].id,
                            relationship_type="co_occurred_in_incident",
                            strength=1.0,
                            evidence_report_id=rep.id
                        )
                        session.add(new_rel)

        await session.commit()
    print("Demo Data Ingestion completed successfully! 150+ reports loaded.")

if __name__ == "__main__":
    asyncio.run(seed_demo())
