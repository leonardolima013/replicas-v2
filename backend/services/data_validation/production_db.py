"""
Módulo de conexão com banco de dados de produção PostgreSQL.
Autor: Sistema de Validação de Dados
Versão: 1.0
Descrição: Gerencia conexões com o banco de produção PostgreSQL para publicação de dados validados.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from typing import Optional
from contextlib import contextmanager
import logging

# Carregar variáveis de ambiente do .env (se existir - não existe no Docker)
env_path = Path(__file__).parent.parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÃO DO BANCO DE DADOS DE PRODUÇÃO (via env vars)
# ============================================================================

def get_production_config() -> dict:
    """
    Obtém configuração do banco de produção via variáveis de ambiente.
    
    Returns:
        Dict com configurações de conexão
    """
    return {
        'host': os.getenv('PROD_DB_HOST', 'localhost'),
        'port': os.getenv('PROD_DB_PORT', '5432'),
        'database': os.getenv('PROD_DB_NAME', 'hubbi_prod'),
        'user': os.getenv('PROD_DB_USER', 'postgres'),
        'password': os.getenv('PROD_DB_PASSWORD', 'postgres')
    }


def get_production_connection() -> psycopg2.extensions.connection:
    """
    Estabelece conexão com banco de dados de produção.
    
    Returns:
        Conexão psycopg2
        
    Raises:
        Exception: Se não conseguir conectar ao banco
    """
    config = get_production_config()
    
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        logger.info(f"Conexão estabelecida com banco de produção: {config['database']}@{config['host']}")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Erro ao conectar ao banco de produção: {e}")
        raise Exception(f"Não foi possível conectar ao banco de produção: {str(e)}")


@contextmanager
def production_connection():
    """
    Context manager para conexão com banco de produção.
    Garante fechamento adequado da conexão.
    
    Usage:
        with production_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    conn = None
    try:
        conn = get_production_connection()
        yield conn
    finally:
        if conn:
            conn.close()
            logger.debug("Conexão com banco de produção fechada")


def test_production_connection() -> dict:
    """
    Testa conexão com banco de produção e retorna status.
    
    Returns:
        Dict com status da conexão e informações do banco
    """
    config = get_production_config()
    
    try:
        with production_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar versão do PostgreSQL
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            # Verificar se tabelas necessárias existem
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('catalog_part', 'manufacturer_brand', 'manufacturer_manufacturer', 'catalog_similarity')
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = {'catalog_part', 'manufacturer_brand', 'manufacturer_manufacturer'}
            missing_tables = required_tables - set(existing_tables)
            
            cursor.close()
            
            return {
                'status': 'connected',
                'host': config['host'],
                'database': config['database'],
                'postgres_version': version,
                'existing_tables': existing_tables,
                'missing_tables': list(missing_tables),
                'ready': len(missing_tables) == 0
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'host': config['host'],
            'database': config['database'],
            'error': str(e),
            'ready': False
        }


# ============================================================================
# FUNÇÕES AUXILIARES PARA CONSULTAS RÁPIDAS
# ============================================================================

def check_brand_exists(conn: psycopg2.extensions.connection, brand_name: str) -> Optional[int]:
    """
    Verifica se uma brand existe no banco de produção.
    
    Args:
        conn: Conexão com banco de produção
        brand_name: Nome da brand (normalizado uppercase)
        
    Returns:
        brand_id se existir, None caso contrário
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id FROM manufacturer_brand 
            WHERE UPPER(TRIM(name)) = UPPER(TRIM(%s))
            LIMIT 1
        """, (brand_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()


def check_part_exists(conn: psycopg2.extensions.connection, search_ref: str, brand_id: int) -> Optional[int]:
    """
    Verifica se uma peça existe no banco de produção.
    
    Args:
        conn: Conexão com banco de produção
        search_ref: Referência de busca da peça
        brand_id: ID da brand
        
    Returns:
        part_id se existir, None caso contrário
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id FROM catalog_part 
            WHERE search_ref = %s AND brand_id = %s
            LIMIT 1
        """, (search_ref, brand_id))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()


