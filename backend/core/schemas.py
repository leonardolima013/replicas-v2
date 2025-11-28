from pydantic import BaseModel
from backend.core.models import UserRole

class UserCreate(BaseModel):
    usuario: str
    password: str
    role: UserRole = UserRole.DEV

class UserResponse(BaseModel):
    id: int
    usuario: str
    is_active: bool
    role: UserRole
    
    class Config:
        from_attributes = True