from fastapi import APIRouter, Depends, HTTPException
from backend.core import deps, models
from backend.services.replicas import manager, schemas

router = APIRouter(prefix="/replicas", tags=["Réplicas"])

@router.post("/create")
def create_my_replica(
    replica_data: schemas.ReplicaCreate,
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Cria um banco de dados exclusivo para o utilizador logado.
    """
    try:
        info = manager.create_replica_container(current_user.usuario, replica_data.db_password)
        return {
            "msg": "Réplica criada com sucesso!",
            "details": info,
            "user": current_user.usuario
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
def list_all_replicas(
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Lista todas as réplicas ativas no sistema.
    Requer autenticação.
    """
    try:
        replicas = manager.list_all_replicas()
        return {
            "total": len(replicas),
            "replicas": replicas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-replica")
def get_my_replica(
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Retorna informações sobre a réplica do usuário logado.
    """
    try:
        replica = manager.get_user_replica(current_user.usuario)
        if not replica:
            raise HTTPException(status_code=404, detail="Réplica não encontrada")
        return replica
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{username}")
def get_replica_by_username(
    username: str,
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Retorna informações sobre a réplica de um usuário específico.
    Requer autenticação.
    """
    try:
        replica = manager.get_user_replica(username)
        if not replica:
            raise HTTPException(status_code=404, detail=f"Réplica do usuário '{username}' não encontrada")
        return replica
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/user/{username}")
def delete_replica_by_username(
    username: str,
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Deleta a réplica de um usuário específico.
    Requer autenticação.
    """
    try:
        result = manager.delete_user_replica(username)
        if not result:
            raise HTTPException(status_code=404, detail=f"Réplica do usuário '{username}' não encontrada")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-all")
def delete_all_replicas_endpoint(
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Deleta TODAS as réplicas do sistema.
    Requer autenticação. Use com cuidado!
    """
    try:
        result = manager.delete_all_replicas()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))