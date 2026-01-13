"""
Pipeline de Ingestão de Peças - Sistema Transacional com Bulk Operations
Autor: Arquiteto de Dados & Desenvolvedor Python Sênior
Versão: 1.0
Descrição: Processa planilhas Excel (~10k registros), cria manufacturers/brands,
           valida unicidade e insere peças com logging profissional e rollback total
"""

import pandas as pd
import psycopg2
import psycopg2.extras
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass
import logging
import time
from datetime import datetime
import sys
import json

# ============================================================================
# CONFIGURAÇÃO DE ATUALIZAÇÃO DE CAMPOS
# ============================================================================
class UpdateFieldConfig:
    """
    Configuração de como cada campo deve ser tratado ao atualizar peças existentes
    """
    # Campos que NUNCA são atualizados (sistema)
    SYSTEM_FIELDS = [
        'id', 'manufacturer_ref', 'search_ref', 'brand_id', 
        'created', 'updated', 'status', 'has_stock', 'ready_to_p4m',
        'p4m_quantity_by_states', 'p4m_status', 'p4m_logs',
        'manually_categorized', 'from_aux_db', 'similarity_id'
    ]
    
    # Campos disponíveis para atualização (usuário pode escolher)
    AVAILABLE_FIELDS = [
        'name', 'ncm', 'barcode', 'gross_weight', 
        'width', 'depth', 'height', 'notes', 'application'
    ]
    
    def __init__(self, force_override: List[str] = None, concatenate: List[str] = None, update_if_empty: List[str] = None):
        """
        Inicializa configuração de campos
        
        Args:
            force_override: Campos que sempre substituem o valor
            concatenate: Campos que devem ser concatenados
            update_if_empty: Campos atualizados apenas se estiverem vazios/nulos/0
        """
        self.force_override_fields = force_override or []
        self.concatenate_fields = concatenate or []
        self.update_if_empty_fields = update_if_empty or []
        # Campos não configurados são IGNORADOS (não atualizados)
    
    def get_updatable_fields(self) -> List[str]:
        """Retorna lista de todos os campos que podem ser atualizados"""
        return list(set(self.force_override_fields + self.concatenate_fields + self.update_if_empty_fields))
    
    def should_update_field(self, field_name: str, current_value, new_value) -> Tuple[bool, str]:
        """
        Determina se um campo deve ser atualizado
        
        Returns:
            Tuple[should_update: bool, reason: str]
        """
        # Ignorar campos de sistema
        if field_name in self.SYSTEM_FIELDS:
            return False, "field_ignored"
        
        # Novo valor é nulo/vazio - não atualizar
        if self._is_empty(new_value):
            return False, "new_value_empty"
        
        # Force override
        if field_name in self.force_override_fields:
            if current_value != new_value:
                return True, "force_override"
            return False, "no_change"
        
        # Concatenar
        if field_name in self.concatenate_fields:
            # Se atual está vazio, substituir
            if self._is_empty(current_value):
                return True, "concatenate_empty"
            # Se valores são iguais, não atualizar
            if str(current_value).strip() == str(new_value).strip():
                return False, "no_change"
            # Se novo valor já está contido no atual, não atualizar
            if str(new_value).strip() in str(current_value):
                return False, "already_contained"
            return True, "concatenate"
        
        # Update if empty
        if field_name in self.update_if_empty_fields:
            if self._is_empty(current_value):
                return True, "update_if_empty"
            return False, "current_not_empty"
        
        return False, "unknown_field"
    
    @staticmethod
    def _is_empty(value) -> bool:
        """Checa se valor é considerado vazio (None, '', 0, '0')"""
        if value is None:
            return True
        if isinstance(value, str):
            stripped = value.strip()
            return stripped == '' or stripped == '0'
        if isinstance(value, (int, float)):
            return value == 0
        return False

