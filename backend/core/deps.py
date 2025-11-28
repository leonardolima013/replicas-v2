from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from backend.core import database, models, security

# URL onde o frontend (ou Swagger) deve enviar o usuario/senha para pegar o token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Tenta decodificar o token
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        usuario: str = payload.get("sub")
        if usuario is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Busca o usuário no banco para garantir que ele ainda existe/está ativo
    user = db.query(models.User).filter(models.User.usuario == usuario).first()
    if user is None:
        raise credentials_exception
        
    return user