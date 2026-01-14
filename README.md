# Replicas-v2

Sistema moderno de gerenciamento de réplicas de banco de dados PostgreSQL com interface web completa.

## 🎯 Funcionalidades

### Para Administradores (ADM)

- ✅ Criar novos usuários (DEV ou ADM)
- ✅ Visualizar todas as réplicas ativas
- ✅ Deletar réplicas individuais ou todas de uma vez
- ✅ Listar todos os usuários do sistema

### Para Desenvolvedores (DEV)

- ✅ Criar sua própria réplica de banco de dados
- ✅ Visualizar detalhes de conexão
- ✅ Guia passo a passo de como conectar ao banco
- ✅ Deletar sua réplica quando não for mais necessária

## 🚀 Stack Tecnológica

### Backend

- **FastAPI** (Python 3.11)
- **SQLAlchemy** (ORM)
- **PostgreSQL** (Banco de metadados)
- **Docker SDK** (Gerenciamento de containers)
- **JWT** (Autenticação)

### Frontend

- **Vue.js 3** (Composition API + `<script setup>`)
- **Vue Router** (SPA Routing)
- **Tailwind CSS** (Estilização)
- **Axios** (HTTP Client)
- **Vite** (Build Tool)

## 📦 Como Rodar (Single Container)

### Pré-requisitos

- Docker
- Docker Compose (opcional)

### Opção 1: Docker Build Manual

```bash
# 1. Build da imagem (multi-stage: frontend + backend)
docker build -f backend/Dockerfile -t replicas-v2 .

# 2. Rodar o container
docker run -d \
  --name replicas-v2 \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e JWT_SECRET_KEY="sua-chave-secreta-super-segura" \
  -e ALGORITHM="HS256" \
  -e ACCESS_TOKEN_EXPIRE_MINUTES="300" \
  -e DATABASE_URL="sqlite:///./metadata.db" \
  replicas-v2
```

### Opção 2: Docker Compose (Recomendado)

```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar serviços
docker-compose down
```

### Acessar a Aplicação

Abra seu navegador em: **http://localhost:8000**

## 👤 Usuários Padrão

Ao iniciar pela primeira vez, crie um usuário ADM via API:

python3 -m backend.scripts.create_admin

```bash
curl -X 'POST' \
  'http://localhost:8000/users/' \
  -H 'Content-Type: application/json' \
  -d '{
  "usuario": "admin",
  "password": "admin123",
  "role": "adm"
}'
```

Depois faça login em: http://localhost:8000/login

## 🏗️ Estrutura do Projeto

```
replicas-v2/
├── backend/
│   ├── core/
│   │   ├── database.py      # Configuração do banco
│   │   ├── models.py        # Modelos SQLAlchemy
│   │   ├── schemas.py       # Schemas Pydantic
│   │   ├── security.py      # JWT e Autenticação
│   │   └── deps.py          # Dependencies
│   ├── routers/
│   │   ├── auth.py          # Login
│   │   └── users.py         # Gerenciamento de usuários
│   ├── services/
│   │   └── replicas/
│   │       ├── manager.py   # Lógica Docker
│   │       ├── router.py    # Endpoints de réplicas
│   │       └── schemas.py   # Schemas de réplicas
│   ├── main.py              # App FastAPI + Serve Frontend
│   └── Dockerfile           # Multi-stage Build
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Login.vue
│   │   │   └── Dashboard.vue
│   │   ├── services/
│   │   │   └── api.js       # Axios client
│   │   ├── router/
│   │   │   └── index.js     # Vue Router
│   │   ├── App.vue
│   │   ├── main.js
│   │   └── style.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── docker-compose.yml
└── requirements.txt
```

## 🔧 Desenvolvimento Local

### Backend (Apenas)

```bash
cd backend
pip install -r ../requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Apenas)

```bash
cd frontend
npm install
npm run dev
# Acesse em http://localhost:5173
```

## 🎨 Design System

- **Paleta de Cores:**
  - Primária: Azul Navy (#1e3a8a)
  - Background: Branco/Cinza Claro (#F3F4F6)
  - Destaque: Azul (#3b82f6)
- **Tipografia:** Sistema de fontes nativas
- **Componentes:** Sombras suaves, bordas arredondadas
- **Responsividade:** Mobile-first

## 📝 Endpoints da API

### Autenticação

- `POST /auth/login` - Login (retorna JWT)

### Usuários (ADM only)

- `POST /users/` - Criar usuário
- `GET /users/` - Listar usuários

### Réplicas

- `POST /replicas/create` - Criar réplica
- `GET /replicas/my-replica` - Ver minha réplica
- `GET /replicas/list` - Listar todas (ADM)
- `GET /replicas/user/{username}` - Ver réplica de um usuário
- `DELETE /replicas/user/{username}` - Deletar réplica
- `DELETE /replicas/delete-all` - Deletar todas (ADM)

## 🛡️ Segurança

- ✅ Autenticação JWT
- ✅ Proteção de rotas por Role (ADM/DEV)
- ✅ Senhas hasheadas com bcrypt
- ✅ Tokens com expiração configurável
- ✅ CORS configurado
- ✅ Validação de entrada com Pydantic
