"""
Processador de imagens para o módulo lambda_function.
Realiza resize, crop e aplicação de watermark em imagens.
"""
import logging
from io import BytesIO
from typing import Dict, Tuple, Optional
from PIL import Image

from backend.services.data_validation.s3_client import get_watermark_image

logger = logging.getLogger(__name__)

# Configurações de dimensões para cada variante
IMAGE_DIMENSIONS = {
    'high': 2048,      # Alta resolução
    'medium': 300,     # Média resolução
    'low': 200,        # Baixa resolução (thumbnail)
    'watermark': 500   # Com marca d'água
}

# Qualidade de compressão para cada variante
IMAGE_QUALITY = {
    'high': 95,
    'medium': 85,
    'low': 75,
    'watermark': 85
}


def make_square(
    img: Image.Image,
    min_size: int = 266,
    fill_color: Tuple[int, int, int, int] = (255, 255, 255, 0)
) -> Image.Image:
    """
    Converte uma imagem retangular em uma imagem quadrada,
    centralizando o conteúdo e preenchendo as áreas sobrantes
    com uma cor de fundo.
    
    Args:
        img: Instância de PIL.Image a ser transformada em quadrado.
        min_size: Tamanho mínimo (em pixels) de cada lado do quadrado.
        fill_color: Cor RGBA usada para preencher o fundo.
        
    Returns:
        PIL.Image.Image: Nova imagem quadrada contendo a original centralizada.
    """
    x, y = img.size
    
    # Determina o lado do quadrado como o maior valor entre
    # min_size, largura e altura da imagem original
    size = max(min_size, x, y)
    
    # Cria uma nova imagem RGBA quadrada com a cor de preenchimento
    new_img = Image.new('RGBA', (size, size), fill_color)
    
    # Cola a imagem original centralizada na nova imagem
    offset = ((size - x) // 2, (size - y) // 2)
    
    # Converter para RGBA se necessário
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    new_img.paste(img, offset)
    
    return new_img


def resize_image(
    img: Image.Image,
    dimension: int,
    apply_watermark: bool = False,
    watermark_img: Optional[Image.Image] = None
) -> Image.Image:
    """
    Redimensiona uma imagem para um quadrado de tamanho especificado.
    
    Args:
        img: Imagem PIL a ser redimensionada.
        dimension: Tamanho do lado do quadrado em pixels.
        apply_watermark: Se True, aplica marca d'água.
        watermark_img: Imagem PIL da marca d'água (obrigatório se apply_watermark=True).
        
    Returns:
        PIL.Image.Image: Imagem redimensionada.
    """
    # Garantir formato quadrado
    img_square = make_square(img)
    
    # Redimensionar para a dimensão alvo
    img_resized = img_square.resize((dimension, dimension), Image.LANCZOS)
    
    # Aplicar watermark se solicitado
    if apply_watermark and watermark_img is not None:
        # Redimensionar watermark para caber na imagem se necessário
        wm_width, wm_height = watermark_img.size
        if wm_width > dimension or wm_height > dimension:
            # Escalar watermark proporcionalmente
            ratio = min(dimension / wm_width, dimension / wm_height)
            new_wm_size = (int(wm_width * ratio), int(wm_height * ratio))
            watermark_resized = watermark_img.resize(new_wm_size, Image.LANCZOS)
        else:
            watermark_resized = watermark_img
        
        # Colar watermark no canto superior esquerdo
        img_resized.paste(watermark_resized, (0, 0), watermark_resized)
    
    return img_resized


def image_to_bytes(img: Image.Image, format: str = 'PNG', quality: int = 95) -> bytes:
    """
    Converte uma imagem PIL para bytes.
    
    Args:
        img: Imagem PIL.
        format: Formato de saída ('PNG', 'JPEG', etc.).
        quality: Qualidade de compressão (1-100).
        
    Returns:
        bytes: Imagem serializada.
    """
    output = BytesIO()
    
    # PNG não suporta parâmetro quality
    if format.upper() == 'PNG':
        img.save(output, format=format, optimize=True)
    else:
        img.save(output, format=format, quality=quality, optimize=True)
    
    return output.getvalue()


def process_single_image(
    image_bytes: bytes,
    watermark_bytes: Optional[bytes] = None
) -> Dict[str, bytes]:
    """
    Processa uma única imagem gerando todas as 4 variantes.
    
    Args:
        image_bytes: Bytes da imagem original.
        watermark_bytes: Bytes da imagem de watermark (opcional, será carregada do S3 se None).
        
    Returns:
        Dict[str, bytes]: Dicionário com bytes de cada variante:
            - 'high': 2048x2048px
            - 'medium': 300x300px
            - 'low': 200x200px
            - 'watermark': 500x500px com marca d'água
    """
    # Abrir imagem original
    img = Image.open(BytesIO(image_bytes))
    
    # Carregar watermark
    watermark_img = None
    if watermark_bytes:
        watermark_img = Image.open(BytesIO(watermark_bytes))
    else:
        try:
            watermark_data = get_watermark_image()
            watermark_img = Image.open(BytesIO(watermark_data))
        except Exception as e:
            logger.warning(f"Não foi possível carregar watermark: {e}")
    
    variants = {}
    
    # Processar cada variante
    for variant_name, dimension in IMAGE_DIMENSIONS.items():
        apply_wm = (variant_name == 'watermark' and watermark_img is not None)
        
        processed = resize_image(
            img=img,
            dimension=dimension,
            apply_watermark=apply_wm,
            watermark_img=watermark_img
        )
        
        quality = IMAGE_QUALITY.get(variant_name, 85)
        variants[variant_name] = image_to_bytes(processed, 'PNG', quality)
    
    return variants


def extract_sku_from_filename(filename: str) -> Tuple[str, int]:
    """
    Extrai o SKU e índice de um nome de arquivo no formato '{sku}-{indice}.jpg'.
    
    Args:
        filename: Nome do arquivo (ex: 'ABC123-0.jpg', 'XYZ789-2.png')
        
    Returns:
        Tuple[str, int]: (sku, índice)
        
    Raises:
        ValueError: Se o formato do arquivo for inválido.
    """
    # Remover extensão
    name_without_ext = filename.rsplit('.', 1)[0]
    
    # Encontrar último hífen
    last_hyphen = name_without_ext.rfind('-')
    
    if last_hyphen == -1:
        raise ValueError(
            f"Formato inválido: '{filename}'. "
            "Esperado: '{sku}-{indice}.jpg'"
        )
    
    sku = name_without_ext[:last_hyphen]
    index_str = name_without_ext[last_hyphen + 1:]
    
    try:
        index = int(index_str)
    except ValueError:
        raise ValueError(
            f"Índice inválido em '{filename}': '{index_str}' não é um número."
        )
    
    return sku, index


def validate_image_file(
    file_bytes: bytes,
    filename: str,
    max_size_mb: int = 10
) -> Tuple[bool, Optional[str]]:
    """
    Valida um arquivo de imagem.
    
    Args:
        file_bytes: Bytes do arquivo.
        filename: Nome do arquivo.
        max_size_mb: Tamanho máximo permitido em MB.
        
    Returns:
        Tuple[bool, Optional[str]]: (é_válido, mensagem_de_erro)
    """
    # Verificar tamanho
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"Arquivo muito grande: {size_mb:.1f}MB (máximo: {max_size_mb}MB)"
    
    # Verificar extensão
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'}
    if ext not in allowed_extensions:
        return False, f"Extensão não permitida: .{ext}. Use: {allowed_extensions}"
    
    # Verificar magic bytes (cabeçalho do arquivo)
    magic_bytes = {
        b'\xff\xd8\xff': 'jpeg',           # JPEG
        b'\x89PNG\r\n\x1a\n': 'png',       # PNG (8 bytes)
        b'\x89PNG': 'png',                 # PNG (4 bytes - fallback)
        b'GIF87a': 'gif',                  # GIF87a
        b'GIF89a': 'gif',                  # GIF89a
        b'RIFF': 'webp',                   # WebP (começa com RIFF)
        b'BM': 'bmp',                      # BMP
    }
    
    valid_magic = False
    for magic, format_name in magic_bytes.items():
        if len(file_bytes) >= len(magic) and file_bytes[:len(magic)] == magic:
            valid_magic = True
            break
    
    if not valid_magic:
        # Log para debug
        preview = file_bytes[:20].hex() if len(file_bytes) >= 20 else file_bytes.hex()
        return False, f"Arquivo não é uma imagem válida. Primeiros bytes: {preview}"
    
    # Tentar abrir com PIL para validação final
    try:
        img = Image.open(BytesIO(file_bytes))
        img.verify()  # Verifica integridade
    except Exception as e:
        return False, f"Imagem corrompida ou inválida: {str(e)}"
    
    return True, None


def batch_process_images(
    images: Dict[str, bytes],
    watermark_bytes: Optional[bytes] = None,
    progress_callback=None
) -> Tuple[Dict[str, Dict[str, bytes]], list]:
    """
    Processa múltiplas imagens em batch, agrupando por SKU.
    
    Args:
        images: Dicionário {filename: bytes} das imagens.
        watermark_bytes: Bytes da watermark (opcional).
        progress_callback: Função callback(processed, total) para reportar progresso.
        
    Returns:
        Tuple[Dict, list]: 
            - Dict com {sku: {variant: [bytes, ...]}} agrupado por SKU
            - Lista de erros [{'filename': str, 'error': str}]
    """
    results = {}  # {sku: {high: [bytes], medium: [bytes], ...}}
    errors = []
    total = len(images)
    processed = 0
    
    # Carregar watermark uma única vez
    if watermark_bytes is None:
        try:
            watermark_bytes = get_watermark_image()
        except Exception as e:
            logger.warning(f"Não foi possível carregar watermark: {e}")
    
    for filename, image_bytes in images.items():
        try:
            # Validar imagem
            is_valid, error_msg = validate_image_file(image_bytes, filename)
            if not is_valid:
                errors.append({'filename': filename, 'error': error_msg})
                processed += 1
                if progress_callback:
                    progress_callback(processed, total)
                continue
            
            # Extrair SKU
            try:
                sku, index = extract_sku_from_filename(filename)
            except ValueError as e:
                errors.append({'filename': filename, 'error': str(e)})
                processed += 1
                if progress_callback:
                    progress_callback(processed, total)
                continue
            
            # Processar imagem
            variants = process_single_image(image_bytes, watermark_bytes)
            
            # Agrupar por SKU
            if sku not in results:
                results[sku] = {
                    'high': [],
                    'medium': [],
                    'low': [],
                    'watermark': []
                }
            
            for variant_name, variant_bytes in variants.items():
                results[sku][variant_name].append({
                    'index': index,
                    'bytes': variant_bytes
                })
            
        except Exception as e:
            logger.error(f"Erro ao processar {filename}: {e}")
            errors.append({'filename': filename, 'error': str(e)})
        
        processed += 1
        if progress_callback:
            progress_callback(processed, total)
    
    # Ordenar variantes por índice dentro de cada SKU
    for sku in results:
        for variant in results[sku]:
            results[sku][variant].sort(key=lambda x: x['index'])
    
    return results, errors
