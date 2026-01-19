from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Any, Dict

# --- RESPOSTAS JÁ EXISTENTES (Upload) ---
class ProjectResponse(BaseModel):
    id: str
    original_filename: str
    status: str
    created_at: datetime
    owner_username: Optional[str] = None  # Nome do usuário que criou o projeto

    class Config:
        from_attributes = True

# --- NOVAS ESTRUTURAS PARA O PREVIEW ---

class PreviewResponse(BaseModel):
    total_rows: int             # Total de linhas no ficheiro (ex: 1.000.000)
    page: int                   # Página atual (ex: 1)
    page_size: int              # Tamanho da página (ex: 50)
    columns: List[str]          # Nomes das colunas ["id", "nome", "preco"]
    rows: List[Dict[str, Any]]  # Os dados em si [{"id": 1...}, {"id": 2...}]

class QueryRequest(BaseModel):
    sql: str                    # O SQL que o utilizador digita para limpar dados

class QueryResponse(BaseModel):
    status: str
    rows_affected: Optional[int] = 0
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

# --- SCHEMAS PARA ANÁLISE E RENOMEAÇÃO DE COLUNAS ---

class ColumnsAnalysisResponse(BaseModel):
    missing: List[str]      # Colunas obrigatórias que faltam
    extra: List[str]        # Colunas não reconhecidas (nem obrigatórias nem opcionais)
    present: List[str]      # Colunas presentes na tabela
    required: List[str]     # Lista de colunas obrigatórias
    optional: List[str]     # Lista de colunas opcionais

class RenameColumnRequest(BaseModel):
    old_name: str           # Nome atual da coluna
    new_name: str           # Novo nome da coluna

class RenameColumnResponse(BaseModel):
    message: str
    old_name: str
    new_name: str

# --- SCHEMAS PARA FASE 2: DATA HYGIENE ---

class TreatmentDiagnosisResponse(BaseModel):
    # Diagnósticos básicos
    uppercase_issues: List[str]      # Colunas de string com valores não-uppercase
    null_string_issues: List[str]    # Colunas de string com valores nulos ou 'nan'
    null_numeric_issues: List[str]   # Colunas numéricas com valores nulos
    
    # Diagnósticos avançados (Fase 2.1)
    brand_issues: int = 0            # Contagem de problemas em brand
    ncm_issues: int = 0              # Contagem de problemas em ncm
    barcode_issues: int = 0          # Contagem de problemas em barcode
    weight_issues: int = 0           # Contagem de problemas em pesos (gross/net)
    dimension_issues: int = 0        # Contagem de problemas em dimensões
    search_ref_issues: int = 0       # Contagem de problemas em search_ref
    manufacturer_ref_issues: int = 0 # Contagem de problemas em manufacturer_ref

class TreatmentFixResponse(BaseModel):
    message: str
    columns_affected: List[str]
    rows_affected: int

# --- SCHEMAS PARA ANÁLISE DE DUPLICADAS ---

class DuplicateGroup(BaseModel):
    search_ref: str
    brand: str
    count: int              # Número de ocorrências
    rows: List[Dict[str, Any]]  # Todas as linhas duplicadas deste grupo

class DuplicatesAnalysisResponse(BaseModel):
    total_duplicates: int           # Total de linhas duplicadas
    duplicate_groups: int           # Número de grupos de duplicadas
    duplicates: List[DuplicateGroup]  # Lista de grupos duplicados

class DuplicatesDiagnosisResponse(BaseModel):
    total_duplicates: int           # Total de linhas que serão removidas
    preview: List[Dict[str, Any]]   # Preview paginado das duplicatas
    columns_used: List[str]         # Colunas usadas para identificar duplicatas
    page: int                       # Página atual
    page_size: int                  # Tamanho da página
    total_pages: int                # Total de páginas

# --- SCHEMAS PARA MAPEAMENTO DE MARCAS ---

class BrandCorrection(BaseModel):
    original_brand: str             # Marca original (incorreta)
    corrected_brand: str            # Marca corrigida (normalizada)
    occurrences: int                # Número de ocorrências

class UnknownBrand(BaseModel):
    brand: str                      # Nome da marca desconhecida
    occurrences: int                # Número de ocorrências

class BrandAnalysisResponse(BaseModel):
    total_rows: int                 # Total de linhas na tabela
    mapped_count: int               # Linhas com marcas que serão corrigidas
    unknown_count: int              # Linhas com marcas desconhecidas (não no mapeamento)
    top_corrections: List[BrandCorrection]  # Top 5 correções que serão aplicadas
    unknown_brands: List[UnknownBrand]      # Lista de marcas desconhecidas

class BrandApplicationResponse(BaseModel):
    message: str                    # Mensagem de sucesso
    rows_affected: int              # Número de linhas afetadas pelo UPDATE

# --- SCHEMAS PARA RELATÓRIO DE QUALIDADE (ADMIN) ---

class StructuralQuality(BaseModel):
    required_columns_present: int
    required_columns_total: int
    extra_columns_mapped: int
    missing_columns: int

