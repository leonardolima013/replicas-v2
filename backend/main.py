from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.core import models, schemas, security, database
from backend.routers import auth
from backend.services.replicas import router as replicas_router

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Replicas-v2")
app.include_router(auth.router)
app.include_router(replicas_router.router)

@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.usuario == user.usuario).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Usuário já cadastrado")
    
    hashed_password = security.get_password_hash(user.password)
    new_user = models.User(usuario=user.usuario, hashed_password=hashed_password, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/", response_model=List[schemas.UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users