def count_existing_parts(conn: psycopg2.extensions.connection, parts_to_check: list) -> int:
    """
    Conta quantas peças de uma lista já existem no banco.
    
    Args:
        conn: Conexão com banco de produção
        parts_to_check: Lista de tuplas (search_ref, brand_name)
        
    Returns:
        Quantidade de peças existentes
    """
    if not parts_to_check:
        return 0
    
    cursor = conn.cursor()
    try:
        # Dividir em batches para evitar consultas muito grandes
        batch_size = 1000
        existing_count = 0
        
        for i in range(0, len(parts_to_check), batch_size):
            batch = parts_to_check[i:i + batch_size]
            
            # Construir query com JOIN para resolver brand_name -> brand_id
            query = """
                SELECT COUNT(*) FROM catalog_part cp
                JOIN manufacturer_brand mb ON cp.brand_id = mb.id
                WHERE (cp.search_ref, UPPER(TRIM(mb.name))) IN %s
            """
            cursor.execute(query, (tuple(batch),))
            existing_count += cursor.fetchone()[0]
        
        return existing_count
    finally:
        cursor.close()


def get_all_brands(conn: psycopg2.extensions.connection) -> dict:
    """
    Busca todas as brands do banco de produção.
    
    Args:
        conn: Conexão com banco de produção
        
    Returns:
        Dict[brand_name_normalized] -> (brand_id, manufacturer_id)
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT UPPER(TRIM(name)) as name_key, id, manufacturer_id 
            FROM manufacturer_brand
        """)
        results = cursor.fetchall()
        return {row[0]: (row[1], row[2]) for row in results}
    finally:
        cursor.close()


# ============================================================================
# FUNÇÕES PARA ASSET_ASSET E CATALOG_PART_IMAGES
# ============================================================================

def extract_filename_from_url(url: str) -> str:
    """
    Extrai o nome do arquivo de uma URL S3.
    
    Args:
        url: URL completa, ex: "https://bucket.s3.region.amazonaws.com/folder/98601A-0_low.png"
        
    Returns:
        Nome do arquivo, ex: "98601A-0_low.png"
    """
    if not url:
        return ""
    # Pegar a última parte após a última /
    return url.rstrip('/').split('/')[-1]


def bulk_insert_assets(
    conn: psycopg2.extensions.connection,
    assets_data: list
) -> tuple:
    """
    Insere registros em bulk na tabela asset_asset.
    
    Args:
        conn: Conexão com banco de produção
        assets_data: Lista de dicts com:
            - file_high: Nome do arquivo high (extraído da URL)
            - file_medium: Nome do arquivo medium
            - file_low: Nome do arquivo low
            - file_water_mark: Nome do arquivo watermark
            
    Returns:
        Tupla (quantidade inserida, lista de IDs inseridos)
    """
    if not assets_data:
        return 0, []
    
    cursor = conn.cursor()
    try:
        from datetime import datetime
        timestamp_now = datetime.now()
        
        # Preparar dados para inserção
        values_list = []
        for asset in assets_data:
            values_list.append((
                1,  # type sempre = 1
                timestamp_now,  # uploaded_at
                asset.get('file_high', ''),
                asset.get('file_medium', ''),
                asset.get('file_low', ''),
                asset.get('file_water_mark', '')
            ))
        
        query = """
            INSERT INTO asset_asset 
            (type, uploaded_at, file_high, file_medium, file_low, file_water_mark)
            VALUES %s
            RETURNING id
        """
        
        psycopg2.extras.execute_values(
            cursor,
            query,
            values_list,
            template="(%s, %s, %s, %s, %s, %s)",
            page_size=1000,
            fetch=True
        )
        
        inserted_ids = [row[0] for row in cursor.fetchall()]
        logger.info(f"Inseridos {len(inserted_ids)} registros em asset_asset")
        return len(inserted_ids), inserted_ids
        
    except Exception as e:
        logger.error(f"Erro ao inserir assets: {e}")
        raise
    finally:
        cursor.close()


def bulk_insert_part_images(
    conn: psycopg2.extensions.connection,
    part_images_data: list
) -> int:
    """
    Insere registros em bulk na tabela catalog_part_images.
    
    Args:
        conn: Conexão com banco de produção
        part_images_data: Lista de tuplas (part_id, asset_id)
            
    Returns:
        Quantidade de registros inseridos
    """
    if not part_images_data:
        return 0
    
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO catalog_part_images (part_id, asset_id)
            VALUES %s
        """
        
        psycopg2.extras.execute_values(
            cursor,
            query,
            part_images_data,
            template="(%s, %s)",
            page_size=1000
        )
        
        inserted_count = len(part_images_data)
        logger.info(f"Inseridos {inserted_count} registros em catalog_part_images")
        return inserted_count
        
    except Exception as e:
        logger.error(f"Erro ao inserir part_images: {e}")
        raise
    finally:
        cursor.close()
