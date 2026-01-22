[![en](https://img.shields.io/badge/lang-en-blue.svg)](README.md) [![pt-br](https://img.shields.io/badge/lang-pt--br-green.svg)](README.pt-BR.md)

# Sistema de Validação de Dados e Gerenciamento de Réplicas PostgreSQL

Pipeline ETL automatizado para validação de dados de peças automotivas + provisionamento de réplicas PostgreSQL sob demanda. Construído com React, TypeScript, FastAPI, DuckDB e Docker.

---

## O Que Faz

**Módulo de Validação de Dados**  
Automatiza limpeza, normalização e validação de arquivos CSV de fornecedores (códigos NCM, códigos de barras EAN, pesos, dimensões, mapeamento de marcas, detecção de duplicatas).

**Módulo de Réplicas PostgreSQL**  
Provisiona containers PostgreSQL isolados sob demanda para cada desenvolvedor via Docker SDK.

**Gerenciamento de Usuários**  
Controle de acesso baseado em função (DEV/ADM) com autenticação JWT.

---

## Funcionalidades Principais

### 📊 Pipeline de Validação de Dados (Fluxo em 8 Etapas)

1. **Upload** → Importação de CSV com drag-and-drop
2. **Mapeamento de Colunas** → Detecção automática e renomeação de colunas
3. **Tratamento de Dados** → Correção de maiúsculas, nulos, NCM, códigos de barras, pesos, dimensões
4. **Normalização de Marcas** → Mapeamento de variações para nomes canônicos
5. **Remoção de Duplicatas** → Identificação por `search_ref` + marca
6. **Análise de Similaridade** → Detecção de quase-duplicatas com distância de edição
7. **Estatísticas** → Dashboard de métricas de qualidade
8. **Revisão e Envio** → Envio para aprovação do administrador

**Ações do Administrador:**

- Geração de relatórios de qualidade
- Fluxo de aprovação/rejeição
- Estratégias de publicação granulares (ignorar/substituir/concatenar/preencher-vazio)
- Publicação no PostgreSQL com rollback

### 🐘 Réplicas PostgreSQL

- Criação de containers PG isolados (Docker SDK)
- Alocação dinâmica de portas (5433+)
- Guia de túnel SSH
- Exclusão em massa (admin)

### 👥 Gerenciamento de Usuários

- Autenticação JWT (expiração de 5h)
- Acesso baseado em função (DEV/ADM)
- Operações CRUD (somente admin)

---

## Stack Tecnológica

| Camada        | Tecnologias                                   |
| ------------- | --------------------------------------------- |
| **Frontend**  | React 18, TypeScript 5.5, Tailwind CSS, Vite  |
| **Backend**   | FastAPI 0.115, Python 3.11, SQLAlchemy 2.0    |
| **Databases** | DuckDB 1.1 (analytics), PostgreSQL 16 (prod)  |
| **DevOps**    | Docker, Docker Compose, Docker SDK            |
| **Segurança** | JWT (python-jose), bcrypt, validação Pydantic |

---

## Início Rápido

**Pré-requisitos:** Docker 24+, Docker Compose 2+

```bash
# Clonar e configurar
git clone https://github.com/your-repo/replicas-v2.git
cd replicas-v2
cp .env.example .env  # Edite com suas credenciais

# Iniciar serviços
docker compose up -d

# Criar usuário admin
docker exec -it replicas-backend python -m backend.scripts.create_admin

# Acessar
# Frontend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Variáveis de Ambiente

```bash
# JWT
JWT_SECRET_KEY=sua-chave-secreta-aqui
ACCESS_TOKEN_EXPIRE_MINUTES=300

# Banco de Metadados
DATABASE_URL=sqlite:///./metadata.db

# PostgreSQL de Produção
PROD_DB_HOST=seu-host-postgres
PROD_DB_PORT=5432
PROD_DB_NAME=production_db
PROD_DB_USER=postgres
PROD_DB_PASSWORD=sua-senha
```

---

## Endpoints da API

### Autenticação

- `POST /auth/login` - Login com JWT

### Usuários (Somente admin)

- `GET /users/` - Listar usuários
- `POST /users/` - Criar usuário
- `DELETE /users/{username}` - Deletar usuário

### Réplicas

- `POST /replicas/create` - Criar réplica pessoal
- `GET /replicas/my-replica` - Ver minha réplica
- `GET /replicas/list` - Listar todas (admin)
- `DELETE /replicas/user/{user}` - Deletar réplica

### Validação de Dados

- `POST /validation/upload` - Upload de CSV
- `GET /validation/projects` - Listar meus projetos
- `GET /validation/{id}/preview` - Visualizar dados
- `POST /validation/{id}/columns/rename` - Renomear coluna
- `POST /validation/{id}/treatments/fix-*` - Aplicar correções
- `POST /validation/{id}/brands/normalize` - Normalizar marcas
- `POST /validation/{id}/duplicates/remove` - Remover duplicatas
- `PUT /validation/{id}/submit` - Enviar para aprovação
- `POST /validation/{id}/publish` - Publicar em produção (admin)
- `GET /validation/history` - Histórico de publicações (admin)

---

## Estrutura do Projeto

```
replicas-v2/
├── backend/
│   ├── core/                    # Database, models, auth
│   ├── routers/                 # Endpoints de auth & users
│   ├── services/
│   │   ├── data_validation/     # Pipeline ETL
│   │   └── replicas/            # Gerenciamento Docker
│   ├── main.py                  # App FastAPI
│   └── Dockerfile               # Build multi-stage
├── frontend/
│   ├── src/
│   │   ├── pages/               # Login, dashboards
│   │   │   ├── admin/           # Páginas admin
│   │   │   ├── data-validation/ # Workspace dev
│   │   │   └── replicas/        # Dashboard de réplicas
│   │   ├── services/            # Clientes API
│   │   └── components/          # UI reutilizável
│   └── package.json
└── docker-compose.yml
```

---

## Fluxo de Dados

```
Upload CSV → DuckDB → Validações → Revisão Admin → Publicação PostgreSQL
                ↓
        Relatório de Qualidade
```

---

## Regras de Validação

| Regra              | Lógica                            |
| ------------------ | --------------------------------- |
| **NCM**            | 8 dígitos obrigatórios            |
| **Códigos Barras** | Validação EAN-8/13, UPC-12        |
| **Pesos**          | bruto ≥ líquido, ambos > 0        |
| **Dimensões**      | 0 < valor < 1000 cm               |
| **Marcas**         | Normalizar para nomes canônicos   |
| **Duplicatas**     | Baseado em `search_ref` + marca   |
| **Similaridades**  | Distância de edição < 3 (config.) |

---

## Segurança

- Tokens JWT (expiração de 5h)
- Hash de senha com Bcrypt (cost 12)
- Acesso baseado em função (DEV/ADM)
- CORS configurado
- Validação de entrada com Pydantic
- SQLAlchemy ORM (prevenção de SQL injection)

---

## Performance

- DuckDB para analytics rápidos em memória
- Lazy loading no React
- Respostas da API paginadas
- Builds multi-stage no Docker
- Processamento de tarefas em background (Celery-ready)

---

## Deploy

**Docker Compose (Recomendado):**

```bash
docker compose up -d
```

**Build Manual:**

```bash
docker build -f backend/Dockerfile -t leonardo-replicas .
docker run -d -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e JWT_SECRET_KEY="sua-chave" \
  leonardo-replicas
```

---

## Desenvolvimento

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
uvicorn backend.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev  # http://localhost:5173
```

---

## Casos de Uso

### 1. Importação de Dados de Fornecedor

**Problema:** 50.000 linhas com marcas inconsistentes, NCMs inválidos, duplicatas  
**Solução:** Pipeline automatizado em 8 etapas reduz processamento de 2-3 dias para 15 minutos

### 2. Testes de Desenvolvedor

**Problema:** Necessidade de ambiente PostgreSQL isolado  
**Solução:** Criar réplica pessoal via UI em 2 minutos, deletar quando concluído

### 3. Garantia de Qualidade

**Problema:** Verificações manuais de qualidade de dados  
**Solução:** Relatórios de qualidade automatizados com métricas e estatísticas

---

## Métricas

- **LOC:** ~15.000+
- **Endpoints:** 50+
- **Componentes React:** 30+
- **Schemas Pydantic:** 60+
