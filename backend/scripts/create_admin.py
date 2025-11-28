#!/usr/bin/env python3
"""
Script para criar usuário administrador padrão.
Execute: python -m backend.scripts.create_admin
"""
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.database import SessionLocal
from backend.core import models, security

def create_admin_user(username: str = "admin", password: str = "admin123"):
    """Cria um usuário administrador se não existir."""
    db = SessionLocal()
    
    try:
        # Verificar se já existe
        existing = db.query(models.User).filter(models.User.usuario == username).first()
        
        if existing:
            print(f"❌ Usuário '{username}' já existe!")
            return False
        
        # Criar admin
        hashed_password = security.get_password_hash(password)
        admin = models.User(
            usuario=username,
            hashed_password=hashed_password,
            role="adm"
        )
        
        db.add(admin)
        db.commit()
        
        print(f"✅ Usuário administrador criado com sucesso!")
        print(f"   Usuário: {username}")
        print(f"   Senha: {password}")
        print(f"   Role: adm")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar usuário: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Criar usuário administrador')
    parser.add_argument('--username', default='admin', help='Nome do usuário (padrão: admin)')
    parser.add_argument('--password', default='admin123', help='Senha do usuário (padrão: admin123)')
    
    args = parser.parse_args()
    
    create_admin_user(args.username, args.password)
