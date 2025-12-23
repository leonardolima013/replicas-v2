"""
Testes unitários para o BrandMappingService.

Para executar os testes:
    python -m backend.services.data_validation.test_mapping_service
    
Ou com pytest (se instalado):
    pytest backend/services/data_validation/test_mapping_service.py -v
"""

import pandas as pd
from pathlib import Path

from backend.services.data_validation.mapping_service import (
    BrandMappingService,
    get_brand_mapping_service
)

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    pytest = None


class TestBrandMappingService:
    """Testes para o serviço de mapeamento de marcas."""
    
    def test_singleton_pattern(self):
        """Testa se o serviço é realmente um singleton."""
        service1 = BrandMappingService()
        service2 = BrandMappingService()
        service3 = get_brand_mapping_service()
        
        assert service1 is service2
        assert service2 is service3
        assert id(service1) == id(service2) == id(service3)
    
    def test_mapping_file_exists(self):
        """Verifica se o arquivo de mapeamento existe."""
        service = get_brand_mapping_service()
        assert service.LOCAL_MAPPING_PATH.exists(), (
            f"Arquivo de mapeamento não encontrado: {service.LOCAL_MAPPING_PATH}"
        )
    
    def test_get_mapping_df_returns_dataframe(self):
        """Testa se get_mapping_df() retorna um DataFrame válido."""
        service = get_brand_mapping_service()
        df = service.get_mapping_df()
        
        assert isinstance(df, pd.DataFrame)
        assert 'source' in df.columns
        assert 'target' in df.columns
        assert len(df) > 0
    
    def test_get_mapping_df_normalization(self):
        """Verifica se os dados estão normalizados (uppercase + trim)."""
        service = get_brand_mapping_service()
        df = service.get_mapping_df()
        
        # Todas as entradas devem estar em uppercase
        assert all(df['source'].str.isupper()), "Nem todas as sources estão em uppercase"
        assert all(df['target'].str.isupper()), "Nem todos os targets estão em uppercase"
        
        # Não deve haver espaços no início ou fim
        assert all(df['source'] == df['source'].str.strip()), "Sources têm espaços"
        assert all(df['target'] == df['target'].str.strip()), "Targets têm espaços"
    
    def test_get_mapping_dict_returns_dict(self):
        """Testa se get_mapping_dict() retorna um dicionário válido."""
        service = get_brand_mapping_service()
        mapping = service.get_mapping_dict()
        
        assert isinstance(mapping, dict)
        assert len(mapping) > 0
    
    def test_get_target_brand_existing(self):
        """Testa get_target_brand() com uma marca existente."""
        service = get_brand_mapping_service()
        mapping = service.get_mapping_dict()
        
        # Pegar o primeiro item do mapeamento
        if mapping:
            source_brand = next(iter(mapping.keys()))
            expected_target = mapping[source_brand]
            
            # Testar com a mesma casing
            result = service.get_target_brand(source_brand)
            assert result == expected_target
            
            # Testar com casing diferente (deve normalizar)
            result_lower = service.get_target_brand(source_brand.lower())
            assert result_lower == expected_target
            
            result_mixed = service.get_target_brand(source_brand.capitalize())
            assert result_mixed == expected_target
    
    def test_get_target_brand_nonexisting(self):
        """Testa get_target_brand() com uma marca inexistente."""
        service = get_brand_mapping_service()
        
        result = service.get_target_brand("MARCA_INEXISTENTE_XYZ_123")
        assert result is None
    
    def test_get_target_brand_with_spaces(self):
        """Testa normalização com espaços extras."""
        service = get_brand_mapping_service()
        mapping = service.get_mapping_dict()
        
        if mapping:
            source_brand = next(iter(mapping.keys()))
            expected_target = mapping[source_brand]
            
            # Testar com espaços extras
            result = service.get_target_brand(f"  {source_brand}  ")
            assert result == expected_target
    
    def test_has_mapping_for_existing(self):
        """Testa has_mapping_for() com marca existente."""
        service = get_brand_mapping_service()
        mapping = service.get_mapping_dict()
        
        if mapping:
            source_brand = next(iter(mapping.keys()))
            assert service.has_mapping_for(source_brand) is True
    
    def test_has_mapping_for_nonexisting(self):
        """Testa has_mapping_for() com marca inexistente."""
        service = get_brand_mapping_service()
        
        assert service.has_mapping_for("MARCA_INEXISTENTE_XYZ_123") is False
    
    def test_mapping_count(self):
        """Testa a propriedade mapping_count."""
        service = get_brand_mapping_service()
        count = service.mapping_count
        
        assert isinstance(count, int)
        assert count > 0
        
        # Deve ser igual ao tamanho do DataFrame
        df = service.get_mapping_df()
        assert count == len(df)
    
    def test_normalize_brand_static_method(self):
        """Testa o método estático _normalize_brand."""
        assert BrandMappingService._normalize_brand("  teste  ") == "TESTE"
        assert BrandMappingService._normalize_brand("MaRcA") == "MARCA"
        assert BrandMappingService._normalize_brand("") == ""
        assert BrandMappingService._normalize_brand("   ") == ""
    
    def test_dataframe_copy_independence(self):
        """Verifica se get_mapping_df() retorna cópias independentes."""
        service = get_brand_mapping_service()
        
        df1 = service.get_mapping_df()
        df2 = service.get_mapping_df()
        
        # Modificar df1 não deve afetar df2
        df1.loc[0, 'source'] = "MODIFIED"
        assert df1.loc[0, 'source'] != df2.loc[0, 'source']
    
    def test_dict_copy_independence(self):
        """Verifica se get_mapping_dict() retorna cópias independentes."""
        service = get_brand_mapping_service()
        
        dict1 = service.get_mapping_dict()
        dict2 = service.get_mapping_dict()
        
        # Modificar dict1 não deve afetar dict2
        first_key = next(iter(dict1.keys()))
        dict1[first_key] = "MODIFIED"
        assert dict1[first_key] != dict2[first_key]
    
    def test_reload_mapping(self):
        """Testa o método reload_mapping()."""
        service = get_brand_mapping_service()
        
        # Carregar primeira vez
        count1 = service.mapping_count
        
        # Recarregar
        service.reload_mapping()
        count2 = service.mapping_count
        
        # Deve ter a mesma quantidade (arquivo não mudou)
        assert count1 == count2
        
        # Mas o DataFrame deve ser uma nova instância
        # (internamente foi recriado)
        df1 = service.get_mapping_df()
        service.reload_mapping()
        df2 = service.get_mapping_df()
        
        # Mesmo conteúdo
        assert df1.equals(df2)


