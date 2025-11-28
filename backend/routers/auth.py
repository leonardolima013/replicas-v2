from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.core import database, models, security

router = APIRouter(prefix="/auth", tags=["Autenticação"])

@router.post("/login")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(database.get_db)
):
    # 1. Busca usuário pelo usuario (form_data.username no OAuth2 é o nosso usuario)
    user = db.query(models.User).filter(models.User.usuario == form_data.username).first()
    
    # 2. Verifica se usuário existe e senha bate
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Gera o token
    access_token = security.create_access_token(
        data={"sub": user.usuario, "role": user.role}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}