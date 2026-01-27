"""
Schemas Pydantic para endpoints de publicação de dados validados.
Autor: Sistema de Validação de Dados
Versão: 1.0
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class FieldUpdateMode(str, Enum):
    """Modo de atualização de campo para peças existentes"""
    FORCE_OVERRIDE = "force_override"    # Sempre substitui o valor
    CONCATENATE = "concatenate"          # Concatena com valor existente
    UPDATE_IF_EMPTY = "update_if_empty"  # Atualiza apenas se estiver vazio/NULL


class ImageUpdateMode(str, Enum):
    """Modo de atualização de imagens para peças existentes"""
    IGNORE = "ignore"                    # Nenhuma imagem é adicionada
    CONCATENATE = "concatenate"          # Adiciona imagens para novas e existentes
    ADD_IF_EMPTY = "add_if_empty"        # Adiciona apenas se a peça não tiver imagens


# ============================================================================
# SCHEMAS DE CONFIGURAÇÃO
# ============================================================================

class FieldConfiguration(BaseModel):
    """Configuração de um campo específico para atualização"""
    field_name: str = Field(..., description="Nome do campo")
    mode: FieldUpdateMode = Field(..., description="Modo de atualização")


class PublishConfiguration(BaseModel):
    """Configuração completa para publicação de dados"""
    force_override: List[str] = Field(default=[], description="Campos que sempre substituem o valor atual")
    concatenate: List[str] = Field(default=[], description="Campos que concatenam com valor existente")
    update_if_empty: List[str] = Field(default=[], description="Campos que atualizam apenas se vazios")
    image_mode: str = Field(default="concatenate", description="Modo de atualização de imagens: ignore, concatenate, add_if_empty")
    
    class Config:
        json_schema_extra = {
            "example": {
                "force_override": ["name", "ncm"],
                "concatenate": ["notes", "application"],
                "update_if_empty": ["barcode", "gross_weight", "net_weight"],
                "image_mode": "concatenate"
            }
        }


# ============================================================================
# SCHEMAS DE PREVIEW (antes da publicação)
# ============================================================================

class BrandToCreate(BaseModel):
    """Brand que será criada durante a publicação"""
    brand_name: str = Field(..., description="Nome da brand")
    occurrences: int = Field(..., description="Quantidade de peças com esta brand")


class PartPreviewSummary(BaseModel):
    """Resumo de uma peça para preview"""
    search_ref: str
    brand: str
    name: Optional[str] = None
    status: str = Field(..., description="'new' ou 'existing'")


class SimilarityPreview(BaseModel):
    """Preview de processamento de similaridades"""
    total_rows_with_similarity: int = Field(0, description="Total de linhas com coluna similarity preenchida")
    unique_similarity_groups: int = Field(0, description="Grupos únicos de similaridade")


class PublishPreviewResponse(BaseModel):
    """Resposta do endpoint de preview de publicação"""
    project_id: str
    
    # Contagens principais
    total_rows: int = Field(..., description="Total de linhas a processar")
    parts_new: int = Field(..., description="Peças novas que serão inseridas")
    parts_existing: int = Field(..., description="Peças existentes que podem ser atualizadas")
    
    # Brands
    brands_existing: int = Field(..., description="Brands já existentes no banco")
    brands_to_create: int = Field(..., description="Brands que serão criadas")
    brands_to_create_list: List[BrandToCreate] = Field(default=[], description="Lista de brands a criar")
    
    # Campos disponíveis para configuração
    available_fields: List[str] = Field(
        default=["name", "ncm", "barcode", "gross_weight", "net_weight", 
                 "width", "depth", "height", "notes", "application"],
        description="Campos disponíveis para configuração de atualização"
    )
    
    # Similaridades (opcional)
    similarity: Optional[SimilarityPreview] = None
    
    # Status da conexão com produção
    production_db_status: str = Field(..., description="Status da conexão com banco de produção")
    
    # Avisos e bloqueadores
    warnings: List[str] = Field(default=[], description="Avisos sobre a publicação")
    blockers: List[str] = Field(default=[], description="Problemas que impedem a publicação")
    
    can_publish: bool = Field(..., description="Se a publicação pode ser executada")


# ============================================================================
# SCHEMAS DE EXECUÇÃO DA PUBLICAÇÃO
# ============================================================================

class PublishRequest(BaseModel):
    """Request para executar publicação"""
    configuration: PublishConfiguration = Field(
        default_factory=PublishConfiguration,
        description="Configuração de campos para atualização"
    )
    author_id: Optional[int] = Field(None, description="ID do autor (opcional, usa o usuário logado)")
    current_owner_id: Optional[int] = Field(None, description="ID do fornecedor das informações (opcional)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "configuration": {
                    "force_override": ["name"],
                    "concatenate": ["notes"],
                    "update_if_empty": ["ncm", "barcode", "gross_weight"]
                }
            }
        }


class PublishProgressUpdate(BaseModel):
    """Atualização de progresso da publicação (para WebSocket/SSE futuro)"""
    phase: str = Field(..., description="Fase atual do processo")
    phase_number: int = Field(..., description="Número da fase (1-8)")
    total_phases: int = Field(8, description="Total de fases")
    message: str = Field(..., description="Mensagem de progresso")
    percentage: float = Field(..., description="Percentual de conclusão (0-100)")


class PublishResult(BaseModel):
    """Resultado detalhado da publicação"""
    success: bool
    project_id: str
    
    # Métricas de processamento
    total_rows_processed: int = Field(..., description="Total de linhas processadas")
    invalid_records_skipped: int = Field(0, description="Registros inválidos ignorados")
    
    # Brands e Manufacturers
    manufacturers_created: int = Field(0, description="Manufacturers criados")
    brands_created: int = Field(0, description="Brands criadas")
    
    # Peças
    parts_inserted: int = Field(0, description="Peças novas inseridas")
    parts_updated: int = Field(0, description="Peças existentes atualizadas")
    parts_skipped: int = Field(0, description="Peças existentes sem alterações")
    fields_updated: int = Field(0, description="Total de campos atualizados")
    
    # Activities
    activities_created: int = Field(0, description="Registros de activity criados")
    
    # Similaridades (opcional)
    similarity_groups_created: int = Field(0, description="Grupos de similaridade criados")
    similarity_groups_merged: int = Field(0, description="Grupos de similaridade mesclados")
    similarity_parts_updated: int = Field(0, description="Peças com similaridade atualizada")
    
    # Assets de imagens
    assets_created: int = Field(0, description="Registros de asset_asset criados")
    part_images_created: int = Field(0, description="Vínculos catalog_part_images criados")
    skipped_incomplete_images: List[str] = Field(default=[], description="SKUs com imagens incompletas (faltando variantes)")
    skipped_existing_images: int = Field(0, description="Peças ignoradas por já possuírem imagens (modo add_if_empty)")
    
    # Tempo de execução
    execution_time_seconds: float = Field(..., description="Tempo de execução em segundos")
    
    # Mensagens
    message: str = Field(..., description="Mensagem principal do resultado")
    warnings: List[str] = Field(default=[], description="Avisos durante a execução")
    errors: List[str] = Field(default=[], description="Erros que ocorreram (se success=False)")


class PublishResponse(BaseModel):
    """Resposta completa do endpoint de publicação"""
    result: PublishResult
    project_status: str = Field(..., description="Novo status do projeto após publicação")
    duckdb_deleted: bool = Field(..., description="Se o arquivo DuckDB foi deletado")


# ============================================================================
# SCHEMAS AUXILIARES
# ============================================================================

class ProductionDBStatus(BaseModel):
    """Status da conexão com banco de produção"""
    status: str = Field(..., description="'connected' ou 'error'")
    host: str
    database: str
    postgres_version: Optional[str] = None
    existing_tables: List[str] = Field(default=[])
    missing_tables: List[str] = Field(default=[])
    ready: bool = Field(..., description="Se o banco está pronto para receber dados")
    error: Optional[str] = None


class AvailableFieldsResponse(BaseModel):
    """Lista de campos disponíveis para configuração"""
    system_fields: List[str] = Field(
        default=[
            'id', 'manufacturer_ref', 'search_ref', 'brand_id', 
            'created', 'updated', 'status', 'has_stock', 'ready_to_p4m',
            'p4m_quantity_by_states', 'p4m_status', 'p4m_logs',
            'manually_categorized', 'from_aux_db', 'similarity_id'
        ],
        description="Campos de sistema que nunca são atualizados"
    )
    available_fields: List[str] = Field(
        default=[
            'name', 'ncm', 'barcode', 'gross_weight', 'net_weight',
            'width', 'depth', 'height', 'notes', 'application'
        ],
        description="Campos disponíveis para configuração de atualização"
    )
    field_descriptions: Dict[str, str] = Field(
        default={
            'name': 'Nome da peça',
            'ncm': 'Código NCM (formato XXXX.XX.XX)',
            'barcode': 'Código de barras',
            'gross_weight': 'Peso bruto (kg)',
            'net_weight': 'Peso líquido (kg)',
            'width': 'Largura (cm)',
            'depth': 'Profundidade/Comprimento (cm)',
            'height': 'Altura (cm)',
            'notes': 'Especificações/Observações',
            'application': 'Aplicação da peça'
        },
        description="Descrições dos campos"
    )
