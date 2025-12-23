"""
Exemplo de endpoint FastAPI usando BrandMappingService.

Este arquivo demonstra como integrar o serviço de mapeamento
em endpoints FastAPI para correção e diagnóstico de marcas.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

from backend.services.data_validation.mapping_service import get_brand_mapping_service


# ==================== SCHEMAS ====================

class BrandCorrectionRequest(BaseModel):
    """Request para correção de uma marca."""
    brand: str


class BrandCorrectionResponse(BaseModel):
    """Response com marca corrigida."""
    original: str
    corrected: str
    was_corrected: bool


class BrandMappingStatsResponse(BaseModel):
    """Estatísticas do serviço de mapeamento."""
    total_mappings: int
    sample_mappings: List[Dict[str, str]]


class BrandValidationRequest(BaseModel):
    """Request para validação em lote."""
    brands: List[str]


class BrandValidationResponse(BaseModel):
    """Response com validação de múltiplas marcas."""
    total_brands: int
    brands_with_mapping: int
    brands_without_mapping: int
    corrections: List[BrandCorrectionResponse]


# ==================== ROUTER ====================

router = APIRouter(
    prefix="/brand-mapping",
    tags=["Brand Mapping"]
)


@router.get("/stats", response_model=BrandMappingStatsResponse)
def get_mapping_stats():
    """
    Retorna estatísticas do serviço de mapeamento de marcas.
    
    Returns:
        BrandMappingStatsResponse: Estatísticas e amostra de mapeamentos
    """
    try:
        service = get_brand_mapping_service()
        df = service.get_mapping_df()
        
        # Pegar amostra dos primeiros 10 mapeamentos
        sample = df.head(10).to_dict('records')
        
        return BrandMappingStatsResponse(
            total_mappings=service.mapping_count,
            sample_mappings=sample
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao carregar estatísticas de mapeamento: {str(e)}"
        )


@router.post("/correct", response_model=BrandCorrectionResponse)
def correct_brand(request: BrandCorrectionRequest):
    """
    Corrige o nome de uma marca usando o mapeamento.
    
    Args:
        request: Request com o nome da marca a corrigir
    
    Returns:
        BrandCorrectionResponse: Nome original e corrigido
    """
    try:
        service = get_brand_mapping_service()
        
        original = request.brand
        corrected = service.get_target_brand(original)
        
        if corrected:
            return BrandCorrectionResponse(
                original=original,
                corrected=corrected,
                was_corrected=True
            )
        else:
            # Retornar a marca normalizada se não houver mapeamento
            normalized = service._normalize_brand(original)
            return BrandCorrectionResponse(
                original=original,
                corrected=normalized,
                was_corrected=False
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao corrigir marca: {str(e)}"
        )


@router.post("/validate", response_model=BrandValidationResponse)
def validate_brands(request: BrandValidationRequest):
    """
    Valida uma lista de marcas e retorna correções.
    
    Args:
        request: Lista de marcas a validar
    
    Returns:
        BrandValidationResponse: Resultado da validação com correções
    """
    try:
        service = get_brand_mapping_service()
        
        corrections = []
        brands_with_mapping = 0
        
        for brand in request.brands:
            corrected = service.get_target_brand(brand)
            
            if corrected:
                brands_with_mapping += 1
                corrections.append(BrandCorrectionResponse(
                    original=brand,
                    corrected=corrected,
                    was_corrected=True
                ))
            else:
                normalized = service._normalize_brand(brand)
                corrections.append(BrandCorrectionResponse(
                    original=brand,
                    corrected=normalized,
                    was_corrected=False
                ))
        
        return BrandValidationResponse(
            total_brands=len(request.brands),
            brands_with_mapping=brands_with_mapping,
            brands_without_mapping=len(request.brands) - brands_with_mapping,
            corrections=corrections
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao validar marcas: {str(e)}"
        )


@router.post("/reload")
def reload_mapping():
    """
    Força o recarregamento do arquivo de mapeamento.
    
    Útil quando o arquivo JSON é atualizado e o cache precisa ser limpo.
    
    Returns:
        dict: Mensagem de sucesso com quantidade de mapeamentos recarregados
    """
    try:
        service = get_brand_mapping_service()
        service.reload_mapping()
        
        return {
            "message": "Mapeamento recarregado com sucesso",
            "total_mappings": service.mapping_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao recarregar mapeamento: {str(e)}"
        )


@router.get("/search/{brand_name}")
def search_brand(brand_name: str):
    """
    Busca o nome correto de uma marca específica.
    
    Args:
        brand_name: Nome da marca a buscar
    
    Returns:
        dict: Nome original, correto e status do mapeamento
    """
    try:
        service = get_brand_mapping_service()
        
        has_mapping = service.has_mapping_for(brand_name)
        corrected = service.get_target_brand(brand_name)
        
        return {
            "original": brand_name,
            "corrected": corrected if corrected else service._normalize_brand(brand_name),
            "has_mapping": has_mapping,
            "was_corrected": has_mapping
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar marca: {str(e)}"
        )


@router.get("/export")
def export_mapping():
    """
    Exporta todos os mapeamentos em formato JSON.
    
    Returns:
        dict: Dicionário completo de mapeamentos
    """
    try:
        service = get_brand_mapping_service()
        mapping = service.get_mapping_dict()
        
        return {
            "total_mappings": len(mapping),
            "mappings": mapping
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao exportar mapeamentos: {str(e)}"
        )


# ==================== EXEMPLO DE INTEGRAÇÃO ====================

def example_usage_in_duck_manager():
    """
    Exemplo de como usar o serviço no DuckManager para corrigir marcas.
    
    Este é um exemplo de código que pode ser adicionado ao duck_manager.py
    """
    from backend.services.data_validation.mapping_service import get_brand_mapping_service
    import duckdb
    
    # Obter serviço de mapeamento
    service = get_brand_mapping_service()
    
    # Obter DataFrame de mapeamento
    mapping_df = service.get_mapping_df()
    
    # Criar conexão DuckDB
    conn = duckdb.connect()
    
    # Registrar DataFrame de mapeamento
    conn.register('brand_mapping', mapping_df)
    
    # Corrigir marcas na tabela raw_data
    query = """
        UPDATE raw_data r
        SET brand = m.target
        FROM brand_mapping m
        WHERE UPPER(TRIM(r.brand)) = m.source
    """
    
    result = conn.execute(query)
    rows_affected = result.fetchone()[0]
    
    print(f"✅ {rows_affected} marcas corrigidas usando mapeamento")
    
    return rows_affected


def example_diagnose_unmapped_brands():
    """
    Exemplo de diagnóstico de marcas sem mapeamento.
    """
    from backend.services.data_validation.mapping_service import get_brand_mapping_service
    import duckdb
    
    service = get_brand_mapping_service()
    conn = duckdb.connect()
    
    # Buscar marcas únicas na base
    brands_query = """
        SELECT DISTINCT UPPER(TRIM(brand)) as brand, COUNT(*) as count
        FROM raw_data
        WHERE brand IS NOT NULL AND brand != ''
        GROUP BY UPPER(TRIM(brand))
        ORDER BY count DESC
    """
    
    df_brands = conn.execute(brands_query).df()
    
    # Adicionar coluna indicando se tem mapeamento
    df_brands['has_mapping'] = df_brands['brand'].apply(service.has_mapping_for)
    df_brands['corrected'] = df_brands['brand'].apply(service.get_target_brand)
    
    # Filtrar as que não têm mapeamento
    unmapped = df_brands[~df_brands['has_mapping']]
    
    print(f"📊 Marcas sem mapeamento: {len(unmapped)}")
    print(unmapped.head(10).to_string(index=False))
    
    return unmapped
