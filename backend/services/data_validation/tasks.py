"""
Tasks Celery para processamento assíncrono de relatórios de validação.
"""
import os
import time
import traceback
import logging
from datetime import datetime
from typing import Optional

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
            existing_count = 0
            batch_size = 1000
            
            # Preparar lista de peças para verificar
            parts_to_check = []
            for ref, brand in parts_in_data:
                if brand in existing_brands:
                    brand_id = existing_brands[brand][0]
                    parts_to_check.append((ref, brand_id))
            
            total_parts = len(parts_to_check)
            total_batches = (total_parts + batch_size - 1) // batch_size if total_parts > 0 else 0
            
            logger.info(f"📊 [{project_id}] Verificando {total_parts} peças em {total_batches} batches")
            
            if parts_to_check:
                for i in range(0, total_parts, batch_size):
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
                            SELECT COUNT(*) FROM catalog_part
                            WHERE (manufacturer_ref, brand_id) IN %s
                        """, (tuple(batch),))
                        existing_count += cursor.fetchone()[0]
                    except Exception as e:
                        logger.warning(f"Erro ao verificar batch {batch_num}: {e}")
            
            cursor.close()
            
            report.parts_existing = existing_count
            report.parts_new = total_rows - existing_count
            db.commit()
            
            logger.info(f"📊 [{project_id}] Peças existentes: {existing_count}, Novas: {total_rows - existing_count}")
        
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
