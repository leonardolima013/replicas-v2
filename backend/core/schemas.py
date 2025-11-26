from pydantic import BaseModel, EmailStr
from backend.core.models import UserRole

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.DEV

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    role: UserRole
    
    class Config:
        from_attributes = True