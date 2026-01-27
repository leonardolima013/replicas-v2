# 🚀 Guia de Setup - Replicas V2

Este guia detalha como configurar e executar a aplicação **Replicas V2** em qualquer máquina, garantindo portabilidade completa.

---

## 📋 Pré-requisitos

### Obrigatórios

- **Docker Desktop** 24.0+ ou **Docker Engine** + **Docker Compose** 2.0+
  - Windows/Mac: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  - Linux: `sudo apt install docker.io docker-compose-v2`
- **Git** para clonar o repositório

### Verificar Instalação

```bash
docker --version          # Docker version 24.0+
docker compose version    # Docker Compose version 2.0+
git --version            # git version 2.x
```

---

## 🔧 Setup Inicial

### 1. Clonar o Repositório

```bash
git clone <url-do-repositorio>
cd replicas-v2
```

### 2. Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar com suas configurações
nano .env  # ou vim, code, etc.
```

**Configurações OBRIGATÓRIAS no `.env`:**

```bash
# ⚠️ Banco de Produção (onde os dados validados serão publicados)
PROD_DB_HOST=host.docker.internal  # Para banco na máquina host
PROD_DB_PORT=5432
PROD_DB_NAME=hubbi_prod
PROD_DB_USER=postgres
PROD_DB_PASSWORD=sua_senha_aqui

# ⚠️ AWS S3 (para upload de imagens)
AWS_ACCESS_KEY_ID=sua_access_key
AWS_SECRET_ACCESS_KEY=sua_secret_key
AWS_BUCKET_NAME=seu-bucket
AWS_REGION=us-east-1

# ⚠️ JWT (Mude em produção!)
JWT_SECRET_KEY=$(openssl rand -hex 32)  # Gerar chave segura
```

### 3. Criar Diretórios Necessários

```bash
# Criar pastas para dados temporários e arquivos de entrada
mkdir -p temp_data data

# Copiar arquivos Excel para importação (se aplicável)
cp seu_arquivo.xlsx data/input.xlsx
```

### 4. Iniciar os Serviços

```bash
# Build e start de todos os containers
docker compose up -d

# Acompanhar logs
docker compose logs -f app
```

**Tempo estimado:** 2-5 minutos (dependendo da internet para download das imagens)

### 5. Verificar Status dos Serviços

```bash
# Listar containers em execução
docker compose ps

# Deve mostrar 5 containers:
# - replicas_metadados_db (PostgreSQL)
# - replicas-v2_redis (Redis)
# - replicas-v2_app (FastAPI)
# - replicas-v2_celery (Celery Worker)
# - replicas-v2_frontend (Vite/React)
```

### 6. Criar Usuário Admin

```bash
# Executar script de criação de admin
docker exec -it replicas-v2_app python -m backend.scripts.create_admin

# Seguir instruções interativas:
# - Usuário: admin (ou seu nome)
# - Senha: (digite uma senha forte)
# - Tipo: adm
```

---

## 🌐 Acessar a Aplicação

Após a inicialização completa:

- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs
- **API Redoc:** http://localhost:8000/redoc

**Login Padrão:**

- Usuário: `admin` (ou o que você criou)
- Senha: (a que você definiu)

---

## 🔍 Troubleshooting

### Erro: "Cannot connect to Docker daemon"

```bash
# Linux: adicionar usuário ao grupo docker
sudo usermod -aG docker $USER
newgrp docker

# Windows/Mac: Verificar se Docker Desktop está rodando
```

### Erro: "Port already in use"

```bash
# Encontrar processo usando a porta
sudo lsof -i :8000  # ou :5173, :5434, :6380

# Alterar portas no .env
APP_PORT=8001
FRONTEND_PORT=5174
METADADOS_DB_PORT=5435
REDIS_PORT=6381

# Recriar containers
docker compose down
docker compose up -d
```

### Erro: "Network replicas-network not found"

```bash
# Recriar network
docker network create replicas-network

# Ou reiniciar compose
docker compose down
docker compose up -d
```

### Erro: "Cannot connect to production database"

```bash
# Verificar se o banco de produção está acessível
docker exec -it replicas-v2_app psql -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB_NAME

# Se falhar, verificar:
# 1. Firewall permitindo conexões
# 2. PostgreSQL configurado para aceitar conexões remotas (postgresql.conf, pg_hba.conf)
# 3. host.docker.internal funciona apenas em Docker Desktop (Windows/Mac)
#    No Linux, use o IP da máquina host ou 172.17.0.1
```

### Erro: "AWS S3 credentials invalid"

```bash
# Verificar credenciais
docker exec -it replicas-v2_app python -c "import boto3; print(boto3.client('s3').list_buckets())"

