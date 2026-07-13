from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.data.postgres_client import get_db
from app.models.user import User, Session as UserSession
from app.schemas.auth import UserRegister, UserLogin, Token, UserOut
from app.core import security
from app.api import deps
from app.config import settings
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger("truvia.auth")
router = APIRouter()

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists"
        )
        
    hashed_password = security.get_password_hash(user_in.password)
    
    new_user = User(
        email=user_in.email,
        password_hash=hashed_password,
        name=user_in.name,
        phone=user_in.phone,
        role="citizen",  # Self-registration only maps to citizen
        status="active"
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
async def login(
    response: Response,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()
    
    if not user or not security.verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    if user.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended"
        )

    # Issue tokens
    access_token = security.create_access_token(subject=user.id, role=user.role)
    refresh_token = security.create_refresh_token(subject=user.id)
    
    # Store hashed refresh token in sessions table
    hashed_refresh = hash_token(refresh_token)
    session_expiry = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_session = UserSession(
        user_id=user.id,
        refresh_token_hash=hashed_refresh,
        expires_at=session_expiry,
        device_label="Web Client"
    )
    db.add(db_session)
    await db.commit()

    # Set HTTP-only cookie for refresh token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENV != "dev",
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    )

    return Token(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing"
        )
        
    try:
        payload = security.decode_token(refresh_token)
        user_id_str = payload.get("sub")
        token_type = payload.get("type")
        
        if user_id_str is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid/expired refresh token")

    # Verify session exists and is not revoked
    hashed_refresh = hash_token(refresh_token)
    session_result = await db.execute(
        select(UserSession)
        .where(UserSession.refresh_token_hash == hashed_refresh)
        .where(UserSession.revoked_at == None)
        .where(UserSession.expires_at > datetime.utcnow())
    )
    db_session = session_result.scalar_one_or_none()
    
    if not db_session:
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    # Fetch user
    user_result = await db.execute(select(User).where(User.id == db_session.user_id))
    user = user_result.scalar_one_or_none()
    
    if not user or user.status == "suspended":
        raise HTTPException(status_code=401, detail="User account is invalid or suspended")

    # Issue new access token (keep using same refresh token)
    new_access_token = security.create_access_token(subject=user.id, role=user.role)
    
    return Token(
        access_token=new_access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if refresh_token:
        hashed_refresh = hash_token(refresh_token)
        # Revoke session in database
        await db.execute(
            update(UserSession)
            .where(UserSession.refresh_token_hash == hashed_refresh)
            .values(revoked_at=datetime.utcnow())
        )
        await db.commit()
        
    response.delete_cookie("refresh_token")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(deps.get_current_user)):
    return current_user

@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return users

@router.post("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    import uuid
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user UUID format")
    
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_status = payload.get("status")
    if new_status not in ["active", "suspended"]:
        raise HTTPException(status_code=400, detail="Invalid status option")
        
    user.status = new_status
    await db.commit()
    return {"status": "success", "message": f"User status updated to {new_status}"}

@router.post("/users/invite")
async def invite_officer(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    email = payload.get("email")
    # Check if already exists
    existing_result = await db.execute(select(User).where(User.email == email))
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists")
        
    from app.core.security import get_password_hash
    import uuid
    import random
    new_user = User(
        id=uuid.uuid4(),
        role=payload.get("role", "officer"),
        email=email,
        password_hash=get_password_hash("password123"),
        name=payload.get("name"),
        officer_badge_id=f"BADGE-{random.randint(1000, 9999)}" if payload.get("role") == "officer" else None,
        status="active"
    )
    db.add(new_user)
    await db.commit()
    return {"status": "success", "message": f"User {new_user.name} invited successfully"}
