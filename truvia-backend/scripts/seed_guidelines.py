import asyncio
import os
import sys
from uuid import uuid4

# Add parent directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.data.postgres_client import AsyncSessionLocal
from app.models.knowledge import KnowledgeBase, KnowledgeBaseChunk
from app.data.vector_client import get_embedding
from sqlalchemy import select

# Mock admin user id to attach to database relations
DUMMY_ADMIN_ID = "00000000-0000-0000-0000-000000000001"

GUIDELINES = [
    {
        "source": "RBI",
        "title": "RBI Charter on Customer Protection and Safe Banking Practices",
        "content": (
            "Reserve Bank of India (RBI) customer protection circular states that a customer "
            "has zero liability in cases of unauthorized electronic transactions where the "
            "security breach or fraud lies in the system of the bank itself. "
            "For third-party breaches where the deficiency lies elsewhere in the system, "
            "the customer will have zero liability if the transaction is reported to the bank "
            "within three working days of receiving the alert. "
            "If reported within four to seven working days, customer liability is capped at 10,000 INR. "
            "Always notify your bank immediately upon receiving suspicious transactional SMS alerts. "
            "Never share card numbers, PINs, CVV, or net banking passwords with anyone claiming "
            "to be an RBI official or bank representative. RBI never requests payments or credentials."
        ),
        "source_url": "https://www.rbi.org.in"
    },
    {
        "source": "CERT-In",
        "title": "CERT-In Advisory on Countering Digital Arrest Scams",
        "content": (
            "CERT-In has observed a surge in 'Digital Arrest' scams targeting citizens. "
            "In this modus operandi, fraudsters pose as officers from Delhi Police, CBI, NCB, or Customs. "
            "They contact victims via Skype or WhatsApp video calls, claiming that a package containing "
            "illegal narcotics, passports, or fake currencies has been seized in the victim's name. "
            "To coerce cooperation, they place the victim under a mock 'Digital Arrest', forcing them "
            "to keep their camera on for hours or days. "
            "Victims are pressured to transfer 'security deposits' to temporary bank accounts to clear their name. "
            "CERT-In advises: Law enforcement agencies never arrest citizens online over video calls. "
            "Do not comply with demands for money. Report such calls immediately to 1930."
        ),
        "source_url": "https://www.cert-in.org.in"
    },
    {
        "source": "MHA",
        "title": "MHA Advisory on UPI Payment Security and QR Code Scams",
        "content": (
            "Ministry of Home Affairs (MHA) cyber safety division warns citizens against QR code frauds. "
            "Scan a QR code ONLY when making a payment, never when receiving money. "
            "Fraudsters send fake screenshots of payment credits and send a QR code claiming it is to "
            "receive a refund or lottery prize. Scanning this QR code and entering your UPI PIN will "
            "debit money from your account. "
            "Additionally, always double-check the recipient name displayed in the UPI app before "
            "confirming any transaction. If you fall victim to financial cyber fraud, call 1930 "
            "within 2 hours to trigger the bank's transaction block mechanism."
        ),
        "source_url": "https://www.cybercrime.gov.in"
    }
]

async def seed():
    print("Starting Ingestion of Public Safety Guidelines...")
    from app.data.postgres_client import check_and_create_tables
    await check_and_create_tables()
    async with AsyncSessionLocal() as session:
        # Check if dummy admin user exists in DB, if not we create a system placeholder user
        from app.models.user import User
        import uuid
        admin_uuid = uuid.UUID(DUMMY_ADMIN_ID)
        
        user_check = await session.execute(select(User).where(User.id == admin_uuid))
        admin_user = user_check.scalar_one_or_none()
        
        if not admin_user:
            print("Creating system admin user record for guidelines ownership...")
            from app.core.security import get_password_hash
            system_admin = User(
                id=admin_uuid,
                role="admin",
                email="system@truvia.org",
                password_hash=get_password_hash("systempassword"),
                name="System Administrator",
                status="active"
            )
            session.add(system_admin)
            await session.commit()
            
        for g in GUIDELINES:
            # Check if title already ingested
            kb_check = await session.execute(select(KnowledgeBase).where(KnowledgeBase.title == g["title"]))
            existing = kb_check.scalar_one_or_none()
            if existing:
                print(f"Skipping {g['title']} (already exists)")
                continue

            kb_entry = KnowledgeBase(
                source=g["source"],
                title=g["title"],
                content=g["content"],
                source_url=g["source_url"],
                added_by=admin_uuid,
                status="indexed",
                version=1
            )
            session.add(kb_entry)
            await session.flush() # Generate ID

            # Split into chunks of ~200 characters for demo granularity
            # In production, use sentence/token boundaries
            chunk_size = 250
            content = g["content"]
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]

            for idx, chunk_text in enumerate(chunks):
                vector = await get_embedding(chunk_text)
                
                # Format to string representation for postgres array
                chunk_entry = KnowledgeBaseChunk(
                    knowledge_base_id=kb_entry.id,
                    chunk_index=idx,
                    chunk_text=chunk_text,
                    embedding=vector,
                    embedding_model_version="custom-local-hash",
                    token_count=len(chunk_text.split())
                )
                session.add(chunk_entry)
                
            print(f"Ingested {len(chunks)} chunks for: {g['title']}")
            
        await session.commit()
    print("Safety Guidelines Ingested Successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
