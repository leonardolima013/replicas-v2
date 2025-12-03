from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os

from backend.core import models, database
from backend.routers import auth, users
from backend.services.replicas import router as replicas_router
from backend.services.data_validation import router as dv_router

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Replicas-v2")

# Configurar CORS para desenvolvimento
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas da API
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(replicas_router.router)
app.include_router(dv_router.router)

# Servir arquivos estáticos do frontend (após build em produção)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
IS_DEVELOPMENT = os.getenv("ENVIRONMENT", "development") == "development"

if frontend_dist.exists() and not IS_DEVELOPMENT:
    # Montar arquivos estáticos (CSS, JS, imagens)
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
    
    # Rota catch-all para SPA (React Router)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """
        Serve o index.html para todas as rotas que não sejam da API.
        Isso permite que o React Router funcione corretamente.
        """
        # Se for uma rota da API, não serve o frontend
        if full_path.startswith(("auth/", "users/", "replicas/", "validation/", "docs", "redoc", "openapi.json")):
            return {"detail": "Not Found"}
        
        # Para todas as outras rotas, serve o index.html
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"detail": "Frontend not built"}
else:
    # Em desenvolvimento, apenas informar que o frontend está em http://localhost:5173
    @app.get("/")
    async def root():
        return {
            "message": "API Replicas-v2",
            "docs": "http://localhost:8000/docs",
            "frontend_dev": "http://localhost:5173"
        }