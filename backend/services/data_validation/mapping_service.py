"""
Serviço Singleton para Carregamento e Cache de Mapeamento de Marcas.

Este módulo fornece um serviço centralizado para carregar e manter em cache
o mapeamento de marcas (nomes incorretos -> nomes corretos) a partir de um
arquivo JSON, com suporte para S3 e fallback para armazenamento local.
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

import pandas as pd


class BrandMappingService:
    """
    Serviço Singleton para gerenciar o mapeamento de marcas.
    
    Carrega o arquivo JSON de mapeamento uma única vez e mantém em cache,
    evitando leituras repetidas do disco. Suporta carregamento de S3 com
    fallback para arquivo local.
    """
    
    _instance: Optional['BrandMappingService'] = None
    _mapping_df: Optional[pd.DataFrame] = None
    _mapping_dict: Optional[Dict[str, str]] = None
    
    # Configurações do arquivo de mapeamento
    MAPPING_FILENAME = "mapeamento-marcas-invertido.json"
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # Volta para raiz do projeto
    LOCAL_MAPPING_PATH = PROJECT_ROOT / MAPPING_FILENAME
    
    # Configurações S3 (para implementação futura)
    S3_BUCKET: Optional[str] = os.getenv("BRAND_MAPPING_S3_BUCKET")
    S3_KEY: Optional[str] = os.getenv("BRAND_MAPPING_S3_KEY", "mappings/mapeamento-marcas-invertido.json")
    
    def __new__(cls):
        """Implementação Singleton - garante uma única instância."""
        if cls._instance is None:
            cls._instance = super(BrandMappingService, cls).__new__(cls)
        return cls._instance
    
    def get_mapping_df(self) -> pd.DataFrame:
        """
        Retorna o DataFrame de mapeamento de marcas.
        
        O DataFrame possui duas colunas:
        - source: Nome incorreto da marca (normalizado: uppercase + trim)
        - target: Nome correto da marca (normalizado: uppercase + trim)
        
        Returns:
            pd.DataFrame: DataFrame com colunas ['source', 'target']
        
        Raises:
            FileNotFoundError: Se o arquivo de mapeamento não for encontrado
            json.JSONDecodeError: Se o JSON estiver malformado
        """
        if self._mapping_df is None:
            self._load_mapping()
        
        return self._mapping_df.copy()
    
    def get_mapping_dict(self) -> Dict[str, str]:
        """
        Retorna o dicionário de mapeamento de marcas.
        
        Returns:
            Dict[str, str]: Dicionário {source_normalizado: target_normalizado}
        """
        if self._mapping_dict is None:
            self._load_mapping()
        
        return self._mapping_dict.copy()
    
    def _load_mapping(self) -> None:
        """
        Carrega o mapeamento de marcas do arquivo JSON.
        
        Tenta carregar de S3 primeiro (se configurado), com fallback para
        arquivo local. Os dados são normalizados (uppercase + trim) e
        armazenados em cache.
        """
        # Tentar carregar do S3 primeiro (se configurado)
        if self.S3_BUCKET and self.S3_KEY:
            try:
                raw_mapping = self._load_from_s3()
                if raw_mapping:
                    self._process_mapping(raw_mapping)
                    print(f"✅ Mapeamento de marcas carregado do S3: {len(self._mapping_dict)} registros")
                    return
            except Exception as e:
                print(f"⚠️  Falha ao carregar do S3: {e}. Tentando carregar localmente...")
        
        # Fallback: carregar do arquivo local
        raw_mapping = self._load_from_local()
        self._process_mapping(raw_mapping)
        print(f"✅ Mapeamento de marcas carregado localmente: {len(self._mapping_dict)} registros")
    
    def _load_from_s3(self) -> Optional[Dict[str, str]]:
        """
        Carrega o mapeamento de marcas do S3.
        
        Returns:
            Optional[Dict[str, str]]: Dicionário de mapeamento ou None se falhar
        
        Note:
            Implementação futura. Requer boto3 configurado.
        """
        # TODO: Implementar carregamento do S3
        # Exemplo de implementação:
        # import boto3
        # s3 = boto3.client('s3')
        # response = s3.get_object(Bucket=self.S3_BUCKET, Key=self.S3_KEY)
        # content = response['Body'].read().decode('utf-8')
        # return json.loads(content)
        
        pass  # Por enquanto retorna None (fallback para local)
    
    def _load_from_local(self) -> Dict[str, str]:
        """
        Carrega o mapeamento de marcas do arquivo local.
        
        Returns:
            Dict[str, str]: Dicionário de mapeamento {nome_errado: nome_certo}
        
        Raises:
            FileNotFoundError: Se o arquivo não existir
            json.JSONDecodeError: Se o JSON estiver malformado
        """
        if not self.LOCAL_MAPPING_PATH.exists():
            raise FileNotFoundError(
                f"Arquivo de mapeamento não encontrado: {self.LOCAL_MAPPING_PATH}\n"
                f"Certifique-se de que '{self.MAPPING_FILENAME}' existe na raiz do projeto."
            )
        
        with open(self.LOCAL_MAPPING_PATH, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        if not isinstance(mapping_data, dict):
            raise ValueError(
                f"Formato inválido do arquivo de mapeamento. "
                f"Esperado: dict, Recebido: {type(mapping_data).__name__}"
            )
        
        return mapping_data
    
    def _process_mapping(self, raw_mapping: Dict[str, str]) -> None:
        """
        Processa e normaliza o mapeamento de marcas.
        
        Aplica normalização (uppercase + trim) tanto nas chaves (source)
        quanto nos valores (target) para garantir matches no banco de dados.
        
        Args:
            raw_mapping: Dicionário bruto do JSON
        """
        # Normalizar chaves e valores: uppercase + trim
        normalized_mapping = {
            self._normalize_brand(source): self._normalize_brand(target)
            for source, target in raw_mapping.items()
            if source and target  # Ignora entradas vazias
        }
        
        # Armazenar em dicionário para lookup rápido
        self._mapping_dict = normalized_mapping
        
        # Converter para DataFrame para uso em joins/merges do DuckDB
        self._mapping_df = pd.DataFrame([
            {"source": source, "target": target}
            for source, target in normalized_mapping.items()
        ])
    
    @staticmethod
    def _normalize_brand(brand: str) -> str:
        """
        Normaliza o nome de uma marca.
        
        Args:
            brand: Nome da marca a normalizar
        
        Returns:
            str: Nome normalizado (uppercase + trim)
        """
        if not isinstance(brand, str):
            return ""
        
        return brand.strip().upper()
    
    def reload_mapping(self) -> None:
        """
        Força o recarregamento do mapeamento de marcas.
        
        Útil para atualizar o cache quando o arquivo JSON é modificado.
        """
        self._mapping_df = None
        self._mapping_dict = None
        self._load_mapping()
    
    def get_target_brand(self, source_brand: str) -> Optional[str]:
        """
        Retorna o nome correto da marca para um nome incorreto.
        
        Args:
            source_brand: Nome incorreto da marca
        
        Returns:
            Optional[str]: Nome correto da marca ou None se não encontrado
        """
        if self._mapping_dict is None:
            self._load_mapping()
        
        normalized_source = self._normalize_brand(source_brand)
        return self._mapping_dict.get(normalized_source)
    
    def has_mapping_for(self, source_brand: str) -> bool:
        """
        Verifica se existe mapeamento para uma marca específica.
        
        Args:
            source_brand: Nome da marca a verificar
        
        Returns:
            bool: True se existe mapeamento, False caso contrário
        """
        if self._mapping_dict is None:
            self._load_mapping()
        
        normalized_source = self._normalize_brand(source_brand)
        return normalized_source in self._mapping_dict
    
    @property
    def mapping_count(self) -> int:
        """
        Retorna a quantidade de mapeamentos disponíveis.
        
        Returns:
            int: Número de mapeamentos carregados
        """
        if self._mapping_dict is None:
            self._load_mapping()
        
        return len(self._mapping_dict)


# Instância singleton global (lazy loading)
_brand_mapping_service: Optional[BrandMappingService] = None


def get_brand_mapping_service() -> BrandMappingService:
    """
    Factory function para obter a instância singleton do serviço.
    
    Returns:
        BrandMappingService: Instância única do serviço de mapeamento
    """
    global _brand_mapping_service
    
    if _brand_mapping_service is None:
        _brand_mapping_service = BrandMappingService()
    
    return _brand_mapping_service