# ============================================================================
# CONFIGURAÇÃO DE LOGGING PROFISSIONAL
# ============================================================================
def setup_logging():
    """Configura logging para console e arquivo com formatação profissional"""
    log_format = '%(asctime)s | %(levelname)-8s | %(funcName)-20s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configurar handler para arquivo
    file_handler = logging.FileHandler('part_ingestion.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Configurar handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Configurar logger raiz
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# ============================================================================
# DECORATOR PARA MEDIÇÃO DE PERFORMANCE
# ============================================================================
def timer_decorator(func):
    """Decorator para medir tempo de execução de funções"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Iniciando: {func.__name__}")
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        logger.info(f"Concluído: {func.__name__} | Tempo: {elapsed_time:.2f}s")
        return result
    return wrapper

# ============================================================================
# DATACLASS PARA RELATÓRIO DE INGESTÃO
# ============================================================================
@dataclass
class IngestionReport:
    """Relatório de métricas do processo de ingestão"""
    total_rows_original: int
    total_rows_valid: int
    invalid_records: int
    duplicates_internal: int
    brands_created: int
    manufacturers_created: int
    parts_existing: int
    parts_inserted: int
    parts_updated: int
    fields_updated: int
    execution_time: float
    # Similaridades (opcionais)
    has_similarities: bool = False
    similarity_groups_created: int = 0
    similarity_groups_merged: int = 0
    similarity_parts_updated: int = 0
    similar_parts_created: int = 0  # Peças similares criadas automaticamente
    similar_brands_created: int = 0  # Brands criadas durante processamento de similaridades
    similar_manufacturers_created: int = 0  # Manufacturers criados durante processamento de similaridades
    # PartActivity
    part_activities_created: int = 0

# ============================================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ============================================================================
db_config = {
    'host': 'localhost',
    'port': '5432',
    'database': 'hubbi',
    'user': 'pgroot',
    'password': 'pg@root'
}

# ============================================================================
# FUNÇÕES DE VALIDAÇÃO E TRANSFORMAÇÃO
# ============================================================================
def sanitize_string_value(value) -> Optional[str]:
    """
    Sanitiza valores string removendo NaN, 'nan', strings vazias e '0'
    
    Args:
        value: Valor a ser sanitizado
    
    Returns:
        String limpa ou None se inválido
    """
    if pd.isna(value):
        return None
    
    str_value = str(value).strip()
    
    # Checar se é 'nan', 'NaN', vazio ou '0'
    if str_value.upper() in ('NAN', '', '0', 'NONE'):
        return None
    
    return str_value

def sanitize_numeric_value(value) -> Optional[float]:
    """
    Sanitiza valores numéricos removendo NaN e zeros
    
    Args:
        value: Valor numérico a ser sanitizado
    
    Returns:
        Float válido ou None
    """
    if pd.isna(value):
        return None
    
    try:
        float_value = float(value)
        # Converter 0 para None
        if float_value == 0:
            return None
        return float_value
    except (ValueError, TypeError):
        return None

def format_ncm(value) -> Optional[str]:
    """
    Formata NCM no padrão XXXX.XX.XX removendo .0 e adicionando pontos
    
    Args:
        value: Valor do NCM (pode ser string ou número)
    
    Returns:
        NCM formatado ou None se inválido
    """
    if pd.isna(value):
        return None
    
    # Converter para string e remover espaços
    ncm_str = str(value).strip()
    
    # Checar se é inválido
    if ncm_str.upper() in ('NAN', '', '0', 'NONE'):
        return None
    
    # Remover .0 se presente (caso Excel tenha convertido para float)
    if ncm_str.endswith('.0'):
        ncm_str = ncm_str[:-2]
    
    # Remover pontos existentes para normalizar
    ncm_digits = ncm_str.replace('.', '').replace('-', '')
    
    # Validar se tem apenas dígitos
    if not ncm_digits.isdigit():
        logger.warning(f"NCM inválido (não numérico): {value} -> NULL")
        return None
    
    # NCM deve ter 8 dígitos
    if len(ncm_digits) != 8:
        logger.warning(f"NCM inválido (tamanho != 8): {value} -> NULL")
        return None
    
    # Formatar como XXXX.XX.XX
    formatted_ncm = f"{ncm_digits[:4]}.{ncm_digits[4:6]}.{ncm_digits[6:8]}"
    return formatted_ncm

def format_barcode(value) -> Optional[str]:
    """
    Formata barcode removendo .0 se presente
    
    Args:
        value: Valor do barcode (pode ser string ou número)
    
    Returns:
        Barcode limpo ou None se inválido
    """
    if pd.isna(value):
        return None
    
    # Converter para string e remover espaços
    barcode_str = str(value).strip()
    
    # Checar se é inválido
    if barcode_str.upper() in ('NAN', '', '0', 'NONE'):
        return None
    
    # Remover .0 se presente (caso Excel tenha convertido para float)
    if barcode_str.endswith('.0'):
        barcode_str = barcode_str[:-2]
    
    return barcode_str

@timer_decorator
def read_excel(file_path: str) -> Tuple[pd.DataFrame, Dict]:
    """
    Carrega e sanitiza dados do Excel com validação de colunas e normalização
    
    Args:
        file_path: Caminho do arquivo Excel
    
    Returns:
        Tuple[DataFrame sanitizado, Dict com estatísticas de filtragem]
    """
    logger.info(f"Carregando arquivo: {file_path}")
    df = pd.read_excel(file_path)
    
    # Define colunas obrigatórias e opcionais
    colunas_obrigatorias = {
        'Código do Fabricante (SKU)*',
        'Dealer Code (Código Interno)*',
        'Nome do Fabricante*',
        'Estoque*',
        'Preço*'
    }
    
    colunas_opcionais = {
        'Nome da Peça',
        'Descrição Comercial',
        'Aplicação',
        'Especificações',
        'Código de Barras',
        'NCM',
        'Altura (cm)',
        'Comprimento (cm)',
        'Largura (cm)',
        'Peso bruto (kg)',
        'Similaridades'
    }
    
    colunas_permitidas = colunas_obrigatorias | colunas_opcionais
    colunas_atuais = set(df.columns)
    
    # Verifica se todas as colunas obrigatórias estão presentes
    colunas_faltantes = colunas_obrigatorias - colunas_atuais
    if colunas_faltantes:
        raise ValueError(f"Colunas obrigatórias faltando: {', '.join(sorted(colunas_faltantes))}")
    
    # Remove colunas que não estão na lista de permitidas
    colunas_para_remover = colunas_atuais - colunas_permitidas
    if colunas_para_remover:
        logger.info(f"Removendo colunas não permitidas: {', '.join(sorted(colunas_para_remover))}")
        df = df.drop(columns=list(colunas_para_remover))
    
    total_rows_original = len(df)
    logger.info(f"Total de registros carregados: {total_rows_original}")
    
    # Estatísticas de filtragem
    stats = {
        'total_rows_original': total_rows_original,
        'invalid_records': 0,
        'duplicates_internal': 0
    }
    
    # ========================================================================
    # NORMALIZAÇÃO E SANITIZAÇÃO DE DADOS
    # ========================================================================
    
    # Normalizar SKU (manufacturer_ref e search_ref são iguais)
    df['manufacturer_ref'] = df['Código do Fabricante (SKU)*'].astype(str).str.strip().str.upper()
    df['search_ref'] = df['manufacturer_ref']  # Sempre iguais
    
    # Normalizar Nome do Fabricante para matching com manufacturer_brand
    df['brand_name_normalized'] = df['Nome do Fabricante*'].astype(str).str.strip().str.upper()
    
    # ========================================================================
    # IDENTIFICAR SKUs MUITO LONGOS (>60 caracteres)
    # ========================================================================
    long_sku_mask = df['manufacturer_ref'].str.len() > 60
    long_sku_count = long_sku_mask.sum()
    if long_sku_count > 0:
        logger.warning(f"Encontrados {long_sku_count} registros com SKU > 60 caracteres:")
        for idx, row in df[long_sku_mask].iterrows():
            sku_len = len(row['manufacturer_ref'])
            logger.warning(f"  SKU={row['manufacturer_ref'][:100]}... (Length={sku_len}), Brand={row['brand_name_normalized']}")
    
    # ========================================================================
    # REMOVER REGISTROS COM SKU OU BRAND INVÁLIDOS (NAN, vazio, 'NAN', 1-3 dígitos)
    # ========================================================================
    initial_count = len(df)
    
    # Calcular tamanho do SKU
    df['sku_length'] = df['manufacturer_ref'].str.len()
    
    # Filtrar registros onde SKU ou Brand são inválidos
    df = df[
        (df['manufacturer_ref'] != 'NAN') & 
        (df['manufacturer_ref'] != '') & 
        (df['brand_name_normalized'] != 'NAN') & 
        (df['brand_name_normalized'] != '') &
        (df['sku_length'] > 3)  # Remover SKUs com 1-3 caracteres
    ]
    
    # Contar registros removidos por tamanho curto
    short_sku_count = (df['sku_length'] <= 3).sum() if 'sku_length' in df.columns else 0
    
    invalid_count = initial_count - len(df)
    stats['invalid_records'] = invalid_count
    if invalid_count > 0:
        logger.warning(f"Removidos {invalid_count} registros com SKU ou Brand inválidos")
        if short_sku_count > 0:
            logger.warning(f"  - {short_sku_count} registros com SKU de 1-3 caracteres")
        if invalid_count - short_sku_count > 0:
            logger.warning(f"  - {invalid_count - short_sku_count} registros com NAN/vazio")
    
    # Remover coluna auxiliar
    df = df.drop(columns=['sku_length'], errors='ignore')
    
    logger.info(f"Registros válidos após filtragem: {len(df)}")
    
    # ========================================================================
    # SANITIZAÇÃO DE COLUNAS STRING
    # ========================================================================
    
    # Mapear colunas opcionais para schema de catalog_part com sanitização
    if 'Nome da Peça' in df.columns:
        df['name'] = df['Nome da Peça'].apply(sanitize_string_value)
    else:
        df['name'] = None
    
    if 'Código de Barras' in df.columns:
        df['barcode'] = df['Código de Barras'].apply(format_barcode)
    else:
        df['barcode'] = None
    
    if 'NCM' in df.columns:
        df['ncm'] = df['NCM'].apply(format_ncm)
    else:
        df['ncm'] = None
    
    if 'Aplicação' in df.columns:
        df['application'] = df['Aplicação'].apply(sanitize_string_value)
    else:
        df['application'] = None
    
    # ========================================================================
    # SANITIZAÇÃO DE COLUNAS NUMÉRICAS
    # ========================================================================
    
    # Converter colunas numéricas com tratamento de erros e zeros
    def safe_numeric_conversion(series, col_name):
        """Converte para float com log de erros, convertendo 0 para None"""
        try:
            result = pd.to_numeric(series, errors='coerce')
            invalid_count = result.isna().sum() - series.isna().sum()
            if invalid_count > 0:
                logger.warning(f"Coluna '{col_name}': {invalid_count} valores não conversíveis para numérico -> NULL")
            
            # Converter 0 para None
            zero_count = (result == 0).sum()
            if zero_count > 0:
                logger.info(f"Coluna '{col_name}': {zero_count} valores iguais a 0 convertidos para NULL")
                result = result.replace(0, None)
            
            return result
        except Exception as e:
            logger.error(f"Erro ao converter '{col_name}': {e}")
            return None
    
    if 'Peso bruto (kg)' in df.columns:
        df['gross_weight'] = safe_numeric_conversion(df['Peso bruto (kg)'], 'Peso bruto (kg)')
    else:
        df['gross_weight'] = None
    
    if 'Largura (cm)' in df.columns:
        df['width'] = safe_numeric_conversion(df['Largura (cm)'], 'Largura (cm)')
    else:
        df['width'] = None
    
    if 'Comprimento (cm)' in df.columns:
        df['depth'] = safe_numeric_conversion(df['Comprimento (cm)'], 'Comprimento (cm)')
    else:
        df['depth'] = None
    
    if 'Altura (cm)' in df.columns:
        df['height'] = safe_numeric_conversion(df['Altura (cm)'], 'Altura (cm)')
    else:
        df['height'] = None
    
    # Truncar notes em 6000 chars (VARCHAR limit) com sanitização
    if 'Especificações' in df.columns:
        # Limpar strings "NAN" antes de sanitizar
        nan_mask = df['Especificações'].notna() & (df['Especificações'].astype(str).str.strip().str.upper() == 'NAN')
        nan_count = nan_mask.sum()
        if nan_count > 0:
            logger.info(f"Convertendo {nan_count} registros com 'Especificações' = 'NAN' para NULL")
            df.loc[nan_mask, 'Especificações'] = None
        
        df['notes'] = df['Especificações'].apply(sanitize_string_value)
        # Truncar apenas valores não-nulos
        truncated_mask = df['notes'].notna() & (df['notes'].str.len() > 6000)
        truncated_count = truncated_mask.sum()
        if truncated_count > 0:
            logger.warning(f"Truncando {truncated_count} registros com 'notes' > 6000 caracteres")
            df.loc[truncated_mask, 'notes'] = df.loc[truncated_mask, 'notes'].str[:6000]
    else:
        df['notes'] = None
    
    # ========================================================================
    # DETECÇÃO DE DUPLICATAS INTERNAS
    # ========================================================================
    duplicated_mask = df.duplicated(subset=['manufacturer_ref', 'brand_name_normalized'], keep='first')
    duplicates_count = duplicated_mask.sum()
    stats['duplicates_internal'] = duplicates_count
    
    if duplicates_count > 0:
        logger.warning(f"Detectadas {duplicates_count} duplicatas internas (mesmo SKU+Brand)")
        duplicated_rows = df[duplicated_mask][['manufacturer_ref', 'brand_name_normalized']]
        for _, row in duplicated_rows.iterrows():
            logger.warning(f"  Duplicata: SKU={row['manufacturer_ref']}, Brand={row['brand_name_normalized']}")
        
        # Remover duplicatas mantendo a primeira ocorrência
        df = df[~duplicated_mask]
        logger.info(f"Duplicatas removidas. Registros únicos: {len(df)}")
    
    # Drop colunas originais não mais necessárias (preservar Similaridades se existir)
    cols_to_drop = ['Código do Fabricante (SKU)*', 'Nome do Fabricante*', 'Dealer Code (Código Interno)*', 
                    'Estoque*', 'Preço*', 'Descrição Comercial']
    cols_to_drop.extend(['Nome da Peça', 'Código de Barras', 'NCM', 'Aplicação', 'Especificações',
                        'Peso bruto (kg)', 'Largura (cm)', 'Comprimento (cm)', 'Altura (cm)'])
    
    df = df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore')
    
    # Verificar se coluna Similaridades existe
    has_similarities = 'Similaridades' in df.columns
    if has_similarities:
        logger.info("Coluna 'Similaridades' detectada - será processada ao final do pipeline")
    
    logger.info(f"Sanitização concluída. Registros finais: {len(df)}")
    return df, stats

def connect_db(db_config: Dict) -> psycopg2.extensions.connection:
    """Estabelece conexão com PostgreSQL"""
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )
    logger.info("Conexão com banco de dados estabelecida com sucesso.")
    return conn

# ============================================================================
# BRAND REPOSITORY - Gerencia manufacturers e brands
# ============================================================================
class BrandRepository:
    """Repository para operações com manufacturer e manufacturer_brand"""
    
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn
    
    @timer_decorator
    def fetch_all_brands(self) -> Dict[str, Tuple[int, int]]:
        """
        Busca todas as brands do banco e retorna dicionário normalizado
        
        Returns:
            Dict[brand_name_normalized, (brand_id, manufacturer_id)]
        """
        cursor = self.conn.cursor()
        try:
            query = """
                SELECT UPPER(TRIM(name)) as name_key, id, manufacturer_id 
                FROM manufacturer_brand
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            brand_dict = {row[0]: (row[1], row[2]) for row in results}
            logger.info(f"Carregadas {len(brand_dict)} brands do banco de dados")
            return brand_dict
            
        except Exception as e:
            logger.error(f"Erro ao buscar brands: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
    
    @timer_decorator
    def bulk_create_missing_brands(self, missing_brands: Set[str]) -> Dict[str, Tuple[int, int]]:
        """
        Cria manufacturers e brands ausentes em lote
        
        Args:
            missing_brands: Set de nomes de brands a serem criadas
        
        Returns:
            Dict[brand_name, (brand_id, manufacturer_id)] das brands criadas
        """
        if not missing_brands:
            logger.info("Nenhuma brand ausente para criar")
            return {}
        
        cursor = self.conn.cursor()
        created_brands = {}
        
        try:
            logger.info(f"Criando {len(missing_brands)} manufacturers e brands")
            print(f"\n🏭 BRANDS A SEREM CRIADAS ({len(missing_brands)}):")
            for brand in sorted(missing_brands):
                print(f"  ✨ {brand}")
            print()
            
            for brand_name in missing_brands:
                # Criar manufacturer primeiro
                cursor.execute("""
                    INSERT INTO manufacturer_manufacturer (name, commercial_name, names, role, cnpj, created) 
                    VALUES (%s, %s, ARRAY[%s], 4, NULL, NOW()) 
                    RETURNING id
                """, (brand_name, brand_name, brand_name))
                
                manufacturer_id = cursor.fetchone()[0]
                
                # Criar manufacturer_brand vinculada ao manufacturer
                cursor.execute("""
                    INSERT INTO manufacturer_brand (name, manufacturer_id, created, asset_id) 
                    VALUES (%s, %s, NOW(), NULL) 
                    RETURNING id
                """, (brand_name, manufacturer_id))
                
                brand_id = cursor.fetchone()[0]
                
                created_brands[brand_name] = (brand_id, manufacturer_id)
                logger.debug(f"Criado: Brand '{brand_name}' (brand_id={brand_id}, manufacturer_id={manufacturer_id})")
            
            logger.info(f"Criados com sucesso: {len(created_brands)} manufacturers e brands")
            return created_brands
            
        except Exception as e:
            logger.error(f"Erro ao criar brands: {e}", exc_info=True)
            raise
        finally:
            cursor.close()

# ============================================================================
# PART REPOSITORY - Gerencia catalog_part
# ============================================================================
class PartRepository:
    """Repository para operações com catalog_part"""
    
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn
    
    @timer_decorator
    def fetch_existing_parts(self, parts_to_check: List[Tuple[str, int]]) -> Set[Tuple[str, int]]:
        """
        Busca peças existentes no banco para detectar duplicatas
        
        Args:
            parts_to_check: Lista de tuplas (manufacturer_ref, brand_id)
        
        Returns:
            Set de tuplas (manufacturer_ref, brand_id) que já existem
        """
        if not parts_to_check:
            return set()
        
        cursor = self.conn.cursor()
        existing_parts = set()
        
        try:
            # Dividir em batches de 1000 para evitar "stack depth limit exceeded"
            batch_size = 1000
            total_batches = (len(parts_to_check) + batch_size - 1) // batch_size
            
            logger.info(f"Verificando {len(parts_to_check)} peças em {total_batches} batches de {batch_size}")
            
            for i in range(0, len(parts_to_check), batch_size):
                batch = parts_to_check[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                logger.debug(f"Processando batch {batch_num}/{total_batches} ({len(batch)} peças)")
                
                query = """
                    SELECT manufacturer_ref, brand_id 
                    FROM catalog_part 
                    WHERE (manufacturer_ref, brand_id) IN %s
                """
                
                cursor.execute(query, (tuple(batch),))
                results = cursor.fetchall()
                existing_parts.update(results)
            
            logger.info(f"Encontradas {len(existing_parts)} peças já existentes no banco")
            return existing_parts
            
        except Exception as e:
            logger.error(f"Erro ao buscar peças existentes: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
    
    @timer_decorator
    def fetch_parts_details(self, parts_to_fetch: List[Tuple[str, int]], updatable_fields: List[str]) -> Dict[Tuple[str, int], Dict]:
        """
        Busca detalhes completos de peças existentes para comparação
        
        Args:
            parts_to_fetch: Lista de tuplas (manufacturer_ref, brand_id)
            updatable_fields: Lista de campos a serem buscados
        
        Returns:
            Dict[(manufacturer_ref, brand_id), {campo: valor}]
        """
        if not parts_to_fetch:
            return {}
        
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        parts_dict = {}
        
        try:
            batch_size = 1000
            fields_str = ', '.join(['id', 'manufacturer_ref', 'brand_id'] + updatable_fields)
            
            logger.info(f"Buscando detalhes de {len(parts_to_fetch)} peças existentes")
            
            for i in range(0, len(parts_to_fetch), batch_size):
                batch = parts_to_fetch[i:i + batch_size]
                
                query = f"""
                    SELECT {fields_str}
                    FROM catalog_part
                    WHERE (manufacturer_ref, brand_id) IN %s
                """
                
                cursor.execute(query, (tuple(batch),))
                results = cursor.fetchall()
                
                for row in results:
                    key = (row['manufacturer_ref'], row['brand_id'])
                    parts_dict[key] = dict(row)
            
            logger.info(f"Detalhes carregados de {len(parts_dict)} peças")
            return parts_dict
            
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes de peças: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
    
    @timer_decorator
    def bulk_insert_parts(self, parts_data: List[Tuple]) -> Tuple[int, List[int]]:
        """
        Insere peças em lote usando execute_values para performance otimizada
        
        Args:
            parts_data: Lista de tuplas com dados das peças
        
        Returns:
            Tupla (quantidade inserida, lista de IDs das peças inseridas)
        """
        if not parts_data:
            logger.info("Nenhuma peça para inserir")
            return 0, []
        
        cursor = self.conn.cursor()
        try:
            query = """
                INSERT INTO catalog_part 
                (manufacturer_ref, search_ref, name, brand_id, ncm, barcode, 
                 gross_weight, width, depth, height, notes, application, created, updated, status, has_stock, ready_to_p4m,
                 p4m_quantity_by_states, p4m_status, p4m_logs, manually_categorized, from_aux_db, born_at, deprecated_at)
                VALUES %s
                RETURNING id
            """
            
            # Usar execute_values com page_size=1000 para performance e capturar IDs
            psycopg2.extras.execute_values(
                cursor, 
                query, 
                parts_data, 
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                page_size=1000,
                fetch=True
            )
            
            # Capturar IDs retornados
            inserted_ids = [row[0] for row in cursor.fetchall()]
            inserted_count = len(inserted_ids)
            
            logger.info(f"Inseridas {inserted_count} peças no banco de dados")
            return inserted_count, inserted_ids
            
        except Exception as e:
            logger.error(f"Erro ao inserir peças: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
    
    @timer_decorator
    def bulk_update_parts(self, updates: List[Dict]) -> int:
        """
        Atualiza campos de peças existentes
        
        Args:
            updates: Lista de dicts com {part_id, field_updates: {campo: valor}}
        
        Returns:
            Quantidade de peças atualizadas
        """
        if not updates:
            logger.info("Nenhuma peça para atualizar")
            return 0
        
        cursor = self.conn.cursor()
        updated_count = 0
        
        try:
            timestamp_now = datetime.now()
            
            for update_item in updates:
                part_id = update_item['part_id']
                field_updates = update_item['field_updates']
                
                if not field_updates:
                    continue
                
                # Construir cláusula SET dinamicamente
                set_clauses = []
                values = []
                
                for field_name, new_value in field_updates.items():
                    set_clauses.append(f"{field_name} = %s")
                    values.append(new_value)
                
                # Adicionar updated timestamp
                set_clauses.append("updated = %s")
                values.append(timestamp_now)
                
                # Adicionar part_id ao final
                values.append(part_id)
                
                query = f"""
                    UPDATE catalog_part
                    SET {', '.join(set_clauses)}
                    WHERE id = %s
                """
                
                cursor.execute(query, values)
                updated_count += cursor.rowcount
            
            logger.info(f"Atualizadas {updated_count} peças no banco de dados")
            return updated_count
            
        except Exception as e:
            logger.error(f"Erro ao atualizar peças: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
    
    @timer_decorator
    def bulk_insert_part_activities(self, part_ids: List[int], author_id: int, current_owner_id: int) -> int:
        """
        Registra activities de CREATION para peças recém-inseridas
        
        Args:
            part_ids: Lista de IDs das peças inseridas
            author_id: ID do usuário autor da operação
            current_owner_id: ID do manufacturer fornecedor das informações
        
        Returns:
            Quantidade de activities criadas
        """
        if not part_ids:
            logger.info("Nenhuma activity para criar")
            return 0
        
        cursor = self.conn.cursor()
        try:
            # Preparar dados para bulk insert
            # (part_id, activity_type, author_id, attribute, current_owner_id, created)
            timestamp_now = datetime.now()
            activities_data = [
                (part_id, 'CRE', author_id, 'all', None, None, None, current_owner_id, timestamp_now)
                for part_id in part_ids
            ]
            
            query = """
                INSERT INTO catalog_partactivity 
                (part_id, activity_type, author_id, attribute, previous_value, previous_owner_id, current_value, current_owner_id, created)
                VALUES %s
            """
            
            psycopg2.extras.execute_values(
                cursor,
                query,
                activities_data,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                page_size=1000
            )
            
            activities_count = cursor.rowcount
            logger.info(f"Criadas {activities_count} activities de CREATION")
            return activities_count
            
        except Exception as e:
            logger.error(f"Erro ao inserir activities: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
    
    @timer_decorator
    def bulk_insert_update_activities(self, activities_data: List[Dict], author_id: int, current_owner_id: int) -> int:
        """
        Registra activities de UPDATE para campos modificados
        
        Args:
            activities_data: Lista de dicts com {part_id, attribute, previous_value, current_value}
            author_id: ID do usuário autor
            current_owner_id: ID do manufacturer fornecedor
        
        Returns:
            Quantidade de activities criadas
        """
        if not activities_data:
            return 0
        
        cursor = self.conn.cursor()
        try:
            timestamp_now = datetime.now()
            
            # Preparar dados para bulk insert
            activities_tuples = [
                (
                    item['part_id'],
                    'UPD',
                    author_id,
                    item['attribute'],
                    str(item['previous_value']) if item['previous_value'] is not None else None,
                    None,  # previous_owner_id
                    str(item['current_value']) if item['current_value'] is not None else None,
                    current_owner_id,
                    timestamp_now
                )
                for item in activities_data
            ]
            
            query = """
                INSERT INTO catalog_partactivity
                (part_id, activity_type, author_id, attribute, previous_value, previous_owner_id, current_value, current_owner_id, created)
                VALUES %s
            """
            
            psycopg2.extras.execute_values(
                cursor,
                query,
                activities_tuples,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                page_size=1000
            )
            
            activities_count = cursor.rowcount
            logger.info(f"Criadas {activities_count} activities de UPDATE")
            return activities_count
            
        except Exception as e:
            logger.error(f"Erro ao inserir update activities: {e}", exc_info=True)
            raise
        finally:
            cursor.close()

# ============================================================================
# SIMILARITY REPOSITORY - Gerencia catalog_similarity
# ============================================================================
class SimilarityRepository:
    """Repository para operações com catalog_similarity"""
    
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn
    
    def fetch_parts_with_similarity(self, parts_refs: List[Tuple[str, str]]) -> Dict[Tuple[str, str], Tuple[int, Optional[int]]]:
        """
        Busca part_id e similarity_id de peças baseado em (search_ref, brand_name)
        
        Args:
            parts_refs: Lista de tuplas (search_ref, brand_name_normalized)
        
        Returns:
            Dict[(search_ref, brand_name), (part_id, similarity_id)]
        """
        if not parts_refs:
            return {}
        
        cursor = self.conn.cursor()
        result_dict = {}
        
        try:
            # Processar em batches
            batch_size = 1000
            for i in range(0, len(parts_refs), batch_size):
                batch = parts_refs[i:i + batch_size]
                
                query = """
                    SELECT cp.search_ref, UPPER(TRIM(mb.name)) as brand_name, cp.id, cp.similarity_id
                    FROM catalog_part cp
                    JOIN manufacturer_brand mb ON cp.brand_id = mb.id
                    WHERE (cp.search_ref, UPPER(TRIM(mb.name))) IN %s
                """
                
                cursor.execute(query, (tuple(batch),))
                results = cursor.fetchall()
                
                for row in results:
                    search_ref, brand_name, part_id, similarity_id = row
                    result_dict[(search_ref, brand_name)] = (part_id, similarity_id)
            
            return result_dict
            
        except Exception as e:
            logger.error(f"Erro ao buscar peças com similaridade: {e}", exc_info=True)
            # ROLLBACK para recuperar transação após erro SQL
            self.conn.rollback()
            raise
        finally:
            cursor.close()
    
    def create_similarity_group(self) -> int:
        """
        Cria um novo grupo de similaridade sempre usando MAX(id) + 1
        
        Returns:
            ID do novo grupo criado
        """
        cursor = self.conn.cursor()
        try:
            # Buscar o próximo ID disponível baseado no MAX atual
            cursor.execute("""
                SELECT COALESCE(MAX(id), 0) + 1 FROM catalog_similarity
            """)
            next_id = cursor.fetchone()[0]
            
            # Inserir com ID explícito
            cursor.execute("""
                INSERT INTO catalog_similarity (id, created)
                VALUES (%s, NOW())
                RETURNING id
            """, (next_id,))
            
            similarity_id = cursor.fetchone()[0]
            logger.debug(f"Criado novo grupo de similaridade: ID={similarity_id}")
            
            # Atualizar sequence para evitar conflitos futuros
            cursor.execute("""
                SELECT setval('catalog_similarity_id_seq', %s, true)
            """, (similarity_id,))
            
            return similarity_id
        except Exception as e:
            logger.error(f"Erro ao criar grupo de similaridade: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
    
    def update_parts_similarity(self, part_ids: List[int], similarity_id: int) -> int:
        """
        Atualiza similarity_id de múltiplas peças
        
        Args:
            part_ids: Lista de IDs de peças
            similarity_id: ID do grupo de similaridade
        
        Returns:
            Quantidade de registros atualizados
        """
        if not part_ids:
            return 0
        
        cursor = self.conn.cursor()
        try:
            query = """
                UPDATE catalog_part
                SET similarity_id = %s, updated = NOW()
                WHERE id = ANY(%s)
            """
            cursor.execute(query, (similarity_id, part_ids))
            updated_count = cursor.rowcount
            logger.debug(f"Atualizadas {updated_count} peças com similarity_id={similarity_id}")
            return updated_count
        except Exception as e:
            logger.error(f"Erro ao atualizar similarity_id: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
    
    def migrate_similarity_groups(self, from_similarity_id: int, to_similarity_id: int) -> int:
        """
        Migra todas as peças de um grupo de similaridade para outro
        
        Args:
            from_similarity_id: ID origem
            to_similarity_id: ID destino
        
        Returns:
            Quantidade de registros migrados
        """
        cursor = self.conn.cursor()
        try:
            query = """
                UPDATE catalog_part
                SET similarity_id = %s, updated = NOW()
                WHERE similarity_id = %s
            """
            cursor.execute(query, (to_similarity_id, from_similarity_id))
            migrated_count = cursor.rowcount
            logger.info(f"Migradas {migrated_count} peças de similarity_id={from_similarity_id} para {to_similarity_id}")
            return migrated_count
        except Exception as e:
            logger.error(f"Erro ao migrar grupos de similaridade: {e}", exc_info=True)
            raise
        finally:
            cursor.close()

# ============================================================================
# FUNÇÕES AUXILIARES PARA MAPEAMENTO DE MARCAS
# ============================================================================
def load_brand_mapping(mapping_file: str = 'mapeamento-marcas-invertido.json') -> Dict[str, str]:
    """
    Carrega arquivo de mapeamento de marcas
    
    Args:
        mapping_file: Caminho do arquivo JSON de mapeamento
    
    Returns:
        Dict[brand_name_original, brand_name_mapped] normalizado (uppercase)
    """
    try:
        # Tentar carregar do diretório atual
        script_dir = Path(__file__).parent
        mapping_path = script_dir / mapping_file
        
        if not mapping_path.exists():
            logger.warning(f"Arquivo de mapeamento não encontrado: {mapping_path}")
            return {}
        
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        # Normalizar keys e values para uppercase
        normalized_mapping = {
            k.strip().upper(): v.strip().upper() 
            for k, v in mapping.items()
        }
        
        logger.info(f"Mapeamento de marcas carregado: {len(normalized_mapping)} entradas")
        return normalized_mapping
        
    except Exception as e:
        logger.error(f"Erro ao carregar mapeamento de marcas: {e}", exc_info=True)
        return {}

def apply_brand_mapping(brand_name: str, brand_mapping: Dict[str, str]) -> str:
    """
    Aplica mapeamento a uma marca
    
    Args:
        brand_name: Nome original da marca (já normalizado uppercase)
        brand_mapping: Dicionário de mapeamento
    
    Returns:
        Nome mapeado ou original se não houver mapeamento
    """
    return brand_mapping.get(brand_name, brand_name)

# ============================================================================
# PROCESSAMENTO DE SIMILARIDADES
# ============================================================================
@timer_decorator
def process_similarities(conn: psycopg2.extensions.connection, df: pd.DataFrame, file_path: str) -> Dict:
    """
    Processa coluna Similaridades e atualiza similarity_id das peças
    
    Args:
        conn: Conexão com banco de dados
        df: DataFrame com dados processados (inclui coluna Similaridades se existir)
        file_path: Caminho do arquivo original para recarregar planilha completa
    
    Returns:
        Dict com estatísticas do processamento
    """
    logger.info("="*80)
    logger.info("FASE 8: PROCESSAMENTO DE SIMILARIDADES")
    logger.info("="*80)
    
    # Verificar se coluna Similaridades existe
    if 'Similaridades' not in df.columns:
        logger.info("Coluna 'Similaridades' não encontrada - pulando processamento")
        return {'processed': False}
    
    # Carregar mapeamento de marcas
    brand_mapping = load_brand_mapping()
    
    similarity_repo = SimilarityRepository(conn)
    stats = {
        'processed': True,
        'total_rows_with_similarities': 0,
        'groups_created': 0,
        'groups_merged': 0,
        'parts_updated': 0,
        'similar_parts_created': 0,
        'similar_brands_created': 0,
        'similar_manufacturers_created': 0
    }
    
    # Recarregar planilha original para pegar todas as colunas incluindo Similaridades
    logger.info(f"Recarregando planilha para processar similaridades: {file_path}")
    df_full = pd.read_excel(file_path)
    
    # Normalizar colunas chave
    df_full['manufacturer_ref'] = df_full['Código do Fabricante (SKU)*'].astype(str).str.strip().str.upper()
    df_full['brand_name_normalized'] = df_full['Nome do Fabricante*'].astype(str).str.strip().str.upper()
    
    # Filtrar apenas linhas com similaridades não vazias
    df_with_sim = df_full[df_full['Similaridades'].notna()].copy()
    stats['total_rows_with_similarities'] = len(df_with_sim)
    
    if stats['total_rows_with_similarities'] == 0:
        logger.info("Nenhum registro com similaridades para processar")
        return stats
    
    logger.info(f"Processando {stats['total_rows_with_similarities']} registros com similaridades")
    
    # Coletar todas as peças similares referenciadas
    all_similar_refs = set()  # Set de (search_ref, brand_name)
    main_part_names = {}  # Dict[(search_ref, brand)] -> name da peça principal
    
    for idx, row in df_with_sim.iterrows():
        try:
            main_ref = row['manufacturer_ref']
            main_brand = row['brand_name_normalized']
            main_name = df_full[df_full['manufacturer_ref'] == main_ref]['Nome da Peça'].iloc[0] if 'Nome da Peça' in df_full.columns else ''
            main_name = str(main_name).strip() if pd.notna(main_name) else ''
            
            # Parsear similaridades
            similarities_raw = row['Similaridades']
            similarities_list = None
            
            if isinstance(similarities_raw, str):
                try:
                    similarities_list = json.loads(similarities_raw)
                except json.JSONDecodeError:
                    try:
                        import ast
                        similarities_list = ast.literal_eval(similarities_raw)
                    except (ValueError, SyntaxError):
                        continue
            elif isinstance(similarities_raw, list):
                similarities_list = similarities_raw
            else:
                continue
            
            if not isinstance(similarities_list, list) or len(similarities_list) == 0:
                continue
            
            # Coletar refs de similares
            for sim in similarities_list:
                if isinstance(sim, dict) and 'search_ref' in sim and 'brand' in sim:
                    sim_ref = str(sim['search_ref']).strip().upper()
                    sim_brand_original = str(sim['brand']).strip().upper()
                    
                    # Aplicar mapeamento de marca
                    sim_brand = apply_brand_mapping(sim_brand_original, brand_mapping)
                    if sim_brand != sim_brand_original:
                        logger.debug(f"Marca similar mapeada: '{sim_brand_original}' -> '{sim_brand}'")
                    
                    # Verificar se SKU é muito longo (>60 caracteres)
                    if len(sim_ref) > 60:
                        logger.warning(f"SKU similar muito longo (>{60}): '{sim_ref}' (Length={len(sim_ref)}), Brand={sim_brand}, Linha={idx}")
                    
                    # Filtrar SKUs com 1-3 caracteres
                    if len(sim_ref) <= 3:
                        logger.warning(f"SKU similar muito curto (1-3 chars): '{sim_ref}', Brand={sim_brand}, Linha={idx} - IGNORADO")
                        continue
                    
                    all_similar_refs.add((sim_ref, sim_brand))
                    # Associar nome da peça principal às similares
                    main_part_names[(sim_ref, sim_brand)] = main_name
        
        except Exception as e:
            logger.error(f"Erro ao coletar similaridades da linha {idx}: {e}", exc_info=True)
            continue
    
    logger.info(f"Total de peças similares únicas referenciadas: {len(all_similar_refs)}")
    
    # Verificar quais peças similares não existem no banco
    if all_similar_refs:
        existing_similar_parts = similarity_repo.fetch_parts_with_similarity(list(all_similar_refs))
        missing_similar_refs = all_similar_refs - set(existing_similar_parts.keys())
        
        if missing_similar_refs:
            logger.info(f"Peças similares faltantes: {len(missing_similar_refs)}")
            
            # Criar peças similares faltantes
            brand_repo = BrandRepository(conn)
            part_repo = PartRepository(conn)
            
            # Buscar brands existentes
            existing_brands = brand_repo.fetch_all_brands()
            
            # Identificar brands ausentes
            brands_needed = set([brand for _, brand in missing_similar_refs])
            missing_brands = brands_needed - set(existing_brands.keys())
            
            if missing_brands:
                logger.info(f"Criando {len(missing_brands)} brands para peças similares")
                created_brands = brand_repo.bulk_create_missing_brands(missing_brands)
                existing_brands.update(created_brands)
                # Rastrear brands criadas durante similaridades
                stats['similar_brands_created'] = len(created_brands)
                stats['similar_manufacturers_created'] = len(created_brands)  # 1:1 relationship
            
            # Preparar dados das peças similares
            timestamp_now = datetime.now()
            similar_parts_data = []
            
            for sim_ref, sim_brand in missing_similar_refs:
                brand_id = existing_brands[sim_brand][0]
                part_name = main_part_names.get((sim_ref, sim_brand), '')
                
                part_tuple = (
                    sim_ref,        # manufacturer_ref
                    sim_ref,        # search_ref (mesmo valor)
                    part_name,      # name (nome da peça principal)
                    brand_id,       # brand_id
                    None,           # ncm
                    None,           # barcode
                    None,           # gross_weight
                    None,           # width
                    None,           # depth
                    None,           # height
                    None,           # notes
                    '',             # application (string vazia)
                    timestamp_now,  # created
                    timestamp_now,  # updated
                    1,              # status = 1
                    False,          # has_stock
                    False,          # ready_to_p4m
                    '{}',           # p4m_quantity_by_states
                    'not_sent',     # p4m_status
                    '[]',           # p4m_logs
                    False,          # manually_categorized
                    False,          # from_aux_db
                    None,           # born_at = NULL (não usar default do banco)
                    None            # deprecated_at = NULL (não usar default do banco)
                )
                similar_parts_data.append(part_tuple)
            
            # Inserir peças similares
            if similar_parts_data:
                logger.info(f"Inserindo {len(similar_parts_data)} peças similares faltantes")
                inserted_count, inserted_ids = part_repo.bulk_insert_parts(similar_parts_data)
                logger.info(f"Peças similares inseridas: {inserted_count}")
                stats['similar_parts_created'] = inserted_count
                
                # Commit das peças criadas
                conn.commit()
        else:
            logger.info("Todas as peças similares já existem no banco")
    
    # Processar cada registro
    for idx, row in df_with_sim.iterrows():
        try:
            main_ref = row['manufacturer_ref']
            main_brand = row['brand_name_normalized']
            
            # Parsear similaridades com tratamento robusto
            similarities_raw = row['Similaridades']
            similarities_list = None
            
            if isinstance(similarities_raw, str):
                try:
                    similarities_list = json.loads(similarities_raw)
                except json.JSONDecodeError as je:
                    # Tentar com ast.literal_eval para formato Python
                    try:
                        import ast
                        similarities_list = ast.literal_eval(similarities_raw)
                    except (ValueError, SyntaxError) as ae:
                        logger.warning(f"Linha {idx}: Formato inválido de Similaridades - pulando registro. "
                                      f"JSON error: {je}, AST error: {ae}. Valor: {similarities_raw[:100]}")
                        continue
            elif isinstance(similarities_raw, list):
                similarities_list = similarities_raw
            else:
                logger.warning(f"Linha {idx}: Tipo inesperado para Similaridades ({type(similarities_raw)}) - pulando")
                continue
            
            if not isinstance(similarities_list, list) or len(similarities_list) == 0:
                continue
            
            # Coletar todas as refs (peça principal + similares)
            all_refs = [(main_ref, main_brand)]
            for sim in similarities_list:
                if isinstance(sim, dict) and 'search_ref' in sim and 'brand' in sim:
                    sim_ref = str(sim['search_ref']).strip().upper()
                    sim_brand_original = str(sim['brand']).strip().upper()
                    # Aplicar mapeamento de marca
                    sim_brand = apply_brand_mapping(sim_brand_original, brand_mapping)
                    all_refs.append((sim_ref, sim_brand))
            
            # Buscar informações de todas as peças no banco
            parts_info = similarity_repo.fetch_parts_with_similarity(all_refs)
            
            if not parts_info:
                logger.debug(f"Nenhuma peça encontrada no banco para {main_ref} + {main_brand}")
                continue
            
            # Coletar IDs e similarity_ids
            part_ids = [info[0] for info in parts_info.values()]
            similarity_ids = [info[1] for info in parts_info.values() if info[1] is not None]
            unique_similarity_ids = list(set(similarity_ids))
            
            # LÓGICA DE AGRUPAMENTO
            if len(unique_similarity_ids) == 0:
                # Caso 1: Nenhuma peça tem similarity_id - criar novo grupo
                new_similarity_id = similarity_repo.create_similarity_group()
                similarity_repo.update_parts_similarity(part_ids, new_similarity_id)
                stats['groups_created'] += 1
                stats['parts_updated'] += len(part_ids)
                logger.info(f"Novo grupo criado (ID={new_similarity_id}) para {len(part_ids)} peças: {main_ref}+{main_brand}")
            
            elif len(unique_similarity_ids) == 1:
                # Caso 2: Um único ID existente - atribuir a todas
                target_similarity_id = unique_similarity_ids[0]
                parts_without_id = [pid for pid in part_ids 
                                   if parts_info.get(list(parts_info.keys())[part_ids.index(pid)], (None, None))[1] is None]
                
                if parts_without_id:
                    similarity_repo.update_parts_similarity(parts_without_id, target_similarity_id)
                    stats['parts_updated'] += len(parts_without_id)
                    logger.info(f"Atribuído similarity_id={target_similarity_id} a {len(parts_without_id)} peças: {main_ref}+{main_brand}")
            
            else:
                # Caso 3: Múltiplos IDs - usar o menor e migrar todos os outros
                min_similarity_id = min(unique_similarity_ids)
                other_ids = [sid for sid in unique_similarity_ids if sid != min_similarity_id]
                
                logger.info(f"Mesclando grupos {unique_similarity_ids} -> {min_similarity_id} para {main_ref}+{main_brand}")
                
                # Migrar todos os grupos para o menor ID
                for other_id in other_ids:
                    migrated = similarity_repo.migrate_similarity_groups(other_id, min_similarity_id)
                    stats['parts_updated'] += migrated
                    stats['groups_merged'] += 1
                
                # Garantir que as peças atuais também tenham o ID correto
                parts_needing_update = [pid for pid, (ref, brand) in zip(part_ids, parts_info.keys())
                                       if parts_info[(ref, brand)][1] != min_similarity_id]
                
                if parts_needing_update:
                    similarity_repo.update_parts_similarity(parts_needing_update, min_similarity_id)
        
        except Exception as e:
            logger.error(f"Erro ao processar similaridades da linha {idx}: {e}", exc_info=True)
            # ROLLBACK para recuperar transação e permitir continuar processamento
            conn.rollback()
            continue
    
    logger.info(f"Similaridades processadas: {stats['groups_created']} grupos criados, "
                f"{stats['groups_merged']} grupos mesclados, {stats['parts_updated']} peças atualizadas")
    
    return stats

# ============================================================================
# PIPELINE DE INGESTÃO - Orquestrador Principal
# ============================================================================
class PartIngestionPipeline:
    """Orquestrador principal do processo de ingestão de peças"""
    
    def __init__(self, conn: psycopg2.extensions.connection, author_id: int, current_owner_id: int, update_config: UpdateFieldConfig):
        self.conn = conn
        self.brand_repo = BrandRepository(conn)
        self.part_repo = PartRepository(conn)
        self.author_id = author_id
        self.current_owner_id = current_owner_id
        self.update_config = update_config
        self.file_path_cache = None  # Cache do caminho do arquivo para processar similaridades
    
    @timer_decorator
    def ingest_from_excel(self, file_path: str) -> IngestionReport:
        """
        Executa pipeline completo de ingestão com controle transacional
        
        Args:
            file_path: Caminho do arquivo Excel
        
        Returns:
            IngestionReport com métricas do processamento
        """
        start_time = time.time()
        
        try:
            # ================================================================
            # FASE 1: VALIDAÇÃO - Carregar e validar planilha
            # ================================================================
            logger.info("="*80)
            logger.info("FASE 1: VALIDAÇÃO E CARREGAMENTO DE DADOS")
            logger.info("="*80)
            
            df, stats = read_excel(file_path)
            total_rows_original = stats['total_rows_original']
            total_rows_valid = len(df)
            invalid_records = stats['invalid_records']
            duplicates_internal = stats['duplicates_internal']
            
            # ================================================================
            # FASE 2: BRANDS - Buscar brands existentes e identificar ausentes
            # ================================================================
            logger.info("="*80)
            logger.info("FASE 2: RESOLUÇÃO DE BRANDS E MANUFACTURERS")
            logger.info("="*80)
            
            existing_brands = self.brand_repo.fetch_all_brands()
            
            # Identificar brands ausentes
            brands_in_file = set(df['brand_name_normalized'].unique())
            missing_brands = brands_in_file - set(existing_brands.keys())
            
            if missing_brands:
                logger.info(f"Brands ausentes detectadas: {len(missing_brands)}")
                for brand in sorted(missing_brands):
                    logger.info(f"  Brand ausente: {brand}")
            
            # ================================================================
            # FASE 3: CRIAÇÃO - Criar manufacturers e brands ausentes
            # ================================================================
            brands_created = 0
            manufacturers_created = 0
            
            if missing_brands:
                logger.info("="*80)
                logger.info("FASE 3: CRIAÇÃO DE MANUFACTURERS E BRANDS")
                logger.info("="*80)
                
                created_brands = self.brand_repo.bulk_create_missing_brands(missing_brands)
                brands_created = len(created_brands)
                manufacturers_created = brands_created  # 1:1 relationship
                
                # Atualizar dicionário de brands
                existing_brands.update(created_brands)
            
            # ================================================================
            # FASE 4: MAPEAMENTO - Adicionar brand_id ao DataFrame
            # ================================================================
            logger.info("="*80)
            logger.info("FASE 4: MAPEAMENTO DE BRAND IDS")
            logger.info("="*80)
            
            df['brand_id'] = df['brand_name_normalized'].map(lambda x: existing_brands[x][0])
            logger.info(f"Brand IDs mapeados com sucesso para {len(df)} registros")
            
            # ================================================================
            # FASE 5: DETECÇÃO - Buscar peças existentes e separar NEW vs UPDATE
            # ================================================================
            logger.info("="*80)
            logger.info("FASE 5: DETECÇÃO DE PEÇAS EXISTENTES")
            logger.info("="*80)
            
            parts_to_check = list(zip(df['manufacturer_ref'], df['brand_id']))
            existing_parts_set = self.part_repo.fetch_existing_parts(parts_to_check)
            
            # Separar peças novas e existentes
            df['is_duplicate'] = df.apply(
                lambda row: (row['manufacturer_ref'], row['brand_id']) in existing_parts_set, 
                axis=1
            )
            
            df_existing = df[df['is_duplicate']]
            df_new = df[~df['is_duplicate']]
            parts_existing = len(df_existing)
            
            logger.info(f"Peças já existentes (para UPDATE): {parts_existing}")
            logger.info(f"Peças novas (para INSERT): {len(df_new)}")
            
            # ================================================================
            # FASE 6: PREPARAÇÃO - Converter DataFrame para lista de tuplas
            # ================================================================
            logger.info("="*80)
            logger.info("FASE 6: PREPARAÇÃO DOS DADOS PARA INSERÇÃO")
            logger.info("="*80)
            
            parts_data = []
            for _, row in df_new.iterrows():
                timestamp_now = datetime.now()
                
                # Helper para garantir que strings vazias viram None
                def get_clean_string(value):
                    if pd.isna(value):
                        return None
                    str_val = str(value).strip()
                    return str_val if str_val else None
                
                # Helper para garantir que valores numéricos 0 viram None
                def get_clean_numeric(value):
                    if pd.isna(value):
                        return None
                    try:
                        num_val = float(value)
                        return num_val if num_val != 0 else None
                    except (ValueError, TypeError):
                        return None
                
                # name é NOT NULL no banco - usar string vazia como fallback
                name_value = get_clean_string(row['name']) or ''
                
                part_tuple = (
                    row['manufacturer_ref'],
                    row['search_ref'],
                    name_value,  # Garantido não ser None
                    row['brand_id'],
                    get_clean_string(row['ncm']),
                    get_clean_string(row['barcode']),
                    get_clean_numeric(row['gross_weight']),
                    get_clean_numeric(row['width']),
                    get_clean_numeric(row['depth']),
                    get_clean_numeric(row['height']),
                    get_clean_string(row['notes']),
                    get_clean_string(row['application']) or '',  # String vazia se NULL (mantido para compatibilidade)
                    timestamp_now,  # created
                    timestamp_now,  # updated (mesmo valor de created)
                    1,              # status = 1
                    False,          # has_stock = False
                    False,          # ready_to_p4m = False
                    '{}',           # p4m_quantity_by_states = {} (jsonb vazio)
                    'not_sent',     # p4m_status = 'not_sent'
                    '[]',           # p4m_logs = [] (jsonb array vazio)
                    False,          # manually_categorized = False
                    False,          # from_aux_db = False
                    None,           # born_at = NULL (não usar default do banco)
                    None            # deprecated_at = NULL (não usar default do banco)
                )
                parts_data.append(part_tuple)
            
            logger.info(f"Preparados {len(parts_data)} registros para bulk insert")
            
            # ================================================================
            # FASE 6.5: UPDATE - Atualizar peças existentes
            # ================================================================
            logger.info("="*80)
            logger.info("FASE 6.5: ATUALIZAÇÃO DE PEÇAS EXISTENTES")
            logger.info("="*80)
            
            parts_inserted = 0  # Inicializar contador
            parts_updated = 0
            fields_updated = 0
            update_activities = []
            
            if len(df_existing) > 0:
                # Buscar detalhes completos das peças existentes
                existing_parts_keys = list(zip(df_existing['manufacturer_ref'], df_existing['brand_id']))
                updatable_fields = self.update_config.get_updatable_fields()
                
                if not updatable_fields:
                    logger.info("Nenhum campo configurado para atualização - pulando update")
                else:
                    existing_parts_details = self.part_repo.fetch_parts_details(existing_parts_keys, updatable_fields)
                    
                    updates_to_apply = []
                    
                    # Processar cada peça existente
                    for _, row in df_existing.iterrows():
                        key = (row['manufacturer_ref'], row['brand_id'])
                        current_part = existing_parts_details.get(key)
                        
                        if not current_part:
                            logger.warning(f"Peça não encontrada nos detalhes: {key}")
                            continue
                        
                        part_id = current_part['id']
                        field_updates = {}
                        
                        # Comparar cada campo atualizável
                        for field_name in updatable_fields:
                            current_value = current_part.get(field_name)
                            new_value = row.get(field_name)
                            
                            should_update, reason = self.update_config.should_update_field(
                                field_name, current_value, new_value
                            )
                        
                        if should_update:
                            # Determinar valor final
                            if reason == 'concatenate':
                                # Concatenar valores com quebra de linha dupla
                                final_value = f"{current_value}\n\n{new_value}"
                            else:
                                # Substituir
                                final_value = new_value
                            
                            field_updates[field_name] = final_value
                            fields_updated += 1
                            
                            # Registrar activity
                            update_activities.append({
                                'part_id': part_id,
                                'attribute': field_name,
                                'previous_value': current_value,
                                'current_value': final_value
                            })
                            
                            logger.debug(f"UPDATE: Part {part_id} | {field_name}: '{current_value}' -> '{final_value}' (reason: {reason})")
                    
                    if field_updates:
                        updates_to_apply.append({
                            'part_id': part_id,
                            'field_updates': field_updates
                        })
                
                    # Aplicar updates
                    if updates_to_apply:
                        parts_updated = self.part_repo.bulk_update_parts(updates_to_apply)
                        logger.info(f"Atualizadas {parts_updated} peças com {fields_updated} campos modificados")
                    else:
                        logger.info("Nenhuma peça necessita atualização")
                logger.info("Nenhuma peça existente para atualizar")
            
            # ================================================================
            # FASE 7: INSERÇÃO - Bulk insert de peças novas
            # ================================================================
            logger.info("="*80)
            logger.info("FASE 7: INSERÇÃO EM LOTE DE PEÇAS")
            logger.info("="*80)
            
            parts_inserted, inserted_part_ids = self.part_repo.bulk_insert_parts(parts_data)
            
            # ================================================================
            # FASE 7.5: REGISTRO DE ACTIVITIES - Criar PartActivity para peças inseridas
            # ================================================================
            logger.info("="*80)
            logger.info("FASE 7.5: REGISTRO DE ACTIVITIES (PartActivity)")
            logger.info("="*80)
            
            part_activities_created = 0
            if inserted_part_ids:
                # Criar activities usando current_owner_id fixo
                part_activities_created = self.part_repo.bulk_insert_part_activities(
                    inserted_part_ids,
                    self.author_id,
                    self.current_owner_id
                )
            
            # Criar activities de UPDATE
            if update_activities:
                update_activities_count = self.part_repo.bulk_insert_update_activities(
                    update_activities,
                    self.author_id,
                    self.current_owner_id
                )
                part_activities_created += update_activities_count
            
            # ================================================================
            # COMMIT TRANSACIONAL
            # ================================================================
            self.conn.commit()
            logger.info("Transação commitada com sucesso!")
            
            # ================================================================
            # GERAR RELATÓRIO FINAL
            # ================================================================
            execution_time = time.time() - start_time
            
            report = IngestionReport(
                total_rows_original=total_rows_original,
                total_rows_valid=total_rows_valid,
                invalid_records=invalid_records,
                duplicates_internal=duplicates_internal,
                brands_created=brands_created,
                manufacturers_created=manufacturers_created,
                parts_existing=parts_existing,
                parts_inserted=parts_inserted,
                parts_updated=parts_updated,
                fields_updated=fields_updated,
                execution_time=execution_time,
                part_activities_created=part_activities_created
            )
            
            # Adicionar estatísticas de similaridades se processadas
            if 'Similaridades' in df.columns:
                try:
                    similarity_stats = process_similarities(self.conn, df, file_path)
                    if similarity_stats['processed']:
                        report.has_similarities = True
                        report.similarity_groups_created = similarity_stats.get('groups_created', 0)
                        report.similarity_groups_merged = similarity_stats.get('groups_merged', 0)
                        report.similarity_parts_updated = similarity_stats.get('parts_updated', 0)
                        report.similar_parts_created = similarity_stats.get('similar_parts_created', 0)
                        report.similar_brands_created = similarity_stats.get('similar_brands_created', 0)
                        report.similar_manufacturers_created = similarity_stats.get('similar_manufacturers_created', 0)
                        # Somar peças/brands/manufacturers criados nas similaridades ao total
                        report.parts_inserted += report.similar_parts_created
                        report.brands_created += report.similar_brands_created
                        report.manufacturers_created += report.similar_manufacturers_created
                        self.conn.commit()
                        logger.info("Similaridades processadas e commitadas com sucesso!")
                except Exception as e:
                    logger.error(f"Erro ao processar similaridades: {e}", exc_info=True)
                    logger.warning("Rollback do processamento de similaridades")
                    self.conn.rollback()
            
            return report
            
        except Exception as e:
            logger.error(f"ERRO NO PIPELINE: {e}", exc_info=True)
            logger.warning("Executando ROLLBACK da transação")
            self.conn.rollback()
            raise

# ============================================================================
# FUNÇÃO DE RELATÓRIO
# ============================================================================
def print_ingestion_report(report: IngestionReport):
    """Imprime relatório formatado do processamento"""
    
    success_rate = (report.parts_inserted / report.total_rows_original * 100) if report.total_rows_original > 0 else 0
    
    # Montar seção de similaridades se existir
    similarity_section = ""
    if report.has_similarities:
        similarity_section = f"""
🔗 SIMILARIDADES:
{'─'*80}
➕ Peças Similares Criadas:  {report.similar_parts_created:,}
✨ Brands Criadas:           {report.similar_brands_created:,}
🏭 Manufacturers Criados:    {report.similar_manufacturers_created:,}
✨ Grupos Criados:           {report.similarity_groups_created:,}
🔀 Grupos Mesclados:         {report.similarity_groups_merged:,}
✅ Peças Atualizadas:        {report.similarity_parts_updated:,}

"""
    
    report_text = f"""
{'='*80}
📦 RELATÓRIO FINAL DE INGESTÃO DE PEÇAS
{'='*80}
🕐 Timestamp:                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⏱️  Tempo Total:              {report.execution_time:.2f}s

📊 ESTATÍSTICAS DE PROCESSAMENTO:
{'─'*80}
📥 Total na Planilha:        {report.total_rows_original:,} registros
❌ Registros Inválidos:      {report.invalid_records:,} registros (SKU/Brand NAN/vazio)
🔄 Duplicatas Internas:      {report.duplicates_internal:,} registros (mesmo SKU+Brand)
✅ Registros Válidos:        {report.total_rows_valid:,} registros

🏭 MANUFACTURERS & BRANDS:
{'─'*80}
✨ Manufacturers Criados:    {report.manufacturers_created:,}
✨ Brands Criadas:           {report.brands_created:,}

🔧 PEÇAS (CATALOG_PART):
{'─'*80}
➕ Inseridas (novas):        {report.parts_inserted:,} peças
🔄 Atualizadas (existentes): {report.parts_updated:,} peças
📊 Campos Modificados:       {report.fields_updated:,} campos
⏭️  Já Existentes (sem mudanças): {report.parts_existing - report.parts_updated:,} peças

📝 ACTIVITIES (PART_ACTIVITY):
{'─'*80}
✨ Activities Criadas:       {report.part_activities_created:,} registros (CREATION + UPDATE)

{similarity_section}📈 TAXA DE SUCESSO:          {success_rate:.2f}%
{'='*80}
    """
    
    print(report_text)
    logger.info("Relatório final gerado com sucesso")

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================
def get_user_by_email(conn: psycopg2.extensions.connection, email: str) -> Optional[int]:
    """
    Busca user_id pelo email
    
    Args:
        conn: Conexão com banco de dados
        email: Email do usuário
    
    Returns:
        ID do usuário ou None se não encontrado
    """
    cursor = conn.cursor()
    try:
        query = """
            SELECT id, email, first_name, last_name
            FROM authentication_user
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
            LIMIT 1
        """
        cursor.execute(query, (email,))
        result = cursor.fetchone()
        
        if result:
            user_id, user_email, first_name, last_name = result
            logger.info(f"Usuário encontrado: ID={user_id}, Email={user_email}, Nome={first_name} {last_name}")
            return user_id
        else:
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar usuário: {e}", exc_info=True)
        return None
    finally:
        cursor.close()

def get_manufacturer_by_name(conn: psycopg2.extensions.connection, manufacturer_name: str) -> Optional[int]:
    """
    Busca manufacturer_id pelo nome (case-insensitive)
    
    Args:
        conn: Conexão com banco de dados
        manufacturer_name: Nome do manufacturer a buscar
    
    Returns:
        ID do manufacturer ou None se não encontrado
    """
    cursor = conn.cursor()
    try:
        query = """
            SELECT id, name, commercial_name 
            FROM manufacturer_manufacturer 
            WHERE UPPER(TRIM(name)) = UPPER(TRIM(%s)) 
               OR UPPER(TRIM(commercial_name)) = UPPER(TRIM(%s))
            LIMIT 1
        """
        cursor.execute(query, (manufacturer_name, manufacturer_name))
        result = cursor.fetchone()
        
        if result:
            manufacturer_id, name, commercial_name = result
            logger.info(f"Manufacturer encontrado: ID={manufacturer_id}, Name={name}, Commercial={commercial_name}")
            return manufacturer_id
        else:
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar manufacturer: {e}", exc_info=True)
        return None
    finally:
        cursor.close()

def list_available_manufacturers(conn: psycopg2.extensions.connection) -> List[Tuple[int, str]]:
    """
    Lista todos os manufacturers disponíveis no banco
    
    Returns:
        Lista de tuplas (id, name)
    """
    cursor = conn.cursor()
    try:
        query = """
            SELECT id, COALESCE(commercial_name, name) as display_name
            FROM manufacturer_manufacturer
            ORDER BY display_name
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Erro ao listar manufacturers: {e}", exc_info=True)
        return []
    finally:
        cursor.close()

def configure_update_fields() -> UpdateFieldConfig:
    """
    Solicita ao usuário configuração de campos para atualização
    
    Returns:
        UpdateFieldConfig configurado
    """
    print("\n" + "="*80)
    print("CONFIGURAÇÃO DE ATUALIZAÇÃO DE CAMPOS")
    print("="*80)
    print("\nCampos disponíveis para atualização:")
    for i, field in enumerate(UpdateFieldConfig.AVAILABLE_FIELDS, 1):
        print(f"  {i}. {field}")
    
    print("\n" + "-"*80)
    print("Instruções:")
    print("  - Digite os números dos campos separados por vírgula")
    print("  - Exemplo: 1,3,5 ou deixe vazio para nenhum")
    print("-"*80)
    
    # Solicitar campos FORCE_OVERRIDE
    print("\n📌 CAMPOS COM SUBSTITUIÇÃO FORÇADA (sempre substituem o valor atual):")
    override_input = input("Digite os números (ou Enter para pular): ").strip()
    force_override = []
    if override_input:
        try:
            indices = [int(x.strip()) for x in override_input.split(',')]
            force_override = [UpdateFieldConfig.AVAILABLE_FIELDS[i-1] for i in indices if 1 <= i <= len(UpdateFieldConfig.AVAILABLE_FIELDS)]
            print(f"✅ Campos selecionados: {', '.join(force_override) if force_override else 'nenhum'}")
        except (ValueError, IndexError) as e:
            print(f"❌ Entrada inválida: {e}. Nenhum campo será forçado.")
    
    # Solicitar campos CONCATENATE
    print("\n🔗 CAMPOS COM CONCATENAÇÃO (juntam valores com \\n\\n):")
    concat_input = input("Digite os números (ou Enter para pular): ").strip()
    concatenate = []
    if concat_input:
        try:
            indices = [int(x.strip()) for x in concat_input.split(',')]
            concatenate = [UpdateFieldConfig.AVAILABLE_FIELDS[i-1] for i in indices if 1 <= i <= len(UpdateFieldConfig.AVAILABLE_FIELDS)]
            print(f"✅ Campos selecionados: {', '.join(concatenate) if concatenate else 'nenhum'}")
        except (ValueError, IndexError) as e:
            print(f"❌ Entrada inválida: {e}. Nenhum campo será concatenado.")
    
    # Solicitar campos UPDATE_IF_EMPTY
    print("\n📌 CAMPOS COM PREENCHIMENTO SE VAZIO (atualizam apenas se NULL/0/vazio):")
    update_empty_input = input("Digite os números (ou Enter para pular): ").strip()
    update_if_empty = []
    if update_empty_input:
        try:
            indices = [int(x.strip()) for x in update_empty_input.split(',')]
            update_if_empty = [UpdateFieldConfig.AVAILABLE_FIELDS[i-1] for i in indices if 1 <= i <= len(UpdateFieldConfig.AVAILABLE_FIELDS)]
            print(f"✅ Campos selecionados: {', '.join(update_if_empty) if update_if_empty else 'nenhum'}")
        except (ValueError, IndexError) as e:
            print(f"❌ Entrada inválida: {e}. Nenhum campo será preenchido se vazio.")
    
    # Validar overlaps
    all_configured_temp = set(force_override + concatenate + update_if_empty)
    if len(all_configured_temp) < len(force_override) + len(concatenate) + len(update_if_empty):
        # Há duplicações - remover de concatenate e update_if_empty (prioridade: force_override)
        overlap_force_concat = set(force_override) & set(concatenate)
        overlap_force_empty = set(force_override) & set(update_if_empty)
        overlap_concat_empty = set(concatenate) & set(update_if_empty)
        
        if overlap_force_concat:
            print(f"\n⚠️  AVISO: Campos duplicados removidos de CONCATENATE: {', '.join(overlap_force_concat)}")
            concatenate = [f for f in concatenate if f not in overlap_force_concat]
        
        if overlap_force_empty:
            print(f"\n⚠️  AVISO: Campos duplicados removidos de UPDATE_IF_EMPTY: {', '.join(overlap_force_empty)}")
            update_if_empty = [f for f in update_if_empty if f not in overlap_force_empty]
        
        if overlap_concat_empty:
            print(f"\n⚠️  AVISO: Campos duplicados removidos de UPDATE_IF_EMPTY (prioridade CONCATENATE): {', '.join(overlap_concat_empty)}")
            update_if_empty = [f for f in update_if_empty if f not in overlap_concat_empty]
    
    # Calcular campos ignorados
    all_configured = set(force_override + concatenate + update_if_empty)
    ignored = [f for f in UpdateFieldConfig.AVAILABLE_FIELDS if f not in all_configured]
    
    print("\n" + "="*80)
    print("RESUMO DA CONFIGURAÇÃO:")
    print("="*80)
    print(f"📌 SUBSTITUIÇÃO FORÇADA:     {', '.join(force_override) if force_override else 'nenhum'}")
    print(f"🔗 CONCATENAÇÃO:             {', '.join(concatenate) if concatenate else 'nenhum'}")
    print(f"📌 PREENCHER SE VAZIO:       {', '.join(update_if_empty) if update_if_empty else 'nenhum'}")
    print(f"❌ IGNORADOS (não serão atualizados): {', '.join(ignored) if ignored else 'nenhum'}")
    print("="*80 + "\n")
    
    return UpdateFieldConfig(force_override=force_override, concatenate=concatenate, update_if_empty=update_if_empty)

# ============================================================================
# FUNÇÃO MAIN
# ============================================================================
def main():
    """Função principal de execução"""
    logger.info("="*80)
    logger.info("INICIANDO PIPELINE DE INGESTÃO DE PEÇAS")
    logger.info("="*80)
    
    # Configuração hardcoded do arquivo
    FILE_PATH = '/mnt/c/Users/JF/OneDrive/Documentos/Hubbi/paccini-estoque-consolidado.xlsx'
    AUTHOR_EMAIL = 'devhubbi@gmail.com'  # Email do usuário que executa a importação
    
    conn = None
    try:
        # ================================================================
        # CONFIGURAR CAMPOS DE ATUALIZAÇÃO
        # ================================================================
        update_config = configure_update_fields()
        
        # Conectar ao banco
        logger.info(f"Conectando ao banco: {db_config['database']}@{db_config['host']}")
        conn = connect_db(db_config)
        
        # ================================================================
        # BUSCAR AUTOR POR EMAIL
        # ================================================================
        logger.info(f"Buscando usuário autor: {AUTHOR_EMAIL}")
        AUTHOR_ID = get_user_by_email(conn, AUTHOR_EMAIL)
        
        if AUTHOR_ID is None:
            logger.error(f"Usuário com email '{AUTHOR_EMAIL}' não encontrado no banco")
            print(f"\n❌ ERRO: Usuário '{AUTHOR_EMAIL}' não encontrado no banco de dados.")
            print("Por favor, verifique se o email está correto ou crie o usuário no sistema.\n")
            return
        
        # ================================================================
        # SOLICITAR CURRENT_OWNER (Fornecedor das Informações)
        # ================================================================
        print("\n" + "="*80)
        print("CONFIGURAÇÃO DO FORNECEDOR DAS INFORMAÇÕES (CURRENT_OWNER)")
        print("="*80)
        
        # Listar manufacturers disponíveis
        manufacturers = list_available_manufacturers(conn)
        if manufacturers:
            print("\nManufacturers disponíveis no banco:")
            for mf_id, mf_name in manufacturers[:20]:  # Mostrar apenas os primeiros 20
                print(f"  - {mf_name} (ID: {mf_id})")
            if len(manufacturers) > 20:
                print(f"  ... e mais {len(manufacturers) - 20} manufacturers")
        
        # Solicitar nome do manufacturer
        current_owner_id = None
        while current_owner_id is None:
            owner_name = input("\nDigite o nome do FORNECEDOR das informações (current_owner): ").strip()
            
            if not owner_name:
                print("❌ Nome não pode ser vazio. Tente novamente.")
                continue
            
            current_owner_id = get_manufacturer_by_name(conn, owner_name)
            
            if current_owner_id is None:
                print(f"❌ Manufacturer '{owner_name}' não encontrado no banco.")
                create_new = input("Deseja criar um novo manufacturer? (s/n): ").strip().lower()
                
                if create_new == 's':
                    # Criar novo manufacturer
                    cursor = conn.cursor()
                    try:
                        cursor.execute("""
                            INSERT INTO manufacturer_manufacturer (name, commercial_name, names, role, cnpj, created)
                            VALUES (%s, %s, ARRAY[%s], 4, NULL, NOW())
                            RETURNING id
                        """, (owner_name, owner_name, owner_name))
                        current_owner_id = cursor.fetchone()[0]
                        conn.commit()
                        logger.info(f"Novo manufacturer criado: {owner_name} (ID={current_owner_id})")
                        print(f"✅ Manufacturer '{owner_name}' criado com sucesso! (ID={current_owner_id})")
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"Erro ao criar manufacturer: {e}", exc_info=True)
                        print(f"❌ Erro ao criar manufacturer: {e}")
                    finally:
                        cursor.close()
        
        print(f"\n✅ Fornecedor configurado: ID={current_owner_id}")
        print("="*80 + "\n")
        
        # Instanciar pipeline com author_id, current_owner_id e update_config
        logger.info(f"Autor da importação: User ID = {AUTHOR_ID}")
        logger.info(f"Fornecedor das informações: Manufacturer ID = {current_owner_id}")
        logger.info(f"Campos configurados para atualização: {update_config.get_updatable_fields()}")
        pipeline = PartIngestionPipeline(conn, AUTHOR_ID, current_owner_id, update_config)
        
        # Executar ingestão
        report = pipeline.ingest_from_excel(FILE_PATH)
        
        # Imprimir relatório
        print_ingestion_report(report)
        
        logger.info("PROCESSAMENTO CONCLUÍDO COM SUCESSO! ✅")
        
    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {FILE_PATH}")
    except Exception as e:
        logger.error(f"Erro inesperado: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("Conexão com banco fechada")

if __name__ == "__main__":
    main() 