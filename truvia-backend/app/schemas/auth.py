from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)
    name: str = Field(min_length=2, max_length=100)
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiry in seconds

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    role: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
