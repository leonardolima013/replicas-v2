"""
Cliente S3 para upload e gerenciamento de imagens no AWS S3.
Utilizado pelo módulo lambda_function para armazenamento de imagens processadas.
"""
import os
import logging
from io import BytesIO
from typing import Optional, Dict, List
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Ambientes disponíveis
ENVIRONMENTS = {
    'test': 'test-lambda',
    'production': 'media'
}


def _get_aws_credentials():
    """
    Obtém as credenciais AWS do ambiente em runtime.
    Isso garante que as variáveis de ambiente do Docker sejam lidas corretamente.
    """
    return {
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'bucket_name': os.getenv('AWS_BUCKET_NAME', 'hubbi-uploads-migrated'),
        'region': os.getenv('AWS_REGION', 'us-east-1')
    }


def get_s3_client():
    """
    Cria e retorna um cliente S3 configurado com as credenciais do ambiente.
    Usa boto3.Session() para melhor compatibilidade.
    
    Returns:
        boto3.client: Cliente S3 configurado
        
    Raises:
        ValueError: Se as credenciais AWS não estiverem configuradas
    """
    creds = _get_aws_credentials()
    
    if not creds['aws_access_key_id'] or not creds['aws_secret_access_key']:
        # Log para debug
        logger.error(f"AWS_ACCESS_KEY_ID presente: {bool(creds['aws_access_key_id'])}")
        logger.error(f"AWS_SECRET_ACCESS_KEY presente: {bool(creds['aws_secret_access_key'])}")
        raise ValueError(
            "Credenciais AWS não configuradas. "
            "Configure AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY no .env"
        )
    
    # Usar Session como no exemplo que funcionou
    session = boto3.Session(
        aws_access_key_id=creds['aws_access_key_id'],
        aws_secret_access_key=creds['aws_secret_access_key'],
        region_name=creds['region']
    )
    
    return session.client('s3')


def get_bucket_name() -> str:
    """Retorna o nome do bucket S3 configurado."""
    return _get_aws_credentials()['bucket_name']


# Cache global para imagem de watermark
_watermark_cache: Optional[bytes] = None


def get_watermark_image() -> bytes:
    """
    Recupera a imagem de watermark armazenada no S3 e a mantém em cache global,
    evitando múltiplos downloads.
    
    Returns:
        bytes: Bytes da imagem de watermark
        
    Raises:
        ClientError: Se houver erro ao acessar o S3
    """
    global _watermark_cache
    
    if _watermark_cache is None:
        logger.info("Carregando imagem de watermark do S3...")
        s3 = get_s3_client()
        bucket_name = get_bucket_name()
        
        try:
            response = s3.get_object(
                Bucket=bucket_name,
                Key='media/mascara-hubbi.png'
            )
            _watermark_cache = response['Body'].read()
            logger.info("Watermark carregada com sucesso e armazenada em cache")
        except ClientError as e:
            logger.error(f"Erro ao carregar watermark do S3: {e}")
            raise
    
    return _watermark_cache


def clear_watermark_cache():
    """Limpa o cache da watermark (útil para testes ou reload)"""
    global _watermark_cache
    _watermark_cache = None
    logger.info("Cache de watermark limpo")


def upload_file(
    file_bytes: bytes,
    file_name: str,
    folder_name: str,
    content_type: str = 'image/png'
) -> str:
    """
    Faz upload de um arquivo para o S3.
    
    Args:
        file_bytes: Conteúdo do arquivo em bytes
        file_name: Nome do arquivo (ex: 'ABC123_high.png')
        folder_name: Pasta no bucket (ex: 'test-lambda' ou 'media')
        content_type: MIME type do arquivo
        
    Returns:
        str: URL pública do arquivo no S3
        
    Raises:
        ClientError: Se houver erro no upload
    """
    s3 = get_s3_client()
    bucket_name = get_bucket_name()
    key = f"{folder_name}/{file_name}"
    
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=file_bytes,
            ContentType=content_type
        )
        
        url = generate_public_url(file_name, folder_name)
        logger.debug(f"Upload concluído: {url}")
        return url
        
    except ClientError as e:
        logger.error(f"Erro no upload do arquivo {key}: {e}")
        raise