# Se falhar, verificar AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY no .env
```

### Ver Logs de Erros

```bash
# Logs do app
docker compose logs app

# Logs do celery
docker compose logs celery_worker

# Logs do banco de metadados
docker compose logs db_metadados

# Seguir logs em tempo real
docker compose logs -f app celery_worker
```

---

## 🔄 Comandos Úteis

### Parar Aplicação

```bash
docker compose down
```

### Parar e Remover Volumes (⚠️ APAGA DADOS)

```bash
docker compose down -v
```

### Rebuild após Mudanças no Código

```bash
# Rebuild apenas se mudou código Python/Node
docker compose up -d --build
```

### Limpar Dados Temporários

```bash
rm -rf temp_data/*.duckdb
```

### Backup do Banco de Metadados

```bash
docker exec replicas_metadados_db pg_dump -U pgroot replicas_metadados_db > backup.sql
```

### Restaurar Backup

```bash
cat backup.sql | docker exec -i replicas_metadados_db psql -U pgroot replicas_metadados_db
```

### Acessar Shell do Container

```bash
# App
docker exec -it replicas-v2_app bash

# Banco de metadados
docker exec -it replicas_metadados_db psql -U pgroot -d replicas_metadados_db
```

---

## 📊 Estrutura de Diretórios

```
replicas-v2/
├── backend/              # Código Python (FastAPI)
│   ├── core/            # Models, database, auth
│   ├── routers/         # Endpoints de autenticação e usuários
│   ├── services/        # Lógica de negócio
│   │   ├── data_validation/  # Módulo de validação de dados
│   │   └── replicas/         # Módulo de réplicas PostgreSQL
│   └── scripts/         # Scripts utilitários
├── frontend/            # Código React (TypeScript)
│   └── src/
│       ├── components/  # Componentes reutilizáveis
│       ├── pages/       # Páginas da aplicação
│       └── services/    # Clientes API
├── data/                # ⚠️ Arquivos para importação (.xlsx)
├── temp_data/           # ⚠️ Bancos DuckDB temporários
├── docker-compose.yml   # Orquestração de containers
├── .env                 # ⚠️ Configurações (NÃO VERSIONAR)
├── .env.example         # Template de configurações
└── SETUP.md            # Este arquivo
```

**⚠️ Diretórios que NÃO devem ser versionados:**

- `temp_data/` - Bancos temporários
- `data/` - Arquivos Excel de entrada
- `.env` - Credenciais e configurações locais
- `venv/` - Ambiente virtual Python

---

## 🐳 Configuração para Ambientes Específicos

### Linux (Docker Engine)

Usar diretamente como está. Sem alterações necessárias.

### Windows/Mac (Docker Desktop)

- `host.docker.internal` já funciona nativamente
- Para acessar banco na máquina host, use: `PROD_DB_HOST=host.docker.internal`

### Linux (sem host.docker.internal)

Para acessar banco na máquina host:

```bash
# Descobrir IP do host no Docker
ip addr show docker0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1

# Usar no .env (normalmente é 172.17.0.1)
PROD_DB_HOST=172.17.0.1
```

### Produção (Cloud)

```bash
# Use IP público ou DNS do banco de produção
PROD_DB_HOST=10.0.1.50  # IP privado ou público
PROD_DB_PORT=5432

# Ou hostname
PROD_DB_HOST=postgres.prod.meudominio.com
```

---

## 🛡️ Segurança

### Produção

1. **Nunca** use as senhas padrão
2. Gere JWT_SECRET_KEY forte: `openssl rand -hex 32`
3. Configure firewall para limitar acesso às portas
4. Use SSL/TLS para conexões com banco de produção
5. Rotacione credenciais AWS periodicamente

### Desenvolvimento

1. Mantenha `.env` fora do Git (já está no `.gitignore`)
2. Use senhas diferentes para cada ambiente
3. Não exponha portas desnecessárias publicamente

---

## 📞 Suporte

Se encontrar problemas:

1. Verifique os logs: `docker compose logs -f`
2. Confirme que todas as variáveis do `.env` estão preenchidas
3. Teste conectividade com banco de produção
4. Verifique firewall e regras de rede
5. Confirme que as portas não estão em uso

---

## ✅ Checklist de Verificação

- [ ] Docker e Docker Compose instalados
- [ ] `.env` criado e configurado
- [ ] Diretórios `data/` e `temp_data/` criados
- [ ] Banco de produção acessível
- [ ] Credenciais AWS configuradas
- [ ] Containers iniciados: `docker compose ps`
- [ ] Usuário admin criado
- [ ] Frontend acessível em http://localhost:5173
- [ ] API docs acessível em http://localhost:8000/docs

---

**Última atualização:** Janeiro 2026  
**Versão:** 2.0
