import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Variáveis de ambiente
POSTGRES_USER = os.getenv("POSTGRES_USER", "pgroot")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pg@root")
POSTGRES_DB = os.getenv("POSTGRES_DB", "replicas_metadados_db")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# Fazer URL encode da senha para evitar problemas com caracteres especiais
password_encoded = quote_plus(POSTGRES_PASSWORD)

# Construir URL corretamente
SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{password_encoded}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}"

print(f"🔗 Conectando ao banco: {SQLALCHEMY_DATABASE_URL}")  # Debug

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()