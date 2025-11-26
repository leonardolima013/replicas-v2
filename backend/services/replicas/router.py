from fastapi import APIRouter, Depends, HTTPException
from backend.core import deps, models
from backend.services.replicas import manager

router = APIRouter(prefix="/replicas", tags=["Réplicas"])

@router.post("/create")
def create_my_replica(current_user: models.User = Depends(deps.get_current_user)):
    """
    Cria um banco de dados exclusivo para o utilizador logado.
    """
    try:
        info = manager.create_replica_container(current_user.email)
        return {
            "msg": "Réplica criada com sucesso!",
            "details": info,
            "user": current_user.email
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))