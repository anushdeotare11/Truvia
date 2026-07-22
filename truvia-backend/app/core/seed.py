"""
Startup demo-user seeding.

On a fresh deploy the database is empty, so nobody can log in. This module
idempotently ensures a small set of demo login accounts exists (one per role)
using the shared password "password". It is safe to run on every startup: each
account is only created if neither its id nor its email already exists, which
avoids unique-email collisions and duplicate inserts.
"""

import uuid

from sqlalchemy import select

from app.core.security import get_password_hash
from app.data.postgres_client import AsyncSessionLocal
from app.models.user import User
from app.core.logging import logger

# Demo accounts to ensure. Only keys that are valid User columns are used when
# constructing the row (see _valid_user_kwargs), so this stays robust if the
# model changes.
_DEMO_USERS = [
    # Original accounts (password: "password")
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "role": "citizen",
        "email": "citizen@truvia.org",
        "name": "Rahul Sharma",
        "_password": "password",
    },
    {
        "id": "00000000-0000-0000-0000-000000000003",
        "role": "officer",
        "email": "officer@truvia.org",
        "name": "Inspector Amit Kumar",
        "officer_badge_id": "BADGE-9942",
        "_password": "password",
    },
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "role": "admin",
        "email": "admin@truvia.org",
        "name": "Truvia Admin",
        "_password": "password",
    },
    # Friendly demo accounts with easy-to-remember credentials
    {
        "id": "00000000-0000-0000-0000-000000000012",
        "role": "citizen",
        "email": "citizen1@truvia.ai",
        "name": "Demo Citizen",
        "_password": "citizen123",
    },
    {
        "id": "00000000-0000-0000-0000-000000000013",
        "role": "officer",
        "email": "officer1@truvia.ai",
        "name": "Demo Officer",
        "officer_badge_id": "BADGE-0001",
        "_password": "officer123",
    },
    {
        "id": "00000000-0000-0000-0000-000000000011",
        "role": "admin",
        "email": "admin@truvia.ai",
        "name": "Demo Admin",
        "_password": "admin123",
    },
]


def _valid_user_kwargs(spec: dict, password_hash: str) -> dict:
    """Build kwargs limited to columns that actually exist on the User model."""
    columns = {c.name for c in User.__table__.columns}
    kwargs = {}
    for key, value in spec.items():
        if key == "id":
            # Store as a UUID object to match the UUID(as_uuid=True) column.
            kwargs["id"] = uuid.UUID(value)
        elif key.startswith("_"):
            # Skip internal keys like _password
            continue
        elif key in columns:
            kwargs[key] = value
    if "password_hash" in columns:
        kwargs["password_hash"] = password_hash
    return kwargs


async def ensure_demo_users() -> int:
    """
    Idempotently ensure the demo login accounts exist.

    For each demo account, checks by id AND by email; if either already exists
    the account is skipped. Commits once and returns the number of accounts
    created. Any database failure propagates to the caller.
    """
    created = 0

    async with AsyncSessionLocal() as session:
        for spec in _DEMO_USERS:
            user_id = uuid.UUID(spec["id"])
            email = spec["email"]
            pw = spec.get("_password", "password")

            existing = await session.execute(
                select(User).where((User.id == user_id) | (User.email == email))
            )
            if existing.scalars().first() is not None:
                continue

            password_hash = get_password_hash(pw)
            session.add(User(**_valid_user_kwargs(spec, password_hash)))
            created += 1

        if created:
            await session.commit()

    logger.info(f"Demo user seeding complete: {created} account(s) created.")
    return created

