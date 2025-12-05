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