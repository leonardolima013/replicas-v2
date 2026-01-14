"""
Serviço de Publicação de Dados Validados para Banco de Produção.
Autor: Sistema de Validação de Dados
Versão: 1.0
Descrição: Pipeline completo para publicar dados do DuckDB no PostgreSQL de produção.
           Inclui criação de brands/manufacturers, inserção/atualização de peças,
           processamento de similaridades e controle transacional com rollback.
"""

import psycopg2
import psycopg2.extras
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
import time
import json
import os

from backend.services.data_validation import duck_manager
from backend.services.data_validation.production_db import (
    get_production_connection, 
    get_all_brands,
    production_connection
)
from backend.services.data_validation.publish_schemas import (
    PublishConfiguration,
    PublishPreviewResponse,
    PublishResult,
    BrandToCreate,
    SimilarityPreview
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURAÇÃO DE ATUALIZAÇÃO DE CAMPOS (adaptado do create_and_upload_parts.py)
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
        'name', 'ncm', 'barcode', 'gross_weight', 'net_weight',
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
    
    @classmethod
    def from_publish_config(cls, config: PublishConfiguration) -> 'UpdateFieldConfig':
        """Cria UpdateFieldConfig a partir de PublishConfiguration"""
        return cls(
            force_override=config.force_override,
            concatenate=config.concatenate,
            update_if_empty=config.update_if_empty
        )
    
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
            if self._is_empty(current_value):
                return True, "concatenate_empty"
            if str(current_value).strip() == str(new_value).strip():
                return False, "no_change"
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
# DATACLASS PARA RELATÓRIO DE INGESTÃO
# ============================================================================

@dataclass
class IngestionReport:
    """Relatório de métricas do processo de ingestão"""
    total_rows_processed: int = 0
    invalid_records_skipped: int = 0
    brands_created: int = 0
    manufacturers_created: int = 0
    parts_existing: int = 0
    parts_inserted: int = 0
    parts_updated: int = 0
    parts_skipped: int = 0
    fields_updated: int = 0
    execution_time: float = 0.0
    # Similaridades
    has_similarities: bool = False
    similarity_groups_created: int = 0
    similarity_groups_merged: int = 0
    similarity_parts_updated: int = 0
    # Activities
    activities_created: int = 0
    # Erros e avisos
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# ============================================================================
# FUNÇÕES DE SANITIZAÇÃO
# ============================================================================

def sanitize_string_value(value) -> Optional[str]:
    """Sanitiza valores string removendo NaN, 'nan', strings vazias e '0'"""
    if value is None:
        return None
    
    str_value = str(value).strip()
    
    if str_value.upper() in ('NAN', '', '0', 'NONE', 'NULL'):
        return None
    
    return str_value


def sanitize_numeric_value(value) -> Optional[float]:
    """Sanitiza valores numéricos removendo NaN e zeros"""
    if value is None:
        return None
    
    try:
        float_value = float(value)
        if float_value == 0:
            return None
        return float_value
    except (ValueError, TypeError):
        return None


def format_ncm(value) -> Optional[str]:
    """Formata NCM no padrão XXXX.XX.XX"""
    if value is None:
        return None
    
    ncm_str = str(value).strip()
    
    if ncm_str.upper() in ('NAN', '', '0', 'NONE'):
        return None
    
    if ncm_str.endswith('.0'):
        ncm_str = ncm_str[:-2]
    
    ncm_digits = ncm_str.replace('.', '').replace('-', '')
    
    if not ncm_digits.isdigit():
        return None
    
    if len(ncm_digits) != 8:
        return None
    
    return f"{ncm_digits[:4]}.{ncm_digits[4:6]}.{ncm_digits[6:8]}"


# ============================================================================
# BRAND REPOSITORY
# ============================================================================

class BrandRepository:
    """Repository para operações com manufacturer e manufacturer_brand"""
    
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn
    
    def fetch_all_brands(self) -> Dict[str, Tuple[int, int]]:
        """
        Busca todas as brands do banco
        
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
            return {row[0]: (row[1], row[2]) for row in results}
        finally:
            cursor.close()
    
    def bulk_create_missing_brands(self, missing_brands: Set[str]) -> Dict[str, Tuple[int, int]]:
        """
        Cria manufacturers e brands ausentes em lote
        
        Args:
            missing_brands: Set de nomes de brands a serem criadas
        
        Returns:
            Dict[brand_name, (brand_id, manufacturer_id)]
        """
        if not missing_brands:
            return {}
        
        cursor = self.conn.cursor()
        created_brands = {}
        
        try:
            for brand_name in missing_brands:
                # Criar manufacturer
                cursor.execute("""
                    INSERT INTO manufacturer_manufacturer (name, commercial_name, names, role, cnpj, created) 
                    VALUES (%s, %s, ARRAY[%s], 4, NULL, NOW()) 
                    RETURNING id
                """, (brand_name, brand_name, brand_name))
                
                manufacturer_id = cursor.fetchone()[0]
                
                # Criar brand
                cursor.execute("""
                    INSERT INTO manufacturer_brand (name, manufacturer_id, created, asset_id) 
                    VALUES (%s, %s, NOW(), NULL) 
                    RETURNING id
                """, (brand_name, manufacturer_id))
                
                brand_id = cursor.fetchone()[0]
                created_brands[brand_name] = (brand_id, manufacturer_id)
                logger.debug(f"Criado: Brand '{brand_name}' (brand_id={brand_id}, manufacturer_id={manufacturer_id})")
            
            return created_brands
        finally:
            cursor.close()


# ============================================================================
# PART REPOSITORY
# ============================================================================

class PartRepository:
    """Repository para operações com catalog_part"""
    
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn
    
    def fetch_existing_parts(self, parts_to_check: List[Tuple[str, int]]) -> Set[Tuple[str, int]]:
        """
        Busca peças existentes no banco
        
        Args:
            parts_to_check: Lista de tuplas (search_ref, brand_id)
        
        Returns:
            Set de tuplas que já existem
        """
        if not parts_to_check:
            return set()
        
        cursor = self.conn.cursor()
        existing_parts = set()
        
        try:
            batch_size = 1000
            for i in range(0, len(parts_to_check), batch_size):
                batch = parts_to_check[i:i + batch_size]
                query = """
                    SELECT manufacturer_ref, brand_id 
                    FROM catalog_part 
                    WHERE (manufacturer_ref, brand_id) IN %s
                """
                cursor.execute(query, (tuple(batch),))
                results = cursor.fetchall()
                existing_parts.update(results)
            
            return existing_parts
        finally:
            cursor.close()
    
    def fetch_parts_details(self, parts_to_fetch: List[Tuple[str, int]], updatable_fields: List[str]) -> Dict[Tuple[str, int], Dict]:
        """
        Busca detalhes completos de peças existentes
        
        Args:
            parts_to_fetch: Lista de tuplas (manufacturer_ref, brand_id)
            updatable_fields: Lista de campos a buscar
        
        Returns:
            Dict[(manufacturer_ref, brand_id), {campo: valor}]
        """
        if not parts_to_fetch or not updatable_fields:
            return {}
        
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        parts_dict = {}
        
        try:
            batch_size = 1000
            fields_str = ', '.join(['id', 'manufacturer_ref', 'brand_id'] + updatable_fields)
            
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
            
            return parts_dict
        finally:
            cursor.close()
    
    def bulk_insert_parts(self, parts_data: List[Tuple]) -> Tuple[int, List[int]]:
        """
        Insere peças em lote
        
        Args:
            parts_data: Lista de tuplas com dados das peças
        
        Returns:
            Tupla (quantidade inserida, lista de IDs)
        """
        if not parts_data:
            return 0, []
        
        cursor = self.conn.cursor()
        try:
            query = """
                INSERT INTO catalog_part 
                (manufacturer_ref, search_ref, name, brand_id, ncm, barcode, 
                 gross_weight, net_weight, width, depth, height, notes, application, 
                 created, updated, status, has_stock, ready_to_p4m,
                 p4m_quantity_by_states, p4m_status, p4m_logs, manually_categorized, 
                 from_aux_db, born_at, deprecated_at)
                VALUES %s
                RETURNING id
            """
            
            psycopg2.extras.execute_values(
                cursor, 
                query, 
                parts_data, 
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                page_size=1000,
                fetch=True
            )
            
            inserted_ids = [row[0] for row in cursor.fetchall()]
            return len(inserted_ids), inserted_ids
        finally:
            cursor.close()
    
    def bulk_update_parts(self, updates: List[Dict]) -> int:
        """
        Atualiza campos de peças existentes
        
        Args:
            updates: Lista de dicts com {part_id, field_updates: {campo: valor}}
        
        Returns:
            Quantidade de peças atualizadas
        """
        if not updates:
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
                
                set_clauses = []
                values = []
                
                for field_name, new_value in field_updates.items():
                    set_clauses.append(f"{field_name} = %s")
                    values.append(new_value)
                
                set_clauses.append("updated = %s")
                values.append(timestamp_now)
                values.append(part_id)
                
                query = f"""
                    UPDATE catalog_part
                    SET {', '.join(set_clauses)}
                    WHERE id = %s
                """
                cursor.execute(query, values)
                updated_count += cursor.rowcount
            
            return updated_count
        finally:
            cursor.close()
    
    def bulk_insert_part_activities(self, part_ids: List[int], author_id: int, current_owner_id: int) -> int:
        """
        Registra activities de CREATION para peças inseridas
        
        Args:
            part_ids: Lista de IDs das peças inseridas
            author_id: ID do usuário autor
            current_owner_id: ID do manufacturer fornecedor
        
        Returns:
            Quantidade de activities criadas
        """
        if not part_ids:
            return 0
        
        cursor = self.conn.cursor()
        try:
            timestamp_now = datetime.now()
            activities_data = [
                (part_id, 'CRE', author_id, 'all', None, None, None, current_owner_id, timestamp_now)
                for part_id in part_ids
            ]
            
            query = """
                INSERT INTO catalog_partactivity 
                (part_id, activity_type, author_id, attribute, previous_value, 
                 previous_owner_id, current_value, current_owner_id, created)
                VALUES %s
            """
            
            psycopg2.extras.execute_values(
                cursor,
                query,
                activities_data,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                page_size=1000
            )
            
            return cursor.rowcount
        finally:
            cursor.close()
    
    def bulk_insert_update_activities(self, activities_data: List[Dict], author_id: int, current_owner_id: int) -> int:
        """
        Registra activities de UPDATE
        
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
            
            activities_tuples = [
                (
                    item['part_id'],
                    'UPD',
                    author_id,
                    item['attribute'],
                    str(item['previous_value']) if item['previous_value'] is not None else None,
                    None,
                    str(item['current_value']) if item['current_value'] is not None else None,
                    current_owner_id,
                    timestamp_now
                )
                for item in activities_data
            ]
            
            query = """
                INSERT INTO catalog_partactivity
                (part_id, activity_type, author_id, attribute, previous_value, 
                 previous_owner_id, current_value, current_owner_id, created)
                VALUES %s
            """
            
            psycopg2.extras.execute_values(
                cursor,
                query,
                activities_tuples,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                page_size=1000
            )
            
            return cursor.rowcount
        finally:
            cursor.close()


# ============================================================================
# SIMILARITY REPOSITORY
# ============================================================================

class SimilarityRepository:
    """Repository para operações com catalog_similarity"""
    
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn
    
    def fetch_parts_with_similarity(self, parts_refs: List[Tuple[str, str]]) -> Dict[Tuple[str, str], Tuple[int, Optional[int]]]:
        """
        Busca part_id e similarity_id de peças
        
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
            logger.error(f"Erro ao buscar peças com similaridade: {e}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()
    
    def create_similarity_group(self) -> int:
        """Cria um novo grupo de similaridade"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM catalog_similarity")
            next_id = cursor.fetchone()[0]
            
            cursor.execute("""
                INSERT INTO catalog_similarity (id, created)
                VALUES (%s, NOW())
                RETURNING id
            """, (next_id,))
            
            similarity_id = cursor.fetchone()[0]
            
            cursor.execute("SELECT setval('catalog_similarity_id_seq', %s, true)", (similarity_id,))
            
            return similarity_id
        finally:
            cursor.close()
    
    def update_parts_similarity(self, part_ids: List[int], similarity_id: int) -> int:
        """Atualiza similarity_id de múltiplas peças"""
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
            return cursor.rowcount
        finally:
            cursor.close()
    
    def migrate_similarity_groups(self, from_id: int, to_id: int) -> int:
        """Migra peças de um grupo de similaridade para outro"""
        cursor = self.conn.cursor()
        try:
            query = """
                UPDATE catalog_part
                SET similarity_id = %s, updated = NOW()
                WHERE similarity_id = %s
            """
            cursor.execute(query, (to_id, from_id))
            return cursor.rowcount
        finally:
            cursor.close()


