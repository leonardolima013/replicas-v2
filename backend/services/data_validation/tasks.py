"""
Tasks Celery para processamento assíncrono de relatórios de validação.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import time
import traceback
import logging
import base64
from datetime import datetime
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# Carregar variáveis de ambiente do .env (se existir - não existe no Docker)
env_path = Path(__file__).parent.parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from celery import shared_task
from sqlalchemy.orm import Session

from backend.celery_app import celery_app
from backend.core.database import SessionLocal
from backend.services.data_validation import models, duck_manager
from backend.services.data_validation.production_db import (
    test_production_connection,
    production_connection,
    get_all_brands
)
from backend.services.data_validation.s3_client import (
    get_watermark_image,
    upload_file,
    generate_public_url,
    get_folder_for_environment
)
from backend.services.data_validation.image_processor import (
    process_single_image,
    extract_sku_from_filename,
    validate_image_file
)

logger = logging.getLogger(__name__)


def get_db_session() -> Session:
    """Cria uma nova sessão do banco de dados"""
    return SessionLocal()


def update_report_progress(
    db: Session,
    report: models.ProjectReport,
    progress: float,
    step: str,
    status: str = "running"
):
    """Atualiza o progresso do relatório no banco de dados"""
    report.processing_progress = progress
    report.processing_step = step
    report.processing_status = status
    report.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"📊 [{report.project_id}] {progress:.1f}% - {step}")


@celery_app.task(bind=True, name="backend.services.data_validation.tasks.process_project_report")
def process_project_report(self, project_id: str) -> dict:
    """
    Task Celery para processar o relatório de um projeto de validação.
    
    Esta task:
    1. Analisa o arquivo DuckDB do projeto
    2. Conta peças novas vs existentes no banco de produção
    3. Identifica marcas novas vs existentes
    4. Gera métricas de qualidade
    5. Salva tudo na tabela ProjectReport
    
    Args:
        project_id: ID do projeto a processar
        
    Returns:
        dict com status e métricas do processamento
    """
    db = get_db_session()
    start_time = time.time()
    duck_conn = None
    
    try:
        logger.info(f"🚀 [{project_id}] Iniciando processamento do relatório")
        
        # Buscar projeto e relatório
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project:
            raise ValueError(f"Projeto não encontrado: {project_id}")
        
        # Buscar ou criar relatório
        report = db.query(models.ProjectReport).filter(
            models.ProjectReport.project_id == project_id
        ).first()
        
        if not report:
            report = models.ProjectReport(project_id=project_id)
            db.add(report)
            db.commit()
            db.refresh(report)
        
        # Atualizar task ID do Celery
        report.celery_task_id = self.request.id
        report.processing_started_at = datetime.utcnow()
        report.processing_status = "running"
        report.error_message = None
        report.error_traceback = None
        db.commit()
        
        # Atualizar status do projeto
        project.status = models.ProjectStatus.PROCESSING_REPORT
        db.commit()
        
        # ============================================================
        # ETAPA 1: Testar conexão com banco de produção (5%)
        # ============================================================
        update_report_progress(db, report, 5.0, "Testando conexão com banco de produção")
        
        db_status = test_production_connection()
        report.production_db_status = db_status['status']
        report.production_db_ready = db_status.get('ready', False)
        db.commit()
        
        if db_status['status'] != 'connected':
            raise ConnectionError(
                f"Não foi possível conectar ao banco de produção: {db_status.get('error', 'Erro desconhecido')}"
            )
        
        # ============================================================
        # ETAPA 2: Conectar ao DuckDB (10%)
        # ============================================================
        update_report_progress(db, report, 10.0, "Conectando ao arquivo de dados")
        
        duck = duck_manager.DuckSession(project_id)
        duck_conn = duck._get_conn(read_only=True)
        
        # ============================================================
        # ETAPA 3: Contar total de linhas (15%)
        # ============================================================
        update_report_progress(db, report, 15.0, "Contando registros no arquivo")
        
        total_rows = duck_conn.execute("SELECT COUNT(*) FROM raw_data").fetchone()[0]
        report.total_rows = total_rows
        db.commit()
        
        logger.info(f"📊 [{project_id}] Total de linhas: {total_rows}")
        
        # ============================================================
        # ETAPA 4: Identificar colunas (20%)
        # ============================================================
        update_report_progress(db, report, 20.0, "Identificando colunas do arquivo")
        
        columns = [col[0] for col in duck_conn.execute("DESCRIBE raw_data").fetchall()]
        report.columns_found = columns
        db.commit()
        
        logger.info(f"📊 [{project_id}] Colunas encontradas: {len(columns)}")
        
        # ============================================================
        # ETAPA 5: Buscar marcas no dataset (30%)
        # ============================================================
        update_report_progress(db, report, 30.0, "Analisando marcas no arquivo")
        
        brands_query = """
            SELECT UPPER(TRIM(brand)) as brand_name, COUNT(*) as cnt
            FROM raw_data
            WHERE brand IS NOT NULL AND TRIM(brand) != '' AND UPPER(TRIM(brand)) != 'NAN'
            GROUP BY UPPER(TRIM(brand))
        """
        brands_in_data = duck_conn.execute(brands_query).fetchall()
        brands_dict = {row[0]: row[1] for row in brands_in_data}
        
        logger.info(f"📊 [{project_id}] Marcas no arquivo: {len(brands_dict)}")
        
        # ============================================================
        # ETAPA 6: Verificar marcas no banco de produção (40%)
        # ============================================================
        update_report_progress(db, report, 40.0, "Verificando marcas no banco de produção")
        
        with production_connection() as prod_conn:
            existing_brands = get_all_brands(prod_conn)
            
            brands_existing = 0
            brands_to_create_list = []
            
            for brand_name, count in brands_dict.items():
                if brand_name in existing_brands:
                    brands_existing += 1
                else:
                    brands_to_create_list.append({
                        "brand_name": brand_name,
                        "occurrences": count
                    })
            
            report.brands_existing = brands_existing
            report.brands_new = len(brands_to_create_list)
            report.brands_to_create = brands_to_create_list
            db.commit()
            
            logger.info(f"📊 [{project_id}] Marcas existentes: {brands_existing}, Novas: {len(brands_to_create_list)}")
            
            # ============================================================
            # ETAPA 7: Buscar peças no dataset (50%)
            # ============================================================
            update_report_progress(db, report, 50.0, "Analisando peças no arquivo")
            
            parts_query = """
                SELECT UPPER(TRIM(search_ref)) as ref, UPPER(TRIM(brand)) as brand
                FROM raw_data
                WHERE search_ref IS NOT NULL AND brand IS NOT NULL
                AND TRIM(search_ref) != '' AND TRIM(brand) != ''
            """
            parts_in_data = duck_conn.execute(parts_query).fetchall()
            
            logger.info(f"📊 [{project_id}] Peças no arquivo: {len(parts_in_data)}")
            
            # ============================================================
            # ETAPA 8: Verificar peças no banco de produção (50% - 90%)
            # ============================================================
            update_report_progress(db, report, 55.0, "Verificando peças existentes no banco de produção")
            
            cursor = prod_conn.cursor()
            batch_size = 1000
            
            # Preparar lista de peças ÚNICAS para verificar
            parts_to_check_set = set()
            for ref, brand in parts_in_data:
                if brand in existing_brands:
                    brand_id = existing_brands[brand][0]
                    parts_to_check_set.add((ref, brand_id))
            
            parts_to_check = list(parts_to_check_set)
            total_unique_parts = len(parts_to_check)
            total_batches = (total_unique_parts + batch_size - 1) // batch_size if total_unique_parts > 0 else 0
            
            logger.info(f"📊 [{project_id}] Verificando {total_unique_parts} peças únicas em {total_batches} batches")
            
            # Coletar peças que existem no banco (sem contar duplicatas)
            existing_parts_set = set()
            
            if parts_to_check:
                for i in range(0, total_unique_parts, batch_size):
                    batch = parts_to_check[i:i + batch_size]
                    batch_num = (i // batch_size) + 1
                    
                    # Atualizar progresso (50% a 90% durante esta etapa)
                    progress = 55.0 + (batch_num / total_batches) * 35.0
                    
                    if batch_num % 10 == 0 or batch_num == 1 or batch_num == total_batches:
                        update_report_progress(
                            db, report, progress,
                            f"Verificando peças: batch {batch_num}/{total_batches}"
                        )
                    
                    try:
                        cursor.execute("""
                            SELECT search_ref, brand_id FROM catalog_part
                            WHERE (search_ref, brand_id) IN %s
                        """, (tuple(batch),))
                        for row in cursor.fetchall():
                            existing_parts_set.add((row[0], row[1]))
                    except Exception as e:
                        logger.warning(f"Erro ao verificar batch {batch_num}: {e}")
            
            cursor.close()
            
            existing_count = len(existing_parts_set)
            new_count = total_unique_parts - existing_count
            
            report.parts_existing = existing_count
            report.parts_new = new_count
            db.commit()
            
            logger.info(f"📊 [{project_id}] Peças únicas: {total_unique_parts}, Existentes: {existing_count}, Novas: {new_count}")
        
        # ============================================================
        # ETAPA 9: Finalizar relatório (95%)
        # ============================================================
        update_report_progress(db, report, 95.0, "Finalizando relatório")
        
        # Fechar conexão DuckDB
        if duck_conn:
            duck_conn.close()
            duck_conn = None
        
        # Calcular tempo de processamento
        processing_time = time.time() - start_time
        report.processing_time_seconds = processing_time
        report.processing_completed_at = datetime.utcnow()
        report.processing_status = "completed"
        report.processing_progress = 100.0
        report.processing_step = "Relatório concluído"
        db.commit()
        
        # Atualizar status do projeto para READY_TO_PUBLISH
        project.status = models.ProjectStatus.READY_TO_PUBLISH
        db.commit()
        
        logger.info(f"✅ [{project_id}] Relatório concluído em {processing_time:.2f}s")
        
        return {
            "status": "success",
            "project_id": project_id,
            "total_rows": report.total_rows,
            "parts_new": report.parts_new,
            "parts_existing": report.parts_existing,
            "brands_new": report.brands_new,
            "brands_existing": report.brands_existing,
            "processing_time": processing_time
        }
        
    except Exception as e:
        logger.error(f"❌ [{project_id}] Erro no processamento: {e}")
        logger.error(traceback.format_exc())
        
        try:
            # Atualizar relatório com erro
            report = db.query(models.ProjectReport).filter(
                models.ProjectReport.project_id == project_id
            ).first()
            
            if report:
                report.processing_status = "error"
                report.error_message = str(e)
                report.error_traceback = traceback.format_exc()
                report.processing_completed_at = datetime.utcnow()
                report.processing_time_seconds = time.time() - start_time
                db.commit()
            
            # Atualizar status do projeto
            project = db.query(models.Project).filter(models.Project.id == project_id).first()
            if project:
                project.status = models.ProjectStatus.PROCESSING_ERROR
                db.commit()
                
        except Exception as db_error:
            logger.error(f"❌ [{project_id}] Erro ao salvar estado de erro: {db_error}")
        
        return {
            "status": "error",
            "project_id": project_id,
            "error": str(e)
        }
        
    finally:
        if duck_conn:
            try:
                duck_conn.close()
            except:
                pass
        
        db.close()


@celery_app.task(bind=True, name="backend.services.data_validation.tasks.recalculate_project_report")
def recalculate_project_report(self, project_id: str) -> dict:
    """
    Task para recalcular um relatório existente.
    Útil quando o banco de produção mudou desde o último processamento.
    """
    logger.info(f"🔄 [{project_id}] Recalculando relatório")
    
    # Limpar relatório anterior
    db = get_db_session()
    try:
        report = db.query(models.ProjectReport).filter(
            models.ProjectReport.project_id == project_id
        ).first()
        
        if report:
            report.processing_status = "pending"
            report.processing_progress = 0.0
            report.processing_step = None
            report.error_message = None
            report.error_traceback = None
            db.commit()
        
        # Atualizar status do projeto
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if project:
            project.status = models.ProjectStatus.PROCESSING_REPORT
            db.commit()
            
    finally:
        db.close()
    
    # Chamar task principal
    return process_project_report(project_id)


# ==============================================================================
# TASKS PARA PROCESSAMENTO DE IMAGENS (lambda_function)
# ==============================================================================

def update_image_task_progress(
    db: Session,
    task_record: models.ImageProcessingTask,
    progress: float,
    step: str,
    status: str = "running"
):
    """Atualiza o progresso da task de imagens no banco de dados"""
    task_record.processing_progress = progress
    task_record.processing_step = step
    task_record.status = status
    task_record.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"📷 [{task_record.project_id}] {progress:.1f}% - {step}")


@celery_app.task(bind=True, name="backend.services.data_validation.tasks.process_images_batch")
def process_images_batch(
    self,
    project_id: str,
    images_data: List[Dict],
    environment: str = "test"
) -> dict:
    """
    Task Celery para processar um batch de imagens.
    
    Processa imagens em paralelo, faz upload para S3, e retorna mapa de URLs por SKU.
    
    Args:
        project_id: ID do projeto de validação
        images_data: Lista de dicts com {'filename': str, 'content': str (base64)}
        environment: 'test' ou 'production' (define pasta S3: test-lambda ou media)
        
    Returns:
        dict com status, URLs processadas, e erros
    """
    db = get_db_session()
    start_time = time.time()
    
    try:
        logger.info(f"📷 [{project_id}] Iniciando processamento de {len(images_data)} imagens")
        
        # Buscar projeto
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project:
            raise ValueError(f"Projeto não encontrado: {project_id}")
        
        # Criar ou atualizar registro da task
        task_record = db.query(models.ImageProcessingTask).filter(
            models.ImageProcessingTask.project_id == project_id
        ).first()
        
        if not task_record:
            task_record = models.ImageProcessingTask(
                project_id=project_id,
                celery_task_id=self.request.id,
                environment=environment,
                total_images=len(images_data),
                status="running"
            )
            db.add(task_record)
        else:
            task_record.celery_task_id = self.request.id
            task_record.environment = environment
            task_record.total_images = len(images_data)
            task_record.status = "running"
            task_record.error_message = None
            task_record.processed_images = 0
            task_record.failed_images = 0
        
        db.commit()
        db.refresh(task_record)
        
        # Obter pasta S3 baseada no ambiente
        folder_name = get_folder_for_environment(environment)
        
        # ============================================================
        # ETAPA 1: Carregar watermark (5%)
        # ============================================================
        update_image_task_progress(db, task_record, 5.0, "Carregando marca d'água")
        
        try:
            watermark_bytes = get_watermark_image()
        except Exception as e:
            logger.warning(f"Não foi possível carregar watermark: {e}")
            watermark_bytes = None
        
        # ============================================================
        # ETAPA 2: Validar e decodificar imagens (10%)
        # ============================================================
        update_image_task_progress(db, task_record, 10.0, "Validando imagens")
        
        valid_images = []
        errors = []
        
        for img_data in images_data:
            filename = img_data.get('filename', '')
            content_b64 = img_data.get('content', '')
            
            try:
                # Decodificar base64
                image_bytes = base64.b64decode(content_b64)
                
                # Validar imagem
                is_valid, error_msg = validate_image_file(image_bytes, filename)
                if not is_valid:
                    errors.append({'filename': filename, 'error': error_msg})
                    continue
                
                # Extrair SKU
                sku, index = extract_sku_from_filename(filename)
                
                valid_images.append({
                    'filename': filename,
                    'bytes': image_bytes,
                    'sku': sku,
                    'index': index
                })
                
            except Exception as e:
                errors.append({'filename': filename, 'error': str(e)})
        
        task_record.failed_images = len(errors)
        db.commit()
        
        logger.info(f"📷 [{project_id}] {len(valid_images)} imagens válidas, {len(errors)} com erro")
        
        # Log detalhado dos erros de validação
        for err in errors[:5]:  # Log apenas os primeiros 5 erros
            logger.warning(f"📷 [{project_id}] Erro em '{err['filename']}': {err['error']}")
        
        # ============================================================
        # ETAPA 3: Processar imagens em paralelo (15% - 70%)
        # ============================================================
        update_image_task_progress(db, task_record, 15.0, "Processando imagens")
        
        results_by_sku = {}  # {sku: {high: [url], medium: [url], ...}}
        processed_count = 0
        total_valid = len(valid_images)
        
        def process_and_upload_image(img_info):
            """Função para processar uma imagem e fazer upload"""
            filename = img_info['filename']
            image_bytes = img_info['bytes']
            sku = img_info['sku']
            index = img_info['index']
            
            # Processar variantes
            variants = process_single_image(image_bytes, watermark_bytes)
            
            # Upload de cada variante
            urls = {}
            suffix_map = {
                'high': '',
                'medium': '_medium',
                'low': '_low',
                'watermark': '_water_mark'
            }
            
            for variant_name, variant_bytes in variants.items():
                suffix = suffix_map.get(variant_name, f'_{variant_name}')
                # Incluir índice no nome do arquivo para múltiplas imagens
                file_name = f"{sku}-{index}{suffix}.png"
                
                url = upload_file(variant_bytes, file_name, folder_name)
                urls[variant_name] = url
            
            return {
                'sku': sku,
                'index': index,
                'urls': urls
            }
        
        # Processar em paralelo com ThreadPoolExecutor
        # Garantir pelo menos 1 worker (mesmo que total_valid seja 0)
        max_workers = max(1, min(10, total_valid))
        
        # Se não há imagens válidas, pular processamento
        if total_valid == 0:
            logger.warning(f"📷 [{project_id}] Nenhuma imagem válida para processar")
            update_image_task_progress(db, task_record, 70.0, "Nenhuma imagem válida")
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(process_and_upload_image, img): img 
                    for img in valid_images
                }
                
                for future in as_completed(futures):
                    img_info = futures[future]
                    try:
                        result = future.result()
                        sku = result['sku']
                        
                        # Agrupar por SKU
                        if sku not in results_by_sku:
                            results_by_sku[sku] = {
                                'high': [],
                                'medium': [],
                                'low': [],
                                'watermark': []
                            }
                        
                        for variant, url in result['urls'].items():
                            results_by_sku[sku][variant].append({
                                'index': result['index'],
                                'url': url
                            })
                        
                        processed_count += 1
                        
                    except Exception as e:
                        logger.error(f"Erro ao processar {img_info['filename']}: {e}")
                        errors.append({
                            'filename': img_info['filename'],
                            'error': str(e)
                        })
                        task_record.failed_images += 1
                    
                    # Atualizar progresso periodicamente
                    if processed_count % 10 == 0 or processed_count == total_valid:
                        progress = 15.0 + (processed_count / total_valid) * 55.0
                        update_image_task_progress(
                            db, task_record, progress,
                            f"Processando: {processed_count}/{total_valid}"
                        )
                        task_record.processed_images = processed_count
                        db.commit()
        
        # ============================================================
        # ETAPA 4: Ordenar URLs por índice (75%)
        # ============================================================
        update_image_task_progress(db, task_record, 75.0, "Organizando resultados")
        
        # Ordenar URLs por índice e extrair apenas URLs
        final_results = {}
        for sku, variants in results_by_sku.items():
            final_results[sku] = {}
            for variant_name, url_list in variants.items():
                # Ordenar por índice e extrair apenas URLs
                sorted_urls = [
                    item['url'] 
                    for item in sorted(url_list, key=lambda x: x['index'])
                ]
                final_results[sku][variant_name] = sorted_urls
        
        # ============================================================
        # ETAPA 5: Salvar resultado (90%)
        # ============================================================
        update_image_task_progress(db, task_record, 90.0, "Salvando resultados")
        
        task_record.result_data = final_results
        task_record.errors_data = errors
        task_record.processed_images = processed_count
        db.commit()
        
        # ============================================================
        # ETAPA 6: Finalizar (100%)
        # ============================================================
        processing_time = time.time() - start_time
        task_record.processing_time_seconds = processing_time
        task_record.status = "completed"
        task_record.processing_progress = 100.0
        task_record.processing_step = "Processamento concluído"
        task_record.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(
            f"✅ [{project_id}] Processamento de imagens concluído em {processing_time:.2f}s. "
            f"Processadas: {processed_count}, Erros: {len(errors)}, SKUs: {len(final_results)}"
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "total_images": len(images_data),
            "processed_images": processed_count,
            "failed_images": len(errors),
            "skus_count": len(final_results),
            "results": final_results,
            "errors": errors,
            "processing_time": processing_time
        }
        
    except Exception as e:
        logger.error(f"❌ [{project_id}] Erro no processamento de imagens: {e}")
        logger.error(traceback.format_exc())
        
        try:
            task_record = db.query(models.ImageProcessingTask).filter(
                models.ImageProcessingTask.project_id == project_id
            ).first()
            
            if task_record:
                task_record.status = "error"
                task_record.error_message = str(e)
                task_record.completed_at = datetime.utcnow()
                task_record.processing_time_seconds = time.time() - start_time
                db.commit()
                
        except Exception as db_error:
            logger.error(f"❌ [{project_id}] Erro ao salvar estado de erro: {db_error}")
        
        return {
            "status": "error",
            "project_id": project_id,
            "error": str(e)
        }
        
    finally:
        db.close()