def upload_image_variants(
    sku: str,
    variants: Dict[str, bytes],
    folder_name: str
) -> Dict[str, str]:
    """
    Faz upload de múltiplas variantes de uma imagem para o S3.
    
    Args:
        sku: Identificador do produto (usado no nome do arquivo)
        variants: Dicionário com variantes {'high': bytes, 'medium': bytes, ...}
        folder_name: Pasta no bucket ('test-lambda' ou 'media')
        
    Returns:
        Dict[str, str]: Dicionário com URLs de cada variante
    """
    urls = {}
    suffix_map = {
        'high': '',           # ABC123.png
        'medium': '_medium',  # ABC123_medium.png
        'low': '_low',        # ABC123_low.png
        'watermark': '_water_mark'  # ABC123_water_mark.png
    }
    
    for variant_name, file_bytes in variants.items():
        suffix = suffix_map.get(variant_name, f'_{variant_name}')
        file_name = f"{sku}{suffix}.png"
        
        url = upload_file(file_bytes, file_name, folder_name)
        urls[f'file_{variant_name}' if variant_name != 'high' else 'file_high'] = url
    
    return urls


def generate_public_url(file_name: str, folder_name: str) -> str:
    """
    Gera a URL pública de um arquivo no S3.
    
    Args:
        file_name: Nome do arquivo
        folder_name: Pasta no bucket
        
    Returns:
        str: URL pública do arquivo
    """
    creds = _get_aws_credentials()
    return f"https://{creds['bucket_name']}.s3.{creds['region']}.amazonaws.com/{folder_name}/{file_name}"


def generate_presigned_url(
    file_name: str,
    folder_name: str,
    expiration: int = 3600,
    http_method: str = 'PUT'
) -> str:
    """
    Gera uma URL pré-assinada para upload direto ao S3.
    
    Args:
        file_name: Nome do arquivo
        folder_name: Pasta no bucket
        expiration: Tempo de expiração em segundos (padrão: 1 hora)
        http_method: Método HTTP ('PUT' para upload, 'GET' para download)
        
    Returns:
        str: URL pré-assinada
    """
    s3 = get_s3_client()
    bucket_name = get_bucket_name()
    key = f"{folder_name}/{file_name}"
    
    try:
        url = s3.generate_presigned_url(
            ClientMethod='put_object' if http_method == 'PUT' else 'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': key,
                'ContentType': 'image/png'
            },
            ExpiresIn=expiration
        )
        return url
        
    except ClientError as e:
        logger.error(f"Erro ao gerar presigned URL para {key}: {e}")
        raise


def delete_file(file_name: str, folder_name: str) -> bool:
    """
    Remove um arquivo do S3.
    
    Args:
        file_name: Nome do arquivo
        folder_name: Pasta no bucket
        
    Returns:
        bool: True se deletado com sucesso
    """
    s3 = get_s3_client()
    bucket_name = get_bucket_name()
    key = f"{folder_name}/{file_name}"
    
    try:
        s3.delete_object(Bucket=bucket_name, Key=key)
        logger.debug(f"Arquivo deletado: {key}")
        return True
        
    except ClientError as e:
        logger.error(f"Erro ao deletar {key}: {e}")
        return False


def list_files(folder_name: str, prefix: str = '') -> List[Dict[str, str]]:
    """
    Lista arquivos em uma pasta do S3.
    
    Args:
        folder_name: Pasta no bucket
        prefix: Prefixo adicional para filtrar arquivos
        
    Returns:
        List[Dict]: Lista de arquivos com 'key', 'size', 'last_modified'
    """
    s3 = get_s3_client()
    bucket_name = get_bucket_name()
    creds = _get_aws_credentials()
    full_prefix = f"{folder_name}/{prefix}" if prefix else f"{folder_name}/"
    
    try:
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix=full_prefix
        )
        
        files = []
        for obj in response.get('Contents', []):
            files.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat(),
                'url': f"https://{creds['bucket_name']}.s3.{creds['region']}.amazonaws.com/{obj['Key']}"
            })
        
        return files
        
    except ClientError as e:
        logger.error(f"Erro ao listar arquivos em {full_prefix}: {e}")
        return []


def check_file_exists(file_name: str, folder_name: str) -> bool:
    """
    Verifica se um arquivo existe no S3.
    
    Args:
        file_name: Nome do arquivo
        folder_name: Pasta no bucket
        
    Returns:
        bool: True se o arquivo existe
    """
    s3 = get_s3_client()
    bucket_name = get_bucket_name()
    key = f"{folder_name}/{file_name}"
    
    try:
        s3.head_object(Bucket=bucket_name, Key=key)
        return True
    except ClientError:
        return False


def get_folder_for_environment(environment: str) -> str:
    """
    Retorna o nome da pasta S3 para um ambiente.
    
    Args:
        environment: 'test' ou 'production'
        
    Returns:
        str: Nome da pasta ('test-lambda' ou 'media')
        
    Raises:
        ValueError: Se o ambiente não for válido
    """
    if environment not in ENVIRONMENTS:
        raise ValueError(
            f"Ambiente inválido: {environment}. "
            f"Use: {list(ENVIRONMENTS.keys())}"
        )
    return ENVIRONMENTS[environment]
