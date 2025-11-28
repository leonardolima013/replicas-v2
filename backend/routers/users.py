from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.core import models, schemas, security, database, deps

router = APIRouter(prefix="/users", tags=["Usuários"])

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