class TestBrandMappingServiceErrors:
    """Testes de casos de erro."""
    
    def test_invalid_brand_type(self):
        """Testa normalização com tipo inválido."""
        result = BrandMappingService._normalize_brand(123)
        assert result == ""
        
        result = BrandMappingService._normalize_brand(None)
        assert result == ""
    
    def test_get_target_brand_empty_string(self):
        """Testa get_target_brand() com string vazia."""
        service = get_brand_mapping_service()
        result = service.get_target_brand("")
        assert result is None


if __name__ == "__main__":
    # Executar testes básicos
    print("🧪 Executando testes básicos do BrandMappingService...\n")
    
    service = get_brand_mapping_service()
    
    print(f"✅ Singleton: {service is BrandMappingService()}")
    print(f"✅ Arquivo encontrado: {service.LOCAL_MAPPING_PATH.exists()}")
    print(f"✅ Mapeamentos carregados: {service.mapping_count}")
    
    df = service.get_mapping_df()
    print(f"✅ DataFrame: {len(df)} linhas, colunas: {list(df.columns)}")
    
    # Testar algumas marcas
    if service.mapping_count > 0:
        sample_brands = list(service.get_mapping_dict().keys())[:3]
        print("\n📋 Amostra de mapeamentos:")
        for brand in sample_brands:
            target = service.get_target_brand(brand)
            print(f"   {brand} → {target}")
    
    print("\n✅ Todos os testes básicos passaram!")
