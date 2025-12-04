import uuid
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.core.database import Base
from backend.core.models import User

class ProjectStatus(str, enum.Enum):
    DRAFT = "DRAFT"             # Em edição pelo usuário
    PENDING_REVIEW = "PENDING"  # Enviado para o Admin
    DONE = "DONE"               # Publicado no S3

class Project(Base):
    __tablename__ = "validation_projects"

    # Usamos UUID para o ID do projeto, pois vamos usar isso no nome do arquivo físico
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User") # Relacionamento com Usuário

    original_filename = Column(String)
    file_path = Column(String) # Onde está o arquivo .duckdb no disco
    
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    
    s3_url = Column(String, nullable=True) # Preenchido apenas no final
    created_at = Column(DateTime, default=datetime.utcnow)