class DataQualityMetrics(BaseModel):
    completeness_pct: float
    total_rows: int
    uppercase_issues: int
    null_string_issues: int
    null_numeric_issues: int
    brand_issues: int
    ncm_issues: int
    barcode_issues: int
    weight_issues: int
    dimension_issues: int
    search_ref_issues: int
    manufacturer_ref_issues: int

class BrandQualityMetrics(BaseModel):
    total_rows: int
    normalized_count: int
    normalized_pct: float
    unknown_count: int
    unknown_pct: float
    top_unknown_brands: List[UnknownBrand]

class DuplicatesQuality(BaseModel):
    found: int
    removed: int

# --- SCHEMAS PARA VALIDAÇÃO DE SIMILARIDADES ---

class SimilarityIssue(BaseModel):
    row_number: int
    search_ref: Optional[str]
    brand: Optional[str]
    similarity_value: Optional[Any]
    issues: List[str]  # Lista de problemas encontrados

class SimilaritiesDiagnosisResponse(BaseModel):
    column_exists: bool
    format_issues: int              # Problemas de formato JSON
    search_ref_issues: int          # search_ref com espaços/caracteres especiais
    brand_issues: int               # brand em minúsculas
    invalid_refs: int               # search_ref não existe no projeto
    invalid_brands: int             # brand não está no mapeamento
    empty_list_issues: int          # Valores NULL ao invés de []
    total_issues: int               # Total de problemas
    preview: List[SimilarityIssue]  # Preview paginado
    page: int
    page_size: int
    total_pages: int

class TopSearchRef(BaseModel):
    search_ref: str
    count: int

class TopBrand(BaseModel):
    brand: str
    count: int

class SimilarityDistribution(BaseModel):
    similarity_count: int
    row_count: int

class SimilaritiesStatisticsResponse(BaseModel):
    total_rows: int
    rows_with_similarities: int
    percentage_with_similarities: float
    total_similarities: int
    avg_similarities_per_row: float
    top_search_refs: List[TopSearchRef]
    top_brands: List[TopBrand]
    distribution: List[SimilarityDistribution]
    invalid_search_refs: List[str]  # search_refs que não existem no projeto
    invalid_brands: List[str]       # brands que não estão no mapeamento

class StatisticsQuality(BaseModel):
    weight_correlation: Optional[float]
    physical_violations: int
    negative_values: int

class QualityReportResponse(BaseModel):
    project_id: str
    overall_quality_score: float  # 0-100
    structural: StructuralQuality
    data_quality: DataQualityMetrics
    brands: BrandQualityMetrics
    duplicates: DuplicatesQuality
    statistics: StatisticsQuality
    warnings: List[str]
    blockers: List[str]


# --- SCHEMAS PARA PROGRESSO DE PROCESSAMENTO ---

class BrandToCreateSchema(BaseModel):
    brand_name: str
    occurrences: int

class ProjectReportResponse(BaseModel):
    """Resposta do relatório de um projeto"""
    project_id: str
    
    # Métricas do dataset
    total_rows: int = 0
    columns_found: List[str] = []
    
    # Métricas de peças
    parts_new: int = 0
    parts_existing: int = 0
    
    # Métricas de marcas
    brands_new: int = 0
    brands_existing: int = 0
    brands_to_create: List[BrandToCreateSchema] = []
    
    # Status do processamento
    processing_status: str = "pending"  # pending, running, completed, error
    processing_progress: float = 0.0
    processing_step: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    
    # Erro (se houver)
    error_message: Optional[str] = None
    
    # Status do banco de produção
    production_db_status: str = "unknown"
    production_db_ready: bool = False
    
    # Pode publicar?
    can_publish: bool = False
    
    class Config:
        from_attributes = True


class ProjectProgressResponse(BaseModel):
    """Resposta simples do progresso de processamento"""
    project_id: str
    status: str  # project status
    processing_status: str  # pending, running, completed, error
    processing_progress: float
    processing_step: Optional[str] = None
    error_message: Optional[str] = None
    can_retry: bool = False


class ProjectWithReportResponse(BaseModel):
    """Resposta completa do projeto com relatório"""
    id: str
    original_filename: str
    status: str
    created_at: datetime
    owner_username: Optional[str] = None
    
    # Dados de aprovação
    approved_by_username: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    # Relatório (se existir)
    report: Optional[ProjectReportResponse] = None
    
    class Config:
        from_attributes = True


class ValidationHistoryItem(BaseModel):
    """Item do histórico de validações"""
    project_id: str
    original_filename: str
    
    # Quem enviou
    owner_id: int
    owner_username: str
    created_at: datetime
    
    # Quem aprovou/publicou
    published_by_id: Optional[int] = None
    published_by_username: Optional[str] = None
    published_at: Optional[datetime] = None
    
    # Métricas
    total_rows: int = 0
    parts_created: Optional[int] = None
    parts_updated: Optional[int] = None
    brands_created: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    publish_time_seconds: Optional[float] = None


class ValidationHistoryResponse(BaseModel):
    """Resposta do histórico de validações"""
    items: List[ValidationHistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int