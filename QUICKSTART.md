# 🚀 Guia Rápido - Nova Máquina

Setup simplificado para rodar em qualquer máquina.

## ⚡ Setup Rápido (5 minutos)

```bash
# 1. Clonar
git clone <repo-url>
cd replicas-v2

# 2. Configurar
cp .env.example .env
# Edite .env com suas credenciais (PROD_DB_*, AWS_*)

# 3. Criar diretórios
mkdir -p temp_data data

# 4. Iniciar
docker compose up -d

# 5. Criar admin
docker exec -it replicas-v2_app python -m backend.scripts.create_admin

# 6. Acessar
# Frontend: http://localhost:5173
# API: http://localhost:8000/docs
```

## ✅ Verificação

```bash
# Ver status
docker compose ps

# Ver logs
docker compose logs -f app

# Testar API
curl http://localhost:8000/
```

## 🔧 Variáveis Mínimas Necessárias (.env)

```bash
# Banco de Produção (obrigatório)
PROD_DB_HOST=host.docker.internal
PROD_DB_PORT=5432
PROD_DB_NAME=hubbi_prod
PROD_DB_USER=postgres
PROD_DB_PASSWORD=SUA_SENHA

# AWS (obrigatório para upload de imagens)
AWS_ACCESS_KEY_ID=SUA_KEY
AWS_SECRET_ACCESS_KEY=SEU_SECRET
AWS_BUCKET_NAME=seu-bucket

# JWT (gerar nova chave)
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

## 🐛 Problemas Comuns

### Porta em uso

```bash
# Alterar no .env
APP_PORT=8001
FRONTEND_PORT=5174

docker compose down
docker compose up -d
```

### Não conecta ao banco

```bash
# Linux: usar IP do host Docker
PROD_DB_HOST=172.17.0.1

# Windows/Mac: usar host.docker.internal (já é o padrão)
PROD_DB_HOST=host.docker.internal
```

### AWS credentials inválidas

```bash
# Verificar
docker exec -it replicas-v2_app env | grep AWS
```

## 📖 Documentação Completa

Ver [SETUP.md](SETUP.md) para guia detalhado.

---

**Diferenças entre máquinas:**

- ✅ **NENHUMA** - A aplicação está 100% containerizada
- ✅ Apenas configure `.env` com suas credenciais
- ✅ Funciona em Linux, Windows e Mac sem mudanças