# ============================================================================
# PIPELINE DE PUBLICAÇÃO
# ============================================================================

class PublishPipeline:
    """Pipeline principal para publicação de dados validados"""
    
    def __init__(
        self,
        conn: psycopg2.extensions.connection,
        author_id: int,
        current_owner_id: int,
        update_config: UpdateFieldConfig
    ):
        self.conn = conn
        self.brand_repo = BrandRepository(conn)
        self.part_repo = PartRepository(conn)
        self.similarity_repo = SimilarityRepository(conn)
        self.author_id = author_id
        self.current_owner_id = current_owner_id
        self.update_config = update_config
    
    def execute(self, project_id: str) -> IngestionReport:
        """
        Executa pipeline completo de publicação
        
        Args:
            project_id: ID do projeto no DuckDB
        
        Returns:
            IngestionReport com métricas do processamento
        """
        start_time = time.time()
        report = IngestionReport()
        
        try:
            # Carregar dados do DuckDB
            duck = duck_manager.DuckSession(project_id)
            duck_conn = duck._get_conn(read_only=True)
            
            # FASE 1: Buscar todos os dados
            logger.info("FASE 1: Carregando dados do DuckDB")
            all_data = duck_conn.execute("SELECT * FROM raw_data").fetchall()
            columns = [desc[0] for desc in duck_conn.execute("SELECT * FROM raw_data LIMIT 0").description]
            
            # Converter para lista de dicts
            data_list = [dict(zip(columns, row)) for row in all_data]
            report.total_rows_processed = len(data_list)
            logger.info(f"Total de registros: {report.total_rows_processed}")
            
            # FASE 2: Preparar dados e resolver brands
            logger.info("FASE 2: Resolvendo brands")
            existing_brands = self.brand_repo.fetch_all_brands()
            
            # Identificar brands únicas no dataset
            brands_in_data = set()
            for row in data_list:
                brand_value = row.get('brand')
                if brand_value:
                    brand_normalized = str(brand_value).strip().upper()
                    if brand_normalized and brand_normalized not in ('NAN', 'NONE', ''):
                        brands_in_data.add(brand_normalized)
            
            # Identificar brands ausentes
            missing_brands = brands_in_data - set(existing_brands.keys())
            
            # FASE 3: Criar brands faltantes
            if missing_brands:
                logger.info(f"FASE 3: Criando {len(missing_brands)} brands")
                created_brands = self.brand_repo.bulk_create_missing_brands(missing_brands)
                report.brands_created = len(created_brands)
                report.manufacturers_created = len(created_brands)
                existing_brands.update(created_brands)
            else:
                logger.info("FASE 3: Nenhuma brand nova para criar")
            
            # FASE 4: Mapear brand_id para cada registro
            logger.info("FASE 4: Mapeando brand_ids")
            valid_data = []
            for row in data_list:
                brand_value = row.get('brand')
                if not brand_value:
                    report.invalid_records_skipped += 1
                    continue
                
                brand_normalized = str(brand_value).strip().upper()
                if brand_normalized in ('NAN', 'NONE', ''):
                    report.invalid_records_skipped += 1
                    continue
                
                brand_info = existing_brands.get(brand_normalized)
                if not brand_info:
                    report.invalid_records_skipped += 1
                    report.warnings.append(f"Brand não encontrada: {brand_normalized}")
                    continue
                
                row['brand_id'] = brand_info[0]
                row['brand_normalized'] = brand_normalized
                valid_data.append(row)
            
            logger.info(f"Registros válidos: {len(valid_data)}")
            
            # FASE 5: Detectar peças existentes
            logger.info("FASE 5: Detectando peças existentes")
            parts_to_check = []
            for row in valid_data:
                search_ref = row.get('search_ref', '').strip().upper()
                brand_id = row.get('brand_id')
                if search_ref and brand_id:
                    parts_to_check.append((search_ref, brand_id))
            
            existing_parts_set = self.part_repo.fetch_existing_parts(parts_to_check)
            
            # Separar novos e existentes
            new_parts_data = []
            existing_parts_data = []
            
            for row in valid_data:
                search_ref = row.get('search_ref', '').strip().upper()
                manufacturer_ref = row.get('manufacturer_ref', '').strip().upper()
                brand_id = row.get('brand_id')
                
                # Validar search_ref
                if not search_ref or len(search_ref) <= 3:
                    report.invalid_records_skipped += 1
                    continue
                
                key = (search_ref, brand_id)
                if key in existing_parts_set:
                    existing_parts_data.append(row)
                else:
                    new_parts_data.append(row)
            
            report.parts_existing = len(existing_parts_data)
            logger.info(f"Peças novas: {len(new_parts_data)}, Peças existentes: {len(existing_parts_data)}")
            
            # FASE 6: Inserir novas peças
            logger.info("FASE 6: Inserindo novas peças")
            if new_parts_data:
                parts_tuples = self._prepare_parts_for_insert(new_parts_data)
                inserted_count, inserted_ids = self.part_repo.bulk_insert_parts(parts_tuples)
                report.parts_inserted = inserted_count
                
                # Criar activities
                if inserted_ids:
                    activities_count = self.part_repo.bulk_insert_part_activities(
                        inserted_ids, self.author_id, self.current_owner_id
                    )
                    report.activities_created += activities_count
            
            # FASE 7: Atualizar peças existentes
            logger.info("FASE 7: Atualizando peças existentes")
            updatable_fields = self.update_config.get_updatable_fields()
            
            if existing_parts_data and updatable_fields:
                existing_keys = [(r.get('search_ref', '').strip().upper(), r.get('brand_id')) 
                                for r in existing_parts_data]
                existing_details = self.part_repo.fetch_parts_details(existing_keys, updatable_fields)
                
                updates_to_apply = []
                update_activities = []
                
                for row in existing_parts_data:
                    search_ref = row.get('search_ref', '').strip().upper()
                    brand_id = row.get('brand_id')
                    key = (search_ref, brand_id)
                    
                    current_part = existing_details.get(key)
                    if not current_part:
                        continue
                    
                    part_id = current_part['id']
                    field_updates = {}
                    
                    for field_name in updatable_fields:
                        current_value = current_part.get(field_name)
                        new_value = self._get_field_value(row, field_name)
                        
                        should_update, reason = self.update_config.should_update_field(
                            field_name, current_value, new_value
                        )
                        
                        if should_update:
                            if reason == 'concatenate' and current_value:
                                final_value = f"{current_value}\n\n{new_value}"
                            else:
                                final_value = new_value
                            
                            field_updates[field_name] = final_value
                            report.fields_updated += 1
                            
                            update_activities.append({
                                'part_id': part_id,
                                'attribute': field_name,
                                'previous_value': current_value,
                                'current_value': final_value
                            })
                    
                    if field_updates:
                        updates_to_apply.append({
                            'part_id': part_id,
                            'field_updates': field_updates
                        })
                
                if updates_to_apply:
                    report.parts_updated = self.part_repo.bulk_update_parts(updates_to_apply)
                    
                    if update_activities:
                        activities_count = self.part_repo.bulk_insert_update_activities(
                            update_activities, self.author_id, self.current_owner_id
                        )
                        report.activities_created += activities_count
                
                report.parts_skipped = len(existing_parts_data) - report.parts_updated
            
            # FASE 8: Processar similaridades
            logger.info("FASE 8: Processando similaridades")
            if 'similarity' in columns:
                similarity_stats = self._process_similarities(valid_data)
                if similarity_stats:
                    report.has_similarities = True
                    report.similarity_groups_created = similarity_stats.get('groups_created', 0)
                    report.similarity_groups_merged = similarity_stats.get('groups_merged', 0)
                    report.similarity_parts_updated = similarity_stats.get('parts_updated', 0)
            
            # COMMIT FINAL
            self.conn.commit()
            logger.info("Transação commitada com sucesso!")
            
            # Fechar conexão DuckDB
            duck_conn.close()
            
            report.execution_time = time.time() - start_time
            return report
            
        except Exception as e:
            logger.error(f"Erro no pipeline de publicação: {e}")
            self.conn.rollback()
            if 'duck_conn' in locals():
                duck_conn.close()
            report.errors.append(str(e))
            report.execution_time = time.time() - start_time
            raise
    
    def _prepare_parts_for_insert(self, parts_data: List[Dict]) -> List[Tuple]:
        """Prepara dados para inserção em bulk"""
        parts_tuples = []
        timestamp_now = datetime.now()
        
        for row in parts_data:
            search_ref = str(row.get('search_ref', '')).strip().upper()
            manufacturer_ref = str(row.get('manufacturer_ref', search_ref)).strip().upper()
            
            part_tuple = (
                manufacturer_ref,
                search_ref,
                sanitize_string_value(row.get('name')) or '',
                row.get('brand_id'),
                format_ncm(row.get('ncm')),
                sanitize_string_value(row.get('barcode')),
                sanitize_numeric_value(row.get('gross_weight')),
                sanitize_numeric_value(row.get('net_weight')),
                sanitize_numeric_value(row.get('width')),
                sanitize_numeric_value(row.get('depth')),
                sanitize_numeric_value(row.get('height')),
                sanitize_string_value(row.get('notes')),
                sanitize_string_value(row.get('application')) or '',
                timestamp_now,  # created
                timestamp_now,  # updated
                1,              # status
                False,          # has_stock
                False,          # ready_to_p4m
                '{}',           # p4m_quantity_by_states
                'not_sent',     # p4m_status
                '[]',           # p4m_logs
                False,          # manually_categorized
                False,          # from_aux_db
                None,           # born_at
                None            # deprecated_at
            )
            parts_tuples.append(part_tuple)
        
        return parts_tuples
    
    def _get_field_value(self, row: Dict, field_name: str) -> Any:
        """Obtém valor sanitizado de um campo"""
        value = row.get(field_name)
        
        if field_name in ('gross_weight', 'net_weight', 'width', 'depth', 'height'):
            return sanitize_numeric_value(value)
        elif field_name == 'ncm':
            return format_ncm(value)
        else:
            return sanitize_string_value(value)
    
    def _process_similarities(self, data_list: List[Dict]) -> Optional[Dict]:
        """Processa coluna similarity para criar grupos"""
        stats = {
            'groups_created': 0,
            'groups_merged': 0,
            'parts_updated': 0
        }
        
        rows_with_similarity = [r for r in data_list if r.get('similarity')]
        
        if not rows_with_similarity:
            return None
        
        for row in rows_with_similarity:
            try:
                main_ref = str(row.get('search_ref', '')).strip().upper()
                main_brand = row.get('brand_normalized', '')
                
                similarity_value = row.get('similarity')
                if not similarity_value:
                    continue
                
                # Tentar parsear JSON
                if isinstance(similarity_value, str):
                    try:
                        similarity_list = json.loads(similarity_value)
                    except json.JSONDecodeError:
                        continue
                elif isinstance(similarity_value, list):
                    similarity_list = similarity_value
                else:
                    continue
                
                if not similarity_list:
                    continue
                
                # Coletar refs
                all_refs = [(main_ref, main_brand)]
                for sim in similarity_list:
                    if isinstance(sim, dict) and 'search_ref' in sim and 'brand' in sim:
                        sim_ref = str(sim['search_ref']).strip().upper()
                        sim_brand = str(sim['brand']).strip().upper()
                        all_refs.append((sim_ref, sim_brand))
                
                # Buscar info das peças
                parts_info = self.similarity_repo.fetch_parts_with_similarity(all_refs)
                
                if not parts_info:
                    continue
                
                part_ids = [info[0] for info in parts_info.values()]
                similarity_ids = [info[1] for info in parts_info.values() if info[1] is not None]
                unique_ids = list(set(similarity_ids))
                
                if len(unique_ids) == 0:
                    # Criar novo grupo
                    new_id = self.similarity_repo.create_similarity_group()
                    self.similarity_repo.update_parts_similarity(part_ids, new_id)
                    stats['groups_created'] += 1
                    stats['parts_updated'] += len(part_ids)
                
                elif len(unique_ids) == 1:
                    # Usar grupo existente
                    target_id = unique_ids[0]
                    parts_without = [pid for ref, (pid, sid) in zip(all_refs, parts_info.values()) if sid is None]
                    if parts_without:
                        self.similarity_repo.update_parts_similarity(parts_without, target_id)
                        stats['parts_updated'] += len(parts_without)
                
                else:
                    # Mesclar grupos
                    min_id = min(unique_ids)
                    for other_id in unique_ids:
                        if other_id != min_id:
                            migrated = self.similarity_repo.migrate_similarity_groups(other_id, min_id)
                            stats['parts_updated'] += migrated
                            stats['groups_merged'] += 1
                
            except Exception as e:
                logger.warning(f"Erro ao processar similaridade: {e}")
                continue
        
        return stats


