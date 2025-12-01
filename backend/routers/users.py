from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.core import models, schemas, security, database, deps
import docker

router = APIRouter(prefix="/users", tags=["Usuários"])

# Cliente Docker para deletar réplicas ao deletar usuário
docker_client = docker.from_env()

@router.post("/", response_model=schemas.UserResponse)
def create_user(
    user: schemas.UserCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Cria um novo usuário. Apenas ADMINs podem criar usuários.
    """
    # Verificar se o usuário logado é admin
    if current_user.role != "adm":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem criar usuários"
        )
    
    # Verificar se usuário já existe
    db_user = db.query(models.User).filter(models.User.usuario == user.usuario).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Usuário já cadastrado")
    
    # Criar novo usuário
    hashed_password = security.get_password_hash(user.password)
    new_user = models.User(usuario=user.usuario, hashed_password=hashed_password, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/", response_model=List[schemas.UserResponse])
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Lista todos os usuários. Apenas ADMINs podem listar usuários.
    """
    # Verificar se o usuário logado é admin
    if current_user.role != "adm":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem listar usuários"
        )
    
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@router.delete("/{username}")
def delete_user(
    username: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Deleta um usuário. Apenas ADMINs podem deletar usuários.
    Se o usuário tiver uma réplica, ela será deletada também.
    """
    # Verificar se o usuário logado é admin
    if current_user.role != "adm":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem deletar usuários"
        )
    
    # Não permitir que o admin delete a si mesmo
    if current_user.usuario == username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode deletar seu próprio usuário"
        )
    
    # Buscar usuário
    user = db.query(models.User).filter(models.User.usuario == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Tentar deletar a réplica do usuário (se existir)
    container_name = f"replica_{username}"
    replica_deleted = False
    
    try:
        container = docker_client.containers.get(container_name)
        if container.status == "running":
            container.stop()
        container.remove()
        replica_deleted = True
    except docker.errors.NotFound:
        # Usuário não tem réplica, tudo bem
        pass
    except Exception as e:
        # Log do erro mas continua com a deleção do usuário
        print(f"Erro ao deletar réplica do usuário {username}: {e}")
    
    # Deletar usuário do banco
    db.delete(user)
    db.commit()
    
    return {
        "msg": f"Usuário {username} deletado com sucesso",
        "replica_deleted": replica_deleted
    }
