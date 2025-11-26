from sqlalchemy import Boolean, Column, Integer, String, Enum as SQLEnum
from backend.core.database import Base
import enum

class UserRole(str, enum.Enum):
    DEV = "dev"
    ADM = "adm"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="dev", nullable=False)