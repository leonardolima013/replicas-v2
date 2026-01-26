import uuid
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer, Text, Float, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.core.database import Base
from backend.core.models import User


class ProjectStatus(str, enum.Enum):
    """Status do projeto de validação"""
    DRAFT = "DRAFT"                         # Em edição pelo usuário
    PENDING_REVIEW = "PENDING_REVIEW"       # Enviado para o Admin, aguardando processamento
    PROCESSING_REPORT = "PROCESSING_REPORT" # Processando relatório em background
    READY_TO_PUBLISH = "READY_TO_PUBLISH"   # Relatório pronto, aguardando publicação
    PROCESSING_ERROR = "PROCESSING_ERROR"   # Erro no processamento
    DONE = "DONE"                           # Publicado no banco de produção


class Project(Base):
    __tablename__ = "validation_projects"

    # Usamos UUID para o ID do projeto, pois vamos usar isso no nome do arquivo físico
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", foreign_keys=[owner_id])

    original_filename = Column(String)
    file_path = Column(String) # Onde está o arquivo .duckdb no disco
    
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    
    # Admin que aprovou/publicou
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    approved_at = Column(DateTime, nullable=True)
    
    s3_url = Column(String, nullable=True) # Preenchido apenas no final
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamento com relatório
    report = relationship("ProjectReport", back_populates="project", uselist=False, cascade="all, delete-orphan")


class ProjectReport(Base):
    """
    Armazena o relatório de análise do projeto para publicação.
    Processado em background via Celery para evitar timeouts.
    """
    __tablename__ = "validation_project_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("validation_projects.id"), unique=True, nullable=False)
    project = relationship("Project", back_populates="report")
    
    # === Métricas do Dataset ===
    total_rows = Column(Integer, default=0)
    columns_found = Column(JSON, default=list)  # Lista de colunas identificadas
    
    # === Métricas de Peças ===
    parts_new = Column(Integer, default=0)        # Peças que serão criadas
    parts_existing = Column(Integer, default=0)   # Peças que já existem no banco
    
    # === Métricas de Marcas ===
    brands_new = Column(Integer, default=0)       # Marcas que serão criadas
    brands_existing = Column(Integer, default=0)  # Marcas que já existem
    brands_to_create = Column(JSON, default=list) # Lista de marcas a criar com ocorrências
    
    # === Progresso do Processamento ===
    processing_status = Column(String, default="pending")  # pending, running, completed, error
    processing_progress = Column(Float, default=0.0)       # 0.0 a 100.0
    processing_step = Column(String, nullable=True)        # Descrição da etapa atual
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    
    # === Erro (se houver) ===
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # === Configuração do Banco de Produção ===
    production_db_status = Column(String, default="unknown")  # connected, error, unknown
    production_db_ready = Column(Boolean, default=False)
    
    # === Celery Task ===
    celery_task_id = Column(String, nullable=True)
    
    # === Timestamps ===
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # === Dados da Publicação (preenchido após DONE) ===
    published_at = Column(DateTime, nullable=True)
    published_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    published_by = relationship("User")
    parts_created = Column(Integer, nullable=True)     # Peças realmente criadas
    parts_updated = Column(Integer, nullable=True)     # Peças realmente atualizadas
    brands_created = Column(Integer, nullable=True)    # Marcas realmente criadas
    publish_time_seconds = Column(Float, nullable=True)


class ImageProcessingTask(Base):
    """
    Armazena o status e resultado do processamento de imagens (lambda_function).
    Processado em background via Celery.
    """
    __tablename__ = "validation_image_processing_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("validation_projects.id"), nullable=False)
    project = relationship("Project")
    
    # === Configuração ===
    environment = Column(String, default="test")  # 'test' ou 'production' (test-lambda ou media)
    
    # === Métricas ===
    total_images = Column(Integer, default=0)
    processed_images = Column(Integer, default=0)
    failed_images = Column(Integer, default=0)
    
    # === Progresso do Processamento ===
    status = Column(String, default="pending")  # pending, running, completed, error
    processing_progress = Column(Float, default=0.0)
    processing_step = Column(String, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    
    # === Resultado ===
    result_data = Column(JSON, nullable=True)  # {sku: {high: [urls], medium: [urls], ...}}
    errors_data = Column(JSON, nullable=True)  # [{filename: str, error: str}]
    
    # === Erro Fatal (se houver) ===
    error_message = Column(Text, nullable=True)
    
    # === Celery Task ===
    celery_task_id = Column(String, nullable=True)
    
    # === Timestamps ===
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class ImageLinkingResult(Base):
    """
    Armazena o resultado da vinculação de imagens ao DuckDB.
    """
    __tablename__ = "validation_image_linking_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("validation_projects.id"), nullable=False)
    project = relationship("Project")
    
    # === Métricas ===
    total_skus = Column(Integer, default=0)
    linked_skus = Column(Integer, default=0)
    not_found_skus = Column(JSON, default=list)  # Lista de SKUs não encontrados no CSV
    
    # === Timestamps ===
    created_at = Column(DateTime, default=datetime.utcnow)