# ============================================================================
# FUNÇÕES PRINCIPAIS DE SERVIÇO
# ============================================================================

def get_publish_preview(project_id: str) -> PublishPreviewResponse:
    """
    Gera preview da publicação sem executar
    
    Args:
        project_id: ID do projeto no DuckDB
        
    Returns:
        PublishPreviewResponse com métricas e validações
    """
    import time
    start_total = time.time()
    
    warnings = []
    blockers = []
    duck_conn = None
    
    logger.info(f"📊 [PREVIEW] Iniciando preview para projeto: {project_id}")
    
    try:
        # ETAPA 1: Testar conexão com produção
        step_start = time.time()
        logger.info("📊 [PREVIEW] ETAPA 1: Testando conexão com banco de produção...")
        
        from backend.services.data_validation.production_db import test_production_connection
        db_status = test_production_connection()
        
        logger.info(f"📊 [PREVIEW] ETAPA 1 concluída em {time.time() - step_start:.2f}s - Status: {db_status['status']}")
        
        if db_status['status'] != 'connected':
            blockers.append(f"Não foi possível conectar ao banco de produção: {db_status.get('error', 'Erro desconhecido')}")
            logger.warning(f"📊 [PREVIEW] Conexão falhou: {db_status.get('error')}")
            
            return PublishPreviewResponse(
                project_id=project_id,
                total_rows=0,
                parts_new=0,
                parts_existing=0,
                brands_existing=0,
                brands_to_create=0,
                brands_to_create_list=[],
                production_db_status=db_status['status'],
                warnings=warnings,
                blockers=blockers,
                can_publish=False
            )
        
        if not db_status['ready']:
            blockers.append(f"Tabelas faltando no banco de produção: {', '.join(db_status['missing_tables'])}")
        
        # ETAPA 2: Carregar dados do DuckDB
        step_start = time.time()
        logger.info("📊 [PREVIEW] ETAPA 2: Conectando ao DuckDB...")
        
        duck = duck_manager.DuckSession(project_id)
        duck_conn = duck._get_conn(read_only=True)
        
        logger.info(f"📊 [PREVIEW] ETAPA 2 concluída em {time.time() - step_start:.2f}s")
        
        # ETAPA 3: Contar total de linhas
        step_start = time.time()
        logger.info("📊 [PREVIEW] ETAPA 3: Contando total de linhas...")
        
        total_rows = duck_conn.execute("SELECT COUNT(*) FROM raw_data").fetchone()[0]
        
        logger.info(f"📊 [PREVIEW] ETAPA 3 concluída em {time.time() - step_start:.2f}s - Total: {total_rows} linhas")
        
        # ETAPA 4: Buscar dados de brands
        step_start = time.time()
        logger.info("📊 [PREVIEW] ETAPA 4: Buscando brands no dataset...")
        
        brands_query = """
            SELECT UPPER(TRIM(brand)) as brand_name, COUNT(*) as cnt
            FROM raw_data
            WHERE brand IS NOT NULL AND TRIM(brand) != '' AND UPPER(TRIM(brand)) != 'NAN'
            GROUP BY UPPER(TRIM(brand))
        """
        brands_in_data = duck_conn.execute(brands_query).fetchall()
        brands_dict = {row[0]: row[1] for row in brands_in_data}
        
        logger.info(f"📊 [PREVIEW] ETAPA 4 concluída em {time.time() - step_start:.2f}s - {len(brands_dict)} brands encontradas")
        
        # ETAPA 5: Verificar brands existentes na produção
        step_start = time.time()
        logger.info("📊 [PREVIEW] ETAPA 5: Verificando brands no banco de produção...")
        
        with production_connection() as conn:
            existing_brands = get_all_brands(conn)
            logger.info(f"📊 [PREVIEW] ETAPA 5a: {len(existing_brands)} brands existentes no banco")
            
            brands_existing = 0
            brands_to_create_list = []
            
            for brand_name, count in brands_dict.items():
                if brand_name in existing_brands:
                    brands_existing += 1
                else:
                    brands_to_create_list.append(BrandToCreate(brand_name=brand_name, occurrences=count))
            
            logger.info(f"📊 [PREVIEW] ETAPA 5 concluída em {time.time() - step_start:.2f}s - {brands_existing} existentes, {len(brands_to_create_list)} novas")
            
            # ETAPA 6: Verificar peças existentes
            step_start = time.time()
            logger.info("📊 [PREVIEW] ETAPA 6: Buscando peças no dataset...")
            
            parts_query = """
                SELECT UPPER(TRIM(search_ref)) as ref, UPPER(TRIM(brand)) as brand
                FROM raw_data
                WHERE search_ref IS NOT NULL AND brand IS NOT NULL
                AND TRIM(search_ref) != '' AND TRIM(brand) != ''
            """
            parts_in_data = duck_conn.execute(parts_query).fetchall()
            
            logger.info(f"📊 [PREVIEW] ETAPA 6 concluída em {time.time() - step_start:.2f}s - {len(parts_in_data)} peças encontradas")
            
            # ETAPA 7: Contar peças existentes vs novas
            step_start = time.time()
            logger.info("📊 [PREVIEW] ETAPA 7: Verificando peças existentes no banco de produção...")
            
            cursor = conn.cursor()
            existing_count = 0
            batch_size = 1000
            
            parts_to_check = []
            for ref, brand in parts_in_data:
                if brand in existing_brands:
                    brand_id = existing_brands[brand][0]
                    parts_to_check.append((ref, brand_id))
            
            logger.info(f"📊 [PREVIEW] ETAPA 7a: {len(parts_to_check)} peças para verificar no banco")
            
            if parts_to_check:
                total_batches = (len(parts_to_check) + batch_size - 1) // batch_size
                logger.info(f"📊 [PREVIEW] ETAPA 7b: Processando em {total_batches} batches de {batch_size}...")
                
                for i in range(0, len(parts_to_check), batch_size):
                    batch = parts_to_check[i:i + batch_size]
                    batch_num = (i // batch_size) + 1
                    
                    if batch_num % 10 == 0 or batch_num == 1:
                        logger.info(f"📊 [PREVIEW] ETAPA 7b: Processando batch {batch_num}/{total_batches}...")
                    
                    cursor.execute("""
                        SELECT COUNT(*) FROM catalog_part
                        WHERE (manufacturer_ref, brand_id) IN %s
                    """, (tuple(batch),))
                    existing_count += cursor.fetchone()[0]
            
            cursor.close()
            
            logger.info(f"📊 [PREVIEW] ETAPA 7 concluída em {time.time() - step_start:.2f}s - {existing_count} peças existentes")
        
        parts_new = total_rows - existing_count
        parts_existing = existing_count
        
        # ETAPA 8: Verificar coluna similarity
        step_start = time.time()
        logger.info("📊 [PREVIEW] ETAPA 8: Verificando dados de similaridade...")
        
        columns = [col[0] for col in duck_conn.execute("DESCRIBE raw_data").fetchall()]
        similarity_preview = None
        
        if 'similarity' in columns:
            sim_count = duck_conn.execute("""
                SELECT COUNT(*) FROM raw_data 
                WHERE similarity IS NOT NULL AND TRIM(CAST(similarity AS VARCHAR)) != ''
            """).fetchone()[0]
            
            if sim_count > 0:
                similarity_preview = SimilarityPreview(
                    total_rows_with_similarity=sim_count,
                    unique_similarity_groups=0
                )
                logger.info(f"📊 [PREVIEW] ETAPA 8: {sim_count} linhas com similaridade")
        
        logger.info(f"📊 [PREVIEW] ETAPA 8 concluída em {time.time() - step_start:.2f}s")
        
        # Validações finais
        if total_rows == 0:
            blockers.append("O projeto não contém dados para publicar")
        
        if brands_to_create_list:
            warnings.append(f"{len(brands_to_create_list)} brand(s) serão criadas automaticamente")
        
        can_publish = len(blockers) == 0
        
        total_time = time.time() - start_total
        logger.info(f"📊 [PREVIEW] ✅ Preview concluído em {total_time:.2f}s - Pode publicar: {can_publish}")
        
        return PublishPreviewResponse(
            project_id=project_id,
            total_rows=total_rows,
            parts_new=parts_new,
            parts_existing=parts_existing,
            brands_existing=brands_existing,
            brands_to_create=len(brands_to_create_list),
            brands_to_create_list=brands_to_create_list,
            similarity=similarity_preview,
            production_db_status=db_status['status'],
            warnings=warnings,
            blockers=blockers,
            can_publish=can_publish
        )
    
    except Exception as e:
        total_time = time.time() - start_total
        logger.error(f"📊 [PREVIEW] ❌ Erro após {total_time:.2f}s: {e}")
        import traceback
        logger.error(f"📊 [PREVIEW] Traceback: {traceback.format_exc()}")
        
        blockers.append(f"Erro ao analisar dados: {str(e)}")
        
        return PublishPreviewResponse(
            project_id=project_id,
            total_rows=0,
            parts_new=0,
            parts_existing=0,
            brands_existing=0,
            brands_to_create=0,
            brands_to_create_list=[],
            production_db_status='error',
            warnings=warnings,
            blockers=blockers,
            can_publish=False
        )
    
    finally:
        if duck_conn:
            duck_conn.close()
            logger.info("📊 [PREVIEW] Conexão DuckDB fechada")


def execute_publish(
    project_id: str,
    config: PublishConfiguration,
    author_id: int,
    current_owner_id: Optional[int] = None
) -> PublishResult:
    """
    Executa publicação dos dados validados para o banco de produção
    
    Args:
        project_id: ID do projeto no DuckDB
        config: Configuração de campos para atualização
        author_id: ID do usuário que está publicando
        current_owner_id: ID do fornecedor das informações (opcional)
    
    Returns:
        PublishResult com resultado da operação
    """
    start_time = time.time()
    
    try:
        # Estabelecer conexão com produção
        conn = get_production_connection()
        
        # Converter configuração
        update_config = UpdateFieldConfig.from_publish_config(config)
        
        # Usar author_id como current_owner_id se não fornecido
        owner_id = current_owner_id or author_id
        
        # Executar pipeline
        pipeline = PublishPipeline(conn, author_id, owner_id, update_config)
        report = pipeline.execute(project_id)
        
        # Fechar conexão
        conn.close()
        
        # Montar resultado
        return PublishResult(
            success=True,
            project_id=project_id,
            total_rows_processed=report.total_rows_processed,
            invalid_records_skipped=report.invalid_records_skipped,
            manufacturers_created=report.manufacturers_created,
            brands_created=report.brands_created,
            parts_inserted=report.parts_inserted,
            parts_updated=report.parts_updated,
            parts_skipped=report.parts_skipped,
            fields_updated=report.fields_updated,
            activities_created=report.activities_created,
            similarity_groups_created=report.similarity_groups_created,
            similarity_groups_merged=report.similarity_groups_merged,
            similarity_parts_updated=report.similarity_parts_updated,
            execution_time_seconds=report.execution_time,
            message=f"Publicação concluída com sucesso! {report.parts_inserted} peças inseridas, {report.parts_updated} atualizadas.",
            warnings=report.warnings,
            errors=[]
        )
        
    except Exception as e:
        logger.error(f"Erro ao executar publicação: {e}")
        execution_time = time.time() - start_time
        
        return PublishResult(
            success=False,
            project_id=project_id,
            total_rows_processed=0,
            execution_time_seconds=execution_time,
            message=f"Falha na publicação: {str(e)}",
            warnings=[],
            errors=[str(e)]
        )


def cleanup_project_files(project_id: str) -> bool:
    """
    Remove arquivos do projeto após publicação bem-sucedida
    
    Args:
        project_id: ID do projeto
    
    Returns:
        True se removido com sucesso
    """
    try:
        duckdb_path = os.path.join(duck_manager.TEMP_DIR, f"{project_id}.duckdb")
        
        if os.path.exists(duckdb_path):
            os.remove(duckdb_path)
            logger.info(f"Arquivo DuckDB removido: {duckdb_path}")
            return True
        
        return False
    except Exception as e:
        logger.error(f"Erro ao remover arquivo DuckDB: {e}")
        return False
