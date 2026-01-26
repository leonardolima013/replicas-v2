import shutil
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func as db_func

from backend.core import database, deps, models as core_models
from backend.services.data_validation import models, schemas, duck_manager, constants

router = APIRouter(prefix="/validation", tags=["Data Validation"])

# Cria a pasta temporária se não existir
os.makedirs(duck_manager.TEMP_DIR, exist_ok=True)

# --- ROTA: LISTAR TODOS OS PROJETOS ---
@router.get("/projects", response_model=list[schemas.ProjectResponse])
def list_projects(
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Lista todos os projetos do usuário. Admins veem todos os projetos."""
    if current_user.role == "adm":
        projects = db.query(models.Project).order_by(models.Project.created_at.desc()).all()
    else:
        projects = db.query(models.Project).filter(
            models.Project.owner_id == current_user.id
        ).order_by(models.Project.created_at.desc()).all()
    
    # Adicionar username do proprietário a cada projeto
    result = []
    for project in projects:
        project_dict = schemas.ProjectResponse.model_validate(project).model_dump()
        project_dict["owner_username"] = project.owner.usuario if project.owner else None
        result.append(schemas.ProjectResponse(**project_dict))
    
    return result


# --- ROTA: HISTÓRICO DE VALIDAÇÕES (Apenas Admin) ---
@router.get("/history", response_model=schemas.ValidationHistoryResponse)
def get_validation_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Retorna o histórico de validações publicadas. Apenas para admins."""
    # Apenas admins podem ver o histórico
    if current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Apenas administradores podem ver o histórico")
    
    # Buscar projetos com status DONE
    query = db.query(models.Project).filter(
        models.Project.status == models.ProjectStatus.DONE
    ).order_by(models.Project.approved_at.desc())
    
    # Contar total
    total = query.count()
    
    # Aplicar paginação
    offset = (page - 1) * page_size
    projects = query.offset(offset).limit(page_size).all()
    
    # Construir resposta
    items = []
    for project in projects:
        # Buscar relatório
        report = db.query(models.ProjectReport).filter(
            models.ProjectReport.project_id == project.id
        ).first()
        
        item = schemas.ValidationHistoryItem(
            project_id=project.id,
            original_filename=project.original_filename,
            owner_id=project.owner_id,
            owner_username=project.owner.usuario if project.owner else "Desconhecido",
            created_at=project.created_at,
            published_by_id=report.published_by_id if report else None,
            published_by_username=report.published_by.usuario if report and report.published_by else None,
            published_at=report.published_at if report else project.approved_at,
            total_rows=report.total_rows if report else 0,
            parts_created=report.parts_created if report else None,
            parts_updated=report.parts_updated if report else None,
            brands_created=report.brands_created if report else None,
            processing_time_seconds=report.processing_time_seconds if report else None,
            publish_time_seconds=report.publish_time_seconds if report else None
        )
        items.append(item)
    
    total_pages = (total + page_size - 1) // page_size
    
    return schemas.ValidationHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


# --- ROTA DE UPLOAD (Essencial para criar o ficheiro primeiro) ---
@router.post("/upload", response_model=schemas.ProjectResponse)
def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    project_id = str(uuid.uuid4())
    temp_csv_path = os.path.join(duck_manager.TEMP_DIR, f"{project_id}_upload.csv")
    
    try:
        with open(temp_csv_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        duck = duck_manager.DuckSession(project_id)
        duck.load_csv_auto(temp_csv_path)
        
        db_project = models.Project(
            id=project_id,
            owner_id=current_user.id,
            original_filename=file.filename,
            file_path=os.path.join(duck_manager.TEMP_DIR, f"{project_id}.duckdb"),
            status=models.ProjectStatus.DRAFT
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project

    except Exception as e:
        if os.path.exists(temp_csv_path): os.remove(temp_csv_path)
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

# --- NOVA ROTA: PREVIEW (VISUALIZAÇÃO) ---
@router.get("/{project_id}/preview", response_model=schemas.PreviewResponse)
def get_data_preview(
    project_id: str, 
    page: int = Query(1, ge=1),      # Página mínima é 1
    limit: int = Query(50, le=1000), # Limite máximo por página é 1000
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    # 1. Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Adicionada verificação de permissão (admin pode ver todos os projetos)
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão de acesso a este projeto.")
    
    # 2. Buscar os dados no DuckDB
    try:
        duck = duck_manager.DuckSession(project_id)
        # Chama a função inteligente de paginação
        data = duck.get_preview(page=page, limit=limit)
        
        return {
            "total_rows": data["total_rows"],
            "page": page,
            "page_size": limit,
            "columns": data["columns"],
            "rows": data["rows"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- NOVA ROTA: EXECUTAR QUERY (LIMPEZA) ---
@router.post("/{project_id}/query", response_model=schemas.QueryResponse)
def run_sql_query(
    project_id: str,
    query: schemas.QueryRequest,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Adicionada verificação de permissão (admin pode executar queries em qualquer projeto)
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")

    # Bloqueio simples: Só deixa editar se estiver em Rascunho (DRAFT)
    if project.status != models.ProjectStatus.DRAFT:
         # Se não for SELECT, bloqueia
         sql_clean = query.sql.strip().lower()
         if not sql_clean.startswith("select") and not sql_clean.startswith("describe"):
            raise HTTPException(status_code=400, detail="Projeto bloqueado para edição. Apenas SELECTs são permitidos.")

    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.execute_user_query(query.sql)
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ROTA: DELETAR PROJETO ---
@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Deleta um projeto e seus arquivos associados."""
    # Verificar se o projeto existe
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Verificar permissão (owner ou admin)
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para deletar este projeto")
    
    try:
        # Deletar arquivo DuckDB
        duckdb_path = os.path.join(duck_manager.TEMP_DIR, f"{project_id}.duckdb")
        if os.path.exists(duckdb_path):
            os.remove(duckdb_path)
        
        # Deletar CSV exportado se existir
        export_csv = os.path.join(duck_manager.TEMP_DIR, f"{project_id}_export.csv")
        if os.path.exists(export_csv):
            os.remove(export_csv)
        
        # Deletar registro do banco
        db.delete(project)
        db.commit()
        
        return {"message": f"Projeto {project_id} deletado com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar projeto: {str(e)}")

# --- ROTA: ENVIAR PARA VALIDAÇÃO (DRAFT -> PROCESSING_REPORT) ---
@router.post("/{project_id}/submit", response_model=schemas.ProjectResponse)
def submit_project(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Envia o projeto para validação. 
    Muda status de DRAFT para PROCESSING_REPORT e inicia processamento em background.
    """
    from backend.services.data_validation.tasks import process_project_report
    
    # Buscar projeto
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Verificar se é o owner
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o proprietário pode enviar o projeto")
    
    # Verificar se está em DRAFT
    if project.status != models.ProjectStatus.DRAFT:
        raise HTTPException(
            status_code=400, 
            detail=f"Projeto não pode ser enviado. Status atual: {project.status.value}"
        )
    
    # Criar relatório inicial (se não existir)
    report = db.query(models.ProjectReport).filter(
        models.ProjectReport.project_id == project_id
    ).first()
    
    if not report:
        report = models.ProjectReport(
            project_id=project_id,
            processing_status="pending"
        )
        db.add(report)
    else:
        report.processing_status = "pending"
        report.processing_progress = 0.0
        report.error_message = None
        report.error_traceback = None
    
    # Mudar status para PENDING_REVIEW (será alterado para PROCESSING_REPORT pela task)
    project.status = models.ProjectStatus.PENDING_REVIEW
    db.commit()
    
    # Disparar task Celery para processar relatório
    try:
        task = process_project_report.delay(project_id)
        report.celery_task_id = task.id
        db.commit()
        print(f"🚀 Task Celery disparada: {task.id} para projeto {project_id}", flush=True)
    except Exception as e:
        print(f"⚠️ Erro ao disparar task Celery: {e}", flush=True)
        # Continua mesmo sem Celery (para desenvolvimento)
    
    db.refresh(project)
    
    # Retornar projeto atualizado
    project_dict = schemas.ProjectResponse.model_validate(project).model_dump()
    project_dict["owner_username"] = project.owner.usuario if project.owner else None
    return schemas.ProjectResponse(**project_dict)

# --- ROTA: CANCELAR ENVIO (PENDING_REVIEW/PROCESSING -> DRAFT) ---
@router.post("/{project_id}/cancel", response_model=schemas.ProjectResponse)
def cancel_project(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Cancela o envio do projeto. Muda status para DRAFT."""
    # Buscar projeto
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Verificar se é o owner ou admin
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para cancelar o envio")
    
    # Verificar se pode ser cancelado (não pode cancelar DONE)
    cancelable_statuses = [
        models.ProjectStatus.PENDING_REVIEW,
        models.ProjectStatus.PROCESSING_REPORT,
        models.ProjectStatus.READY_TO_PUBLISH,
        models.ProjectStatus.PROCESSING_ERROR
    ]
    
    if project.status not in cancelable_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Projeto não pode ser cancelado. Status atual: {project.status.value}"
        )
    
    # Mudar status de volta para DRAFT
    project.status = models.ProjectStatus.DRAFT
    db.commit()
    db.refresh(project)
    
    # Retornar projeto atualizado
    project_dict = schemas.ProjectResponse.model_validate(project).model_dump()
    project_dict["owner_username"] = project.owner.usuario if project.owner else None
    return schemas.ProjectResponse(**project_dict)


# --- ROTA: OBTER PROGRESSO DO PROCESSAMENTO ---
@router.get("/{project_id}/progress", response_model=schemas.ProjectProgressResponse)
def get_project_progress(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Retorna o progresso do processamento do relatório."""
    # Buscar projeto
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Buscar relatório
    report = db.query(models.ProjectReport).filter(
        models.ProjectReport.project_id == project_id
    ).first()
    
    # Determinar se pode fazer retry
    can_retry = project.status == models.ProjectStatus.PROCESSING_ERROR
    
    return schemas.ProjectProgressResponse(
        project_id=project_id,
        status=project.status.value,
        processing_status=report.processing_status if report else "pending",
        processing_progress=report.processing_progress if report else 0.0,
        processing_step=report.processing_step if report else None,
        error_message=report.error_message if report else None,
        can_retry=can_retry
    )


# --- ROTA: RETRY DO PROCESSAMENTO (PROCESSING_ERROR -> PROCESSING_REPORT) ---
@router.post("/{project_id}/retry", response_model=schemas.ProjectProgressResponse)
def retry_project_processing(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Reprocessa um projeto que teve erro."""
    from backend.services.data_validation.tasks import process_project_report
    
    # Buscar projeto
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Verificar se é o owner ou admin
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para reprocessar")
    
    # Verificar se está em PROCESSING_ERROR
    if project.status != models.ProjectStatus.PROCESSING_ERROR:
        raise HTTPException(
            status_code=400, 
            detail=f"Apenas projetos com erro podem ser reprocessados. Status atual: {project.status.value}"
        )
    
    # Resetar relatório
    report = db.query(models.ProjectReport).filter(
        models.ProjectReport.project_id == project_id
    ).first()
    
    if report:
        report.processing_status = "pending"
        report.processing_progress = 0.0
        report.processing_step = None
        report.error_message = None
        report.error_traceback = None
    
    # Mudar status
    project.status = models.ProjectStatus.PENDING_REVIEW
    db.commit()
    
    # Disparar task Celery
    try:
        task = process_project_report.delay(project_id)
        if report:
            report.celery_task_id = task.id
            db.commit()
        print(f"🔄 Retry: Task Celery disparada: {task.id} para projeto {project_id}", flush=True)
    except Exception as e:
        print(f"⚠️ Erro ao disparar task Celery: {e}", flush=True)
    
    return schemas.ProjectProgressResponse(
        project_id=project_id,
        status=project.status.value,
        processing_status="pending",
        processing_progress=0.0,
        processing_step="Iniciando reprocessamento...",
        error_message=None,
        can_retry=False
    )


# --- ROTA: RECALCULAR RELATÓRIO (READY_TO_PUBLISH -> PROCESSING_REPORT) ---
@router.post("/{project_id}/recalculate", response_model=schemas.ProjectProgressResponse)
def recalculate_project_report(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Recalcula o relatório de um projeto pronto para publicação."""
    from backend.services.data_validation.tasks import recalculate_project_report as recalc_task
    
    # Apenas admins podem recalcular
    if current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Apenas administradores podem recalcular relatórios")
    
    # Buscar projeto
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Verificar se está em READY_TO_PUBLISH
    if project.status != models.ProjectStatus.READY_TO_PUBLISH:
        raise HTTPException(
            status_code=400, 
            detail=f"Apenas projetos prontos para publicação podem ser recalculados. Status atual: {project.status.value}"
        )
    
    # Mudar status
    project.status = models.ProjectStatus.PROCESSING_REPORT
    db.commit()
    
    # Disparar task Celery de recálculo
    try:
        task = recalc_task.delay(project_id)
        print(f"🔄 Recalculate: Task Celery disparada: {task.id} para projeto {project_id}", flush=True)
    except Exception as e:
        print(f"⚠️ Erro ao disparar task Celery: {e}", flush=True)
    
    return schemas.ProjectProgressResponse(
        project_id=project_id,
        status=project.status.value,
        processing_status="pending",
        processing_progress=0.0,
        processing_step="Recalculando relatório...",
        error_message=None,
        can_retry=False
    )


# --- ROTA: OBTER RELATÓRIO COMPLETO ---
@router.get("/{project_id}/report", response_model=schemas.ProjectReportResponse)
def get_project_report(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Retorna o relatório completo do projeto."""
    # Buscar projeto
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Buscar relatório
    report = db.query(models.ProjectReport).filter(
        models.ProjectReport.project_id == project_id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    
    # Determinar se pode publicar
    can_publish = (
        project.status == models.ProjectStatus.READY_TO_PUBLISH and
        report.processing_status == "completed" and
        report.production_db_ready
    )
    
    # Converter brands_to_create para schema
    brands_to_create = [
        schemas.BrandToCreateSchema(**b) if isinstance(b, dict) else b
        for b in (report.brands_to_create or [])
    ]
    
    return schemas.ProjectReportResponse(
        project_id=project_id,
        total_rows=report.total_rows,
        columns_found=report.columns_found or [],
        parts_new=report.parts_new,
        parts_existing=report.parts_existing,
        brands_new=report.brands_new,
        brands_existing=report.brands_existing,
        brands_to_create=brands_to_create,
        processing_status=report.processing_status,
        processing_progress=report.processing_progress,
        processing_step=report.processing_step,
        processing_time_seconds=report.processing_time_seconds,
        error_message=report.error_message,
        production_db_status=report.production_db_status,
        production_db_ready=report.production_db_ready,
        can_publish=can_publish
    )


# --- NOVA ROTA: DOWNLOAD CSV ---
@router.get("/{project_id}/download")
def download_csv(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Exporta os dados do DuckDB para CSV e retorna para download."""
    # 1. Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Admin pode baixar qualquer projeto
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão de acesso a este projeto.")
    
    # 2. Gerar arquivo CSV temporário
    output_csv = os.path.join(duck_manager.TEMP_DIR, f"{project_id}_export.csv")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        duck.export_to_csv(output_csv)
        
        # 3. Retornar arquivo para download
        return FileResponse(
            path=output_csv,
            filename=f"{project.original_filename.replace('.csv', '')}_processed.csv",
            media_type="text/csv",
            background=None  # Não deletar automaticamente, vamos gerenciar manualmente
        )
    except Exception as e:
        if os.path.exists(output_csv):
            os.remove(output_csv)
        raise HTTPException(status_code=500, detail=f"Erro ao exportar CSV: {str(e)}")

# --- FASE 1: TRATAMENTO DE COLUNAS (MAPEAMENTO) ---

@router.get("/{project_id}/columns/analysis", response_model=schemas.ColumnsAnalysisResponse)
def analyze_columns(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Analisa a estrutura das colunas: faltantes, extras e presentes."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão de acesso a este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        db_columns = duck.get_columns()
        
        # Operações de conjunto
        found = set(db_columns)
        required = constants.REQUIRED_COLUMNS
        optional = constants.OPTIONAL_COLUMNS
        all_valid = required | optional
        
        missing = list(required - found)        # Obrigatórias que faltam
        extra = list(found - all_valid)         # Não reconhecidas
        present = list(found & all_valid)       # Presentes e reconhecidas
        
        return {
            "missing": missing,
            "extra": extra,
            "present": present,
            "required": list(required),
            "optional": list(optional)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar colunas: {str(e)}")

@router.post("/{project_id}/columns/rename", response_model=schemas.RenameColumnResponse)
def rename_column(
    project_id: str,
    rename_request: schemas.RenameColumnRequest,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Renomeia uma coluna da tabela."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    # Validar se new_name está nas colunas permitidas
    all_valid = constants.REQUIRED_COLUMNS | constants.OPTIONAL_COLUMNS
    if rename_request.new_name not in all_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Nome '{rename_request.new_name}' não é uma coluna válida. Deve ser uma coluna obrigatória ou opcional."
        )
    
    try:
        duck = duck_manager.DuckSession(project_id)
        
        # Verificar se a coluna antiga existe
        current_columns = duck.get_columns()
        if rename_request.old_name not in current_columns:
            raise HTTPException(status_code=404, detail=f"Coluna '{rename_request.old_name}' não encontrada")
        
        # Verificar se o novo nome já existe
        if rename_request.new_name in current_columns:
            raise HTTPException(status_code=400, detail=f"Coluna '{rename_request.new_name}' já existe")
        
        # Renomear
        duck.rename_column(rename_request.old_name, rename_request.new_name)
        
        return {
            "message": "Coluna renomeada com sucesso",
            "old_name": rename_request.old_name,
            "new_name": rename_request.new_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao renomear coluna: {str(e)}")

# --- FASE 2: TRATAMENTO AUTOMATIZADO (DATA HYGIENE) ---

@router.get("/{project_id}/treatments/diagnosis", response_model=schemas.TreatmentDiagnosisResponse)
def diagnose_treatments(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Diagnostica problemas de qualidade de dados: uppercase, nulos, validações avançadas."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão de acesso a este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        
        # Diagnósticos básicos (Fase 2)
        uppercase_issues = duck.diagnose_uppercase_issues(constants.STRING_CHECK_COLUMNS)
        null_string_issues = duck.diagnose_null_strings(constants.STRING_CHECK_COLUMNS)
        null_numeric_issues = duck.diagnose_null_numerics(constants.NUMERIC_CHECK_COLUMNS)
        
        # Diagnósticos avançados (Fase 2.1)
        brand_issues = duck.diagnose_brand_issues()
        ncm_issues = duck.diagnose_ncm_issues()
        barcode_issues = duck.diagnose_barcode_issues()
        weight_issues = duck.diagnose_weight_issues()
        dimension_issues = duck.diagnose_dimension_issues()
        search_ref_issues = duck.diagnose_search_ref_issues()
        manufacturer_ref_issues = duck.diagnose_manufacturer_ref_issues()
        
        return {
            # Básicos
            "uppercase_issues": uppercase_issues,
            "null_string_issues": null_string_issues,
            "null_numeric_issues": null_numeric_issues,
            # Avançados
            "brand_issues": brand_issues,
            "ncm_issues": ncm_issues,
            "barcode_issues": barcode_issues,
            "weight_issues": weight_issues,
            "dimension_issues": dimension_issues,
            "search_ref_issues": search_ref_issues,
            "manufacturer_ref_issues": manufacturer_ref_issues
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao diagnosticar tratamentos: {str(e)}")

@router.post("/{project_id}/treatments/fix-nulls-string", response_model=schemas.TreatmentFixResponse)
def fix_null_strings(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Corrige valores nulos e 'nan' em colunas de string, substituindo por string vazia."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.fix_null_strings(constants.STRING_CHECK_COLUMNS)
        
        return {
            "message": "Nulos em colunas de string corrigidos com sucesso",
            "columns_affected": result["columns"],
            "rows_affected": result["rows_affected"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao corrigir nulos em strings: {str(e)}")

@router.post("/{project_id}/treatments/fix-uppercase", response_model=schemas.TreatmentFixResponse)
def fix_uppercase(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Converte todos os valores de colunas de string para UPPERCASE."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.apply_uppercase_fix(constants.STRING_CHECK_COLUMNS)
        
        return {
            "message": "Valores convertidos para UPPERCASE com sucesso",
            "columns_affected": result["columns"],
            "rows_affected": result["rows_affected"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao aplicar uppercase: {str(e)}")

@router.post("/{project_id}/treatments/fix-nulls-numeric", response_model=schemas.TreatmentFixResponse)
def fix_null_numerics(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Corrige valores nulos em colunas numéricas, substituindo por 0."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.fix_null_numerics(constants.NUMERIC_CHECK_COLUMNS)
        
        return {
            "message": "Nulos em colunas numéricas corrigidos com sucesso",
            "columns_affected": result["columns"],
            "rows_affected": result["rows_affected"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao corrigir nulos em numéricos: {str(e)}")

# --- FASE 2.2: CORREÇÕES AUTOMÁTICAS AVANÇADAS ---

@router.post("/{project_id}/treatments/fix-barcode", response_model=schemas.TreatmentFixResponse)
def fix_barcode(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Corrige barcodes: calcula checksum EAN-13, adiciona zeros à esquerda."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.apply_barcode_fix()
        
        return {
            "message": "Barcodes corrigidos com sucesso (EAN-13 checksum aplicado)",
            "columns_affected": result["columns"],
            "rows_affected": result["rows_affected"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao corrigir barcodes: {str(e)}")

@router.post("/{project_id}/treatments/fix-ncm", response_model=schemas.TreatmentFixResponse)
def fix_ncm(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Sanitiza NCM removendo pontos, espaços e caracteres não-numéricos."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.apply_ncm_fix()
        
        return {
            "message": "NCM sanitizado com sucesso (apenas números)",
            "columns_affected": result["columns"],
            "rows_affected": result["rows_affected"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao corrigir NCM: {str(e)}")

@router.post("/{project_id}/treatments/fix-codes", response_model=schemas.TreatmentFixResponse)
def fix_codes(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Sanitiza search_ref e manufacturer_ref: TRIM, UPPER, remove caracteres especiais."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.apply_codes_fix()
        
        return {
            "message": "Códigos sanitizados com sucesso (UPPER + alfanuméricos apenas)",
            "columns_affected": result["columns"],
            "rows_affected": result["rows_affected"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao corrigir códigos: {str(e)}")

@router.post("/{project_id}/treatments/fix-negative-weights", response_model=schemas.TreatmentFixResponse)
def fix_negative_weights(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Converte pesos negativos em valores absolutos."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.apply_negative_weights_fix()
        
        return {
            "message": "Pesos negativos corrigidos com sucesso (valores absolutos aplicados)",
            "columns_affected": result["columns"],
            "rows_affected": result["rows_affected"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao corrigir pesos negativos: {str(e)}")

@router.post("/{project_id}/treatments/fix-dimensions", response_model=schemas.TreatmentFixResponse)
def fix_dimensions(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Corrige problemas em dimensões (placeholder - implementação futura)."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    # Por enquanto, retorna sucesso sem fazer nada
    # TODO: Implementar lógica de correção de dimensões no duck_manager
    return {
        "message": "Correção de dimensões não implementada ainda",
        "columns_affected": [],
        "rows_affected": 0
    }

# --- ANÁLISE E REMOÇÃO DE DUPLICADAS ---

@router.get("/{project_id}/duplicates/analysis", response_model=schemas.DuplicatesAnalysisResponse)
def analyze_duplicates(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Analisa peças duplicadas baseado em search_ref + brand."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão de acesso a este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.analyze_duplicates()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar duplicadas: {str(e)}")

@router.get("/{project_id}/duplicates/diagnosis", response_model=schemas.DuplicatesDiagnosisResponse)
def diagnose_duplicates(
    project_id: str,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Diagnostica duplicatas e retorna preview paginado das linhas que serão removidas."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão de acesso a este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.get_duplicates_diagnosis(
            columns=["search_ref", "brand"],
            page=page,
            page_size=page_size
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao diagnosticar duplicadas: {str(e)}")

@router.post("/{project_id}/duplicates/remove", response_model=schemas.TreatmentFixResponse)
def remove_duplicates(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Remove peças duplicadas mantendo apenas a primeira ocorrência de cada search_ref + brand."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.remove_duplicates()
        
        return {
            "message": "Duplicadas removidas com sucesso (mantida apenas primeira ocorrência)",
            "columns_affected": ["search_ref", "brand"],
            "rows_affected": result["rows_affected"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao remover duplicadas: {str(e)}")

# --- ROTA: ESTATÍSTICAS MATEMÁTICAS ---
@router.get("/{project_id}/statistics")
def get_statistics(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """Retorna estatísticas completas: resumo numérico, correlações e violações físicas."""
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão de acesso a este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        stats = duck.get_statistics()
        
        return {
            "project_id": project_id,
            "summary": stats["summary"],
            "violations": stats["violations"],
            "correlation": stats["correlation"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular estatísticas: {str(e)}")

# --- VALIDAÇÃO DE SIMILARIDADES ---

@router.get("/{project_id}/similarities/diagnosis", response_model=schemas.SimilaritiesDiagnosisResponse)
def diagnose_similarities(
    project_id: str,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Diagnostica a coluna similarity e retorna preview paginado das linhas com problemas.
    
    Validações:
    - Verifica se a coluna existe
    - Valida formato JSON (lista de dicionários)
    - Valida chaves obrigatórias (search_ref e brand)
    - Valida search_ref (sem espaços nem caracteres especiais)
    - Valida brand (deve estar em MAIÚSCULAS)
    - Verifica se search_ref existe no projeto
    - Verifica se brand está no mapeamento
    - Verifica se valores NULL devem ser []
    """
    # Verificar se o projeto existe e pertence ao utilizador
    print(f"DEBUG SIMILARITIES: Buscando projeto com ID: {project_id}")
    print(f"DEBUG SIMILARITIES: Tipo do project_id: {type(project_id)}")
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    print(f"DEBUG SIMILARITIES: Projeto encontrado: {project}")
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão de acesso a este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.diagnose_similarities(page=page, page_size=page_size)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao diagnosticar similaridades: {str(e)}")

@router.post("/{project_id}/similarities/fix-all", response_model=schemas.TreatmentFixResponse)
def fix_all_similarities(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Aplica todas as correções na coluna similarity:
    - Normaliza search_ref (remove espaços e caracteres especiais)
    - Converte brands para MAIÚSCULAS
    - Aplica mapeamento de marcas
    - Converte NULL para []
    """
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    # Verificar se o projeto está em modo DRAFT
    if project.status != models.ProjectStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Projeto não pode ser alterado. Status atual: {project.status.value}. Apenas projetos em DRAFT podem ser editados."
        )
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.fix_all_similarities()
        
        return {
            "message": "Todas as correções foram aplicadas na coluna similarity",
            "columns_affected": ["similarity"],
            "rows_affected": result["rows_affected"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao corrigir similaridades: {str(e)}")

@router.get("/{project_id}/similarities/statistics", response_model=schemas.SimilaritiesStatisticsResponse)
def get_similarities_statistics(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Retorna estatísticas detalhadas sobre as similaridades:
    - Total de linhas com/sem similaridades
    - Média de similaridades por linha
    - Top 10 search_refs mais referenciados
    - Top 10 marcas mais referenciadas
    - Distribuição de quantidade de similaridades
    - Refs/brands inexistentes
    """
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão de acesso a este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.get_similarities_statistics()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular estatísticas de similaridades: {str(e)}")

# --- FASE 3: MAPEAMENTO DE MARCAS ---

@router.get("/{project_id}/brands/analysis", response_model=schemas.BrandAnalysisResponse)
def analyze_brands(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Analisa o impacto do mapeamento de marcas nos dados.
    
    Retorna métricas sobre quantas marcas serão corrigidas, quais são desconhecidas,
    e mostra as top 5 correções que serão aplicadas.
    """
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão de acesso a este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        analysis = duck.analyze_brands()
        
        return schemas.BrandAnalysisResponse(
            total_rows=analysis["total_rows"],
            mapped_count=analysis["mapped_count"],
            unknown_count=analysis["unknown_count"],
            top_corrections=[
                schemas.BrandCorrection(**correction)
                for correction in analysis["top_corrections"]
            ],
            unknown_brands=[
                schemas.UnknownBrand(**brand)
                for brand in analysis["unknown_brands"]
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar marcas: {str(e)}")

@router.post("/{project_id}/brands/apply", response_model=schemas.BrandApplicationResponse)
def apply_brand_normalization(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Aplica a normalização de marcas usando o mapeamento.
    
    Executa um UPDATE massivo que corrige os nomes de marcas de acordo
    com o arquivo de mapeamento. Apenas projetos em modo DRAFT podem ser alterados.
    """
    # Verificar se o projeto existe e pertence ao utilizador
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este projeto.")
    
    # Verificar se o projeto está em modo DRAFT
    if project.status != models.ProjectStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Projeto não pode ser alterado. Status atual: {project.status.value}. Apenas projetos em DRAFT podem ser editados."
        )
    
    try:
        duck = duck_manager.DuckSession(project_id)
        result = duck.apply_brand_normalization()
        
        return schemas.BrandApplicationResponse(
            message=result["message"],
            rows_affected=result["rows_affected"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao aplicar normalização de marcas: {str(e)}")

# --- ROTA: RELATÓRIO DE QUALIDADE (ADMIN) ---
@router.get("/{project_id}/quality-report", response_model=schemas.QualityReportResponse)
def get_quality_report(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Gera relatório consolidado de qualidade para revisão do admin.
    
    Agrega métricas de todas as etapas de validação e calcula um score geral.
    Usado na aba de Relatório de Qualidade da interface do admin.
    """
    # Verificar se o projeto existe
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Apenas admin pode acessar o relatório (ou owner)
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão de acesso a este projeto.")
    
    try:
        duck = duck_manager.DuckSession(project_id)
        
        # 1. Analisar estrutura das colunas (replicar lógica do endpoint columns/analysis)
        db_columns = duck.get_columns()
        found = set(db_columns)
        required = constants.REQUIRED_COLUMNS
        optional = constants.OPTIONAL_COLUMNS
        all_valid = required | optional
        
        missing = list(required - found)
        extra = list(found - all_valid)
        present = list(found & all_valid)
        
        structural = schemas.StructuralQuality(
            required_columns_present=len([col for col in present if col in constants.REQUIRED_COLUMNS]),
            required_columns_total=len(constants.REQUIRED_COLUMNS),
            extra_columns_mapped=len(extra),
            missing_columns=len(missing)
        )
        
        # 2. Diagnosticar problemas de qualidade de dados (replicar lógica do endpoint treatments/diagnosis)
        uppercase_issues = duck.diagnose_uppercase_issues(constants.STRING_CHECK_COLUMNS)
        null_string_issues = duck.diagnose_null_strings(constants.STRING_CHECK_COLUMNS)
        null_numeric_issues = duck.diagnose_null_numerics(constants.NUMERIC_CHECK_COLUMNS)
        
        brand_issues = duck.diagnose_brand_issues()
        ncm_issues = duck.diagnose_ncm_issues()
        barcode_issues = duck.diagnose_barcode_issues()
        weight_issues = duck.diagnose_weight_issues()
        dimension_issues = duck.diagnose_dimension_issues()
        search_ref_issues = duck.diagnose_search_ref_issues()
        manufacturer_ref_issues = duck.diagnose_manufacturer_ref_issues()
        
        # Contar total de linhas
        conn = duck._get_conn(read_only=True)
        try:
            total_rows = conn.execute("SELECT COUNT(*) FROM raw_data").fetchone()[0]
            
            # Calcular completude (baseado em colunas com nulls)
            if len(constants.STRING_CHECK_COLUMNS) > 0:
                valid_cols = [col for col in list(constants.STRING_CHECK_COLUMNS)[:5] if col in db_columns]
                if valid_cols:
                    null_query = "SELECT " + ", ".join([
                        f"COUNT(*) - COUNT(\"{col}\") as {col}_nulls"
                        for col in valid_cols
                    ]) + " FROM raw_data"
                    null_result = conn.execute(null_query).fetchone()
                    max_nulls = max(null_result) if null_result else 0
                else:
                    max_nulls = 0
            else:
                max_nulls = 0
        finally:
            conn.close()
        
        completeness_pct = 100.0 if total_rows == 0 else ((total_rows - max_nulls) / total_rows) * 100
        
        data_quality = schemas.DataQualityMetrics(
            completeness_pct=round(completeness_pct, 2),
            total_rows=total_rows,
            uppercase_issues=len(uppercase_issues),
            null_string_issues=len(null_string_issues),
            null_numeric_issues=len(null_numeric_issues),
            brand_issues=brand_issues,
            ncm_issues=ncm_issues,
            barcode_issues=barcode_issues,
            weight_issues=weight_issues,
            dimension_issues=dimension_issues,
            search_ref_issues=search_ref_issues,
            manufacturer_ref_issues=manufacturer_ref_issues
        )
        
        # 3. Analisar marcas
        brand_analysis = duck.analyze_brands()
        brands = schemas.BrandQualityMetrics(
            total_rows=brand_analysis["total_rows"],
            normalized_count=brand_analysis["mapped_count"],
            normalized_pct=round((brand_analysis["mapped_count"] / brand_analysis["total_rows"] * 100) if brand_analysis["total_rows"] > 0 else 0, 2),
            unknown_count=brand_analysis["unknown_count"],
            unknown_pct=round((brand_analysis["unknown_count"] / brand_analysis["total_rows"] * 100) if brand_analysis["total_rows"] > 0 else 0, 2),
            top_unknown_brands=[
                schemas.UnknownBrand(**brand)
                for brand in brand_analysis["unknown_brands"][:5]  # Top 5
            ]
        )
        
        # 4. Diagnosticar duplicatas (current state)
        try:
            dup_diagnosis = duck.diagnose_duplicates(page=1, limit=1)  # Apenas contar
            duplicates = schemas.DuplicatesQuality(
                found=dup_diagnosis["total_duplicates"],
                removed=0  # Assumindo que ainda não foram removidas ou já foram
            )
        except:
            duplicates = schemas.DuplicatesQuality(found=0, removed=0)
        
        # 5. Estatísticas e violações
        stats = duck.get_statistics()
        statistics = schemas.StatisticsQuality(
            weight_correlation=stats["correlation"],
            physical_violations=stats["violations"]["count_weight_error"],
            negative_values=stats["violations"]["count_negative"]
        )
        
        # 6. Calcular score geral (0-100)
        # - Estrutura: 25 pontos (colunas obrigatórias presentes)
        # - Completude: 25 pontos (% de dados preenchidos)
        # - Marcas: 20 pontos (% de marcas reconhecidas)
        # - Qualidade: 20 pontos (baseado em issues)
        # - Estatísticas: 10 pontos (violações e correlação)
        
        structure_score = (structural.required_columns_present / structural.required_columns_total) * 25 if structural.required_columns_total > 0 else 0
        completeness_score = (completeness_pct / 100) * 25
        brands_score = (brands.normalized_pct / 100) * 20
        
        # Qualidade: quanto menos issues, melhor
        total_issues = (
            data_quality.uppercase_issues +
            data_quality.null_string_issues +
            data_quality.null_numeric_issues +
            data_quality.brand_issues +
            data_quality.ncm_issues +
            data_quality.barcode_issues +
            data_quality.weight_issues +
            data_quality.dimension_issues +
            data_quality.search_ref_issues +
            data_quality.manufacturer_ref_issues
        )
        issue_ratio = total_issues / total_rows if total_rows > 0 else 0
        quality_score = max(0, 20 - (issue_ratio * 100))  # Penaliza proporcional aos issues
        
        # Estatísticas: penaliza violações
        violations_ratio = (statistics.physical_violations + statistics.negative_values) / total_rows if total_rows > 0 else 0
        stats_score = max(0, 10 - (violations_ratio * 100))
        
        overall_score = round(structure_score + completeness_score + brands_score + quality_score + stats_score, 2)
        
        # 7. Gerar warnings e blockers
        warnings = []
        blockers = []
        
        if structural.missing_columns > 0:
            blockers.append(f"{structural.missing_columns} colunas obrigatórias faltando")
        
        if brands.unknown_pct > 10:
            warnings.append(f"{brands.unknown_pct}% de marcas desconhecidas ({brands.unknown_count} linhas)")
        
        if statistics.physical_violations > 0:
            warnings.append(f"{statistics.physical_violations} violações físicas detectadas (peso líquido > bruto)")
        
        if statistics.negative_values > 0:
            warnings.append(f"{statistics.negative_values} valores negativos em campos numéricos")
        
        if duplicates.found > 0:
            warnings.append(f"{duplicates.found} linhas duplicadas encontradas")
        
        if completeness_pct < 90:
            warnings.append(f"Completude dos dados: {completeness_pct}% (recomendado > 90%)")
        
        if total_issues > (total_rows * 0.1):  # Mais de 10% com issues
            warnings.append(f"{total_issues} problemas de qualidade encontrados ({round(issue_ratio * 100, 2)}% dos dados)")
        
        return schemas.QualityReportResponse(
            project_id=project_id,
            overall_quality_score=overall_score,
            structural=structural,
            data_quality=data_quality,
            brands=brands,
            duplicates=duplicates,
            statistics=statistics,
            warnings=warnings,
            blockers=blockers
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório de qualidade: {str(e)}")


# ============================================================================
# PUBLICAÇÃO PARA BANCO DE PRODUÇÃO
# ============================================================================

from backend.services.data_validation import publish_schemas, publish_service
from backend.services.data_validation.production_db import test_production_connection

# IMPORTANTE: Endpoints estáticos devem vir ANTES dos endpoints com {project_id}
# para evitar que o FastAPI interprete "publish" como um project_id

@router.get("/publish/db-status", response_model=publish_schemas.ProductionDBStatus)
def get_production_db_status(
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Verifica o status da conexão com o banco de produção.
    Apenas admins podem acessar este endpoint.
    """
    print(f"🔌 [DB-STATUS] Verificando status do banco de produção...", flush=True)
    
    if current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Apenas administradores podem verificar status do banco de produção")
    
    try:
        status = test_production_connection()
        print(f"🔌 [DB-STATUS] Status: {status}", flush=True)
        return publish_schemas.ProductionDBStatus(**status)
    except Exception as e:
        print(f"🔌 [DB-STATUS] Erro: {e}", flush=True)
        return publish_schemas.ProductionDBStatus(
            status='error',
            host='unknown',
            database='unknown',
            ready=False,
            error=str(e)
        )


@router.get("/publish/available-fields", response_model=publish_schemas.AvailableFieldsResponse)
def get_available_fields(
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Retorna lista de campos disponíveis para configuração na publicação.
    Apenas admins podem acessar este endpoint.
    """
    print(f"📋 [AVAILABLE-FIELDS] Retornando campos disponíveis...", flush=True)
    
    if current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Apenas administradores podem acessar configuração de campos")
    
    return publish_schemas.AvailableFieldsResponse()


@router.get("/{project_id}/publish/preview", response_model=publish_schemas.PublishPreviewResponse)
def get_publish_preview(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Preview da publicação: mostra o que será criado/atualizado no banco de produção.
    Apenas admins podem acessar este endpoint.
    """
    import logging
    import sys
    logger = logging.getLogger(__name__)
    
    # Print direto para stdout para garantir que aparece
    print(f"🚀 [ENDPOINT] publish/preview chamado para projeto: {project_id}", flush=True)
    sys.stdout.flush()
    
    logger.info(f"🚀 [ENDPOINT] publish/preview chamado para projeto: {project_id}")
    logger.info(f"🚀 [ENDPOINT] Usuário: {current_user.usuario}, Role: {current_user.role}")
    
    # Verificar se é admin
    if current_user.role != "adm":
        logger.warning(f"🚀 [ENDPOINT] Acesso negado - usuário não é admin")
        raise HTTPException(status_code=403, detail="Apenas administradores podem publicar dados")
    
    logger.info(f"🚀 [ENDPOINT] Buscando projeto no banco de metadados...")
    
    # Verificar se projeto existe
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        logger.warning(f"🚀 [ENDPOINT] Projeto não encontrado: {project_id}")
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    logger.info(f"🚀 [ENDPOINT] Projeto encontrado. Status: {project.status}")
    
    # Verificar se está em status READY_TO_PUBLISH
    if project.status != models.ProjectStatus.READY_TO_PUBLISH:
        logger.warning(f"🚀 [ENDPOINT] Status inválido: {project.status.value}")
        raise HTTPException(
            status_code=400, 
            detail=f"Projeto deve estar em status READY_TO_PUBLISH para publicação. Status atual: {project.status.value}"
        )
    
    logger.info(f"🚀 [ENDPOINT] Chamando publish_service.get_publish_preview()...")
    
    try:
        preview = publish_service.get_publish_preview(project_id)
        logger.info(f"🚀 [ENDPOINT] Preview gerado com sucesso!")
        return preview
    except Exception as e:
        logger.error(f"🚀 [ENDPOINT] Erro ao gerar preview: {e}")
        import traceback
        logger.error(f"🚀 [ENDPOINT] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar preview: {str(e)}")


@router.post("/{project_id}/publish", response_model=publish_schemas.PublishResponse)
def execute_publish(
    project_id: str,
    request: publish_schemas.PublishRequest,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Executa a publicação dos dados validados para o banco de produção.
    
    Este endpoint:
    1. Valida permissões (apenas admin)
    2. Verifica status do projeto (deve ser PENDING_REVIEW)
    3. Executa o pipeline de publicação com rollback em caso de erro
    4. Atualiza status do projeto para DONE
    5. Remove o arquivo DuckDB
    
    Apenas admins podem acessar este endpoint.
    """
    # Verificar se é admin
    if current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Apenas administradores podem publicar dados")
    
    # Verificar se projeto existe
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Verificar se está em status READY_TO_PUBLISH
    if project.status != models.ProjectStatus.READY_TO_PUBLISH:
        raise HTTPException(
            status_code=400, 
            detail=f"Projeto deve estar em status READY_TO_PUBLISH para publicação. Status atual: {project.status.value}"
        )
    
    try:
        # Usar autor como o usuário atual (admin que está publicando)
        # Para current_owner_id, usar o ID fornecido ou None
        author_id = request.author_id or current_user.id
        current_owner_id = request.current_owner_id
        
        # Executar publicação
        result = publish_service.execute_publish(
            project_id=project_id,
            config=request.configuration,
            author_id=author_id,
            current_owner_id=current_owner_id
        )
        
        if result.success:
            # Atualizar status do projeto para DONE
            project.status = models.ProjectStatus.DONE
            project.approved_at = db_func.now()
            
            # Atualizar ProjectReport com informações de publicação
            report = db.query(models.ProjectReport).filter(
                models.ProjectReport.project_id == project_id
            ).first()
            
            if report:
                report.published_at = db_func.now()
                report.published_by_id = current_user.id
                report.parts_created = result.parts_inserted
                report.parts_updated = result.parts_updated
                # Calcular tempo de publicação baseado no tempo total de processamento
                if result.execution_time_seconds:
                    report.publish_time_seconds = result.execution_time_seconds
            
            db.commit()
            
            # Remover arquivo DuckDB
            duckdb_deleted = publish_service.cleanup_project_files(project_id)
            
            return publish_schemas.PublishResponse(
                result=result,
                project_status=models.ProjectStatus.DONE.value,
                duckdb_deleted=duckdb_deleted
            )
        else:
            # Publicação falhou - não altera status
            return publish_schemas.PublishResponse(
                result=result,
                project_status=project.status.value,
                duckdb_deleted=False
            )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao executar publicação: {str(e)}")


# ==============================================================================
# ROTAS PARA PROCESSAMENTO DE IMAGENS (lambda_function)
# ==============================================================================

@router.post("/{project_id}/images/upload", response_model=schemas.ImageUploadResponse)
def upload_images_batch(
    project_id: str,
    request: schemas.ImageUploadRequest,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Inicia o processamento de um batch de imagens para um projeto.
    
    As imagens são processadas em background via Celery:
    1. Redimensionamento para 4 variantes (high, medium, low, watermark)
    2. Upload para S3
    3. Agrupamento por SKU
    
    O environment define a pasta de destino no S3:
    - 'test': pasta 'test-lambda'
    - 'production': pasta 'media'
    """
    # Verificar se o projeto existe
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Verificar permissão (owner ou admin)
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para este projeto")
    
    # Validar environment
    valid_environments = ['test', 'production']
    if request.environment not in valid_environments:
        raise HTTPException(
            status_code=400,
            detail=f"Ambiente inválido: {request.environment}. Use: {valid_environments}"
        )
    
    # Verificar se há imagens
    if not request.images:
        raise HTTPException(status_code=400, detail="Nenhuma imagem fornecida")
    
    # Importar task aqui para evitar imports circulares
    from backend.services.data_validation.tasks import process_images_batch
    
    # Preparar dados para a task
    images_data = [
        {"filename": img.filename, "content": img.content}
        for img in request.images
    ]
    
    # Iniciar task Celery
    task = process_images_batch.delay(
        project_id=project_id,
        images_data=images_data,
        environment=request.environment
    )
    
    # Criar registro da task
    task_record = db.query(models.ImageProcessingTask).filter(
        models.ImageProcessingTask.project_id == project_id
    ).first()
    
    if not task_record:
        task_record = models.ImageProcessingTask(
            project_id=project_id,
            celery_task_id=task.id,
            environment=request.environment,
            total_images=len(request.images),
            status="pending"
        )
        db.add(task_record)
    else:
        task_record.celery_task_id = task.id
        task_record.environment = request.environment
        task_record.total_images = len(request.images)
        task_record.status = "pending"
    
    db.commit()
    
    return schemas.ImageUploadResponse(
        task_id=task.id,
        project_id=project_id,
        total_images=len(request.images),
        status="pending",
        message=f"Processamento iniciado. {len(request.images)} imagens serão processadas."
    )


@router.get("/{project_id}/images/status", response_model=schemas.ImageProcessingStatusResponse)
def get_images_processing_status(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Retorna o status atual do processamento de imagens de um projeto.
    """
    # Verificar se o projeto existe
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Verificar permissão
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para este projeto")
    
    # Buscar task
    task_record = db.query(models.ImageProcessingTask).filter(
        models.ImageProcessingTask.project_id == project_id
    ).first()
    
    if not task_record:
        return schemas.ImageProcessingStatusResponse(
            project_id=project_id,
            status="not_started",
            progress=0.0,
            total_images=0,
            processed_images=0,
            failed_images=0
        )
    
    return schemas.ImageProcessingStatusResponse(
        project_id=project_id,
        task_id=task_record.celery_task_id,
        environment=task_record.environment or "test",
        status=task_record.status,
        progress=task_record.processing_progress or 0.0,
        current_step=task_record.processing_step,
        total_images=task_record.total_images or 0,
        processed_images=task_record.processed_images or 0,
        failed_images=task_record.failed_images or 0,
        processing_time_seconds=task_record.processing_time_seconds,
        error_message=task_record.error_message
    )


@router.get("/{project_id}/images/result", response_model=schemas.ImageProcessingResultResponse)
def get_images_processing_result(
    project_id: str,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Retorna o resultado completo do processamento de imagens.
    Inclui todas as URLs geradas agrupadas por SKU.
    """
    # Verificar se o projeto existe
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Verificar permissão
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para este projeto")
    
    # Buscar task
    task_record = db.query(models.ImageProcessingTask).filter(
        models.ImageProcessingTask.project_id == project_id
    ).first()
    
    if not task_record:
        raise HTTPException(status_code=404, detail="Nenhum processamento de imagens encontrado")
    
    if task_record.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Processamento ainda não concluído. Status: {task_record.status}"
        )
    
    # Converter result_data para o formato esperado
    results = {}
    if task_record.result_data:
        for sku, urls in task_record.result_data.items():
            results[sku] = schemas.ImageUrlSet(
                high=urls.get('high', []),
                medium=urls.get('medium', []),
                low=urls.get('low', []),
                watermark=urls.get('watermark', [])
            )
    
    errors = []
    if task_record.errors_data:
        for err in task_record.errors_data:
            errors.append(schemas.ImageProcessingError(
                filename=err.get('filename', ''),
                error=err.get('error', '')
            ))
    
    return schemas.ImageProcessingResultResponse(
        project_id=project_id,
        status=task_record.status,
        total_images=task_record.total_images or 0,
        processed_images=task_record.processed_images or 0,
        failed_images=task_record.failed_images or 0,
        skus_count=len(results),
        results=results,
        errors=errors,
        processing_time_seconds=task_record.processing_time_seconds
    )


@router.post("/{project_id}/images/link", response_model=schemas.ImageLinkResponse)
def link_images_to_project(
    project_id: str,
    request: schemas.ImageLinkRequest = None,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Vincula as URLs de imagens processadas aos registros do DuckDB.
    
    Atualiza as colunas file_high, file_medium, file_low, file_water_mark
    baseado no search_ref de cada SKU.
    
    Se image_urls não for fornecido, usa o resultado da última task de processamento.
    """
    # Verificar se o projeto existe
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Verificar permissão
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para este projeto")
    
    # Obter URLs de imagens
    image_urls = None
    
    if request and request.image_urls:
        # Usar URLs fornecidas no request
        image_urls = {
            sku: {
                'high': url_set.high,
                'medium': url_set.medium,
                'low': url_set.low,
                'watermark': url_set.watermark
            }
            for sku, url_set in request.image_urls.items()
        }
    else:
        # Buscar da última task de processamento
        task_record = db.query(models.ImageProcessingTask).filter(
            models.ImageProcessingTask.project_id == project_id
        ).first()
        
        if not task_record or not task_record.result_data:
            raise HTTPException(
                status_code=400,
                detail="Nenhum resultado de processamento encontrado. Processe as imagens primeiro."
            )
        
        if task_record.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Processamento ainda não concluído. Status: {task_record.status}"
            )
        
        image_urls = task_record.result_data
    
    if not image_urls:
        raise HTTPException(status_code=400, detail="Nenhuma URL de imagem para vincular")
    
    # Vincular imagens ao DuckDB
    duck = duck_manager.DuckSession(project_id)
    result = duck.link_image_urls(image_urls)
    
    # Salvar resultado da vinculação
    linking_result = models.ImageLinkingResult(
        project_id=project_id,
        total_skus=result['total_skus'],
        linked_skus=result['linked_skus'],
        not_found_skus=result['not_found_skus']
    )
    db.add(linking_result)
    db.commit()
    
    # Preparar mensagem
    if result['not_found_skus']:
        message = (
            f"Vinculação concluída com alertas. "
            f"{result['linked_skus']}/{result['total_skus']} SKUs vinculados. "
            f"{len(result['not_found_skus'])} SKUs não encontrados no CSV."
        )
    else:
        message = f"Vinculação concluída com sucesso. {result['linked_skus']} SKUs vinculados."
    
    return schemas.ImageLinkResponse(
        project_id=project_id,
        total_skus=result['total_skus'],
        linked_skus=result['linked_skus'],
        not_found_skus=result['not_found_skus'],
        message=message
    )


@router.get("/{project_id}/images/preview")
def get_images_preview(
    project_id: str,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(database.get_db),
    current_user: core_models.User = Depends(deps.get_current_user)
):
    """
    Retorna preview dos registros com imagens vinculadas no DuckDB.
    """
    # Verificar se o projeto existe
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    # Verificar permissão
    if project.owner_id != current_user.id and current_user.role != "adm":
        raise HTTPException(status_code=403, detail="Sem permissão para este projeto")
    
    # Obter preview
    duck = duck_manager.DuckSession(project_id)
    return duck.get_image_linking_preview(page=page, page_size=page_size)