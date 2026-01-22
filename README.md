[![en](https://img.shields.io/badge/lang-en-blue.svg)](README.md) [![pt-br](https://img.shields.io/badge/lang-pt--br-green.svg)](README.pt-BR.md)

# Data Validation & PostgreSQL Replicas Manager

Automated ETL pipeline for automotive parts data validation + on-demand PostgreSQL replica provisioning. Built with React, TypeScript, FastAPI, DuckDB, and Docker.

---

## What It Does

**Data Validation Module**  
Automates cleaning, normalization, and validation of supplier CSV files (NCM codes, EAN barcodes, weights, dimensions, brand mapping, duplicate detection).

**PostgreSQL Replicas Module**  
Provisions isolated PostgreSQL containers on-demand for each developer via Docker SDK.

**User Management**  
Role-based access control (DEV/ADM) with JWT authentication.

---

## Key Features

### 📊 Data Validation Pipeline (8-Step Workflow)

1. **Upload** → CSV import with drag-and-drop
2. **Column Mapping** → Auto-detect and rename columns
3. **Data Treatment** → Fix uppercase, nulls, NCM, barcodes, weights, dimensions
4. **Brand Normalization** → Map variations to canonical names
5. **Duplicate Removal** → Identify by `search_ref` + brand
6. **Similarity Analysis** → Detect near-duplicates with edit distance
7. **Statistics** → Quality metrics dashboard
8. **Review & Submit** → Send for admin approval

**Admin Actions:**

- Quality report generation
- Approval/rejection workflow
- Granular publish strategies (ignore/replace/concatenate/fill-empty)
- PostgreSQL publication with rollback

### 🐘 PostgreSQL Replicas

- Create isolated PG containers (Docker SDK)
- Dynamic port allocation (5433+)
- SSH tunneling guide
- Bulk deletion (admin)

### 👥 User Management

- JWT authentication (5h expiration)
- Role-based access (DEV/ADM)
- CRUD operations (admin only)

---

## Tech Stack

| Layer         | Technologies                                   |
| ------------- | ---------------------------------------------- |
| **Frontend**  | React 18, TypeScript 5.5, Tailwind CSS, Vite   |
| **Backend**   | FastAPI 0.115, Python 3.11, SQLAlchemy 2.0     |
| **Databases** | DuckDB 1.1 (analytics), PostgreSQL 16 (prod)   |
| **DevOps**    | Docker, Docker Compose, Docker SDK             |
| **Security**  | JWT (python-jose), bcrypt, Pydantic validation |

---

## Quick Start

**Prerequisites:** Docker 24+, Docker Compose 2+

```bash
# Clone and configure
git clone https://github.com/your-repo/replicas-v2.git
cd replicas-v2
cp .env.example .env  # Edit with your credentials

# Start services
docker compose up -d

# Create admin user
docker exec -it replicas-backend python -m backend.scripts.create_admin

# Access
# Frontend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Environment Variables

```bash
# JWT
JWT_SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=300

# Metadata DB
DATABASE_URL=sqlite:///./metadata.db

# Production PostgreSQL
PROD_DB_HOST=your-postgres-host
PROD_DB_PORT=5432
PROD_DB_NAME=production_db
PROD_DB_USER=postgres
PROD_DB_PASSWORD=your-password
```

---

## API Endpoints

### Authentication

- `POST /auth/login` - Login with JWT

### Users (Admin only)

- `GET /users/` - List users
- `POST /users/` - Create user
- `DELETE /users/{username}` - Delete user

### Replicas

- `POST /replicas/create` - Create personal replica
- `GET /replicas/my-replica` - View my replica
- `GET /replicas/list` - List all (admin)
- `DELETE /replicas/user/{user}` - Delete replica

### Data Validation

- `POST /validation/upload` - Upload CSV
- `GET /validation/projects` - List my projects
- `GET /validation/{id}/preview` - Preview data
- `POST /validation/{id}/columns/rename` - Rename column
- `POST /validation/{id}/treatments/fix-*` - Apply fixes
- `POST /validation/{id}/brands/normalize` - Normalize brands
- `POST /validation/{id}/duplicates/remove` - Remove duplicates
- `PUT /validation/{id}/submit` - Submit for approval
- `POST /validation/{id}/publish` - Publish to production (admin)
- `GET /validation/history` - Publication history (admin)

---

## Project Structure

```
replicas-v2/
├── backend/
│   ├── core/                    # Database, models, auth
│   ├── routers/                 # Auth & users endpoints
│   ├── services/
│   │   ├── data_validation/     # ETL pipeline
│   │   └── replicas/            # Docker management
│   ├── main.py                  # FastAPI app
│   └── Dockerfile               # Multi-stage build
├── frontend/
│   ├── src/
│   │   ├── pages/               # Login, dashboards
│   │   │   ├── admin/           # Admin pages
│   │   │   ├── data-validation/ # Dev workspace
│   │   │   └── replicas/        # Replicas dashboard
│   │   ├── services/            # API clients
│   │   └── components/          # Reusable UI
│   └── package.json
└── docker-compose.yml
```

---

## Data Flow

```
CSV Upload → DuckDB → Validations → Admin Review → PostgreSQL Publish
                ↓
            Quality Report
```

---

## Validation Rules

| Rule             | Logic                            |
| ---------------- | -------------------------------- |
| **NCM**          | 8 digits required                |
| **Barcodes**     | EAN-8/13, UPC-12 validation      |
| **Weights**      | gross ≥ net, both > 0            |
| **Dimensions**   | 0 < value < 1000 cm              |
| **Brands**       | Normalize to canonical names     |
| **Duplicates**   | Based on `search_ref` + brand    |
| **Similarities** | Edit distance < 3 (configurable) |

---

## Security

- JWT tokens (5h expiration)
- Bcrypt password hashing (cost 12)
- Role-based access (DEV/ADM)
- CORS configured
- Pydantic input validation
- SQLAlchemy ORM (SQL injection prevention)

---

## Performance

- DuckDB for fast in-memory analytics
- React lazy loading
- Paginated API responses
- Docker multi-stage builds
- Background task processing (Celery-ready)

---

## Deployment

**Docker Compose (Recommended):**

```bash
docker compose up -d
```

**Manual Build:**

```bash
docker build -f backend/Dockerfile -t leonardo-replicas .
docker run -d -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e JWT_SECRET_KEY="your-key" \
  leonardo-replicas
```

---

## Development

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

## Use Cases

### 1. Supplier Data Import

**Problem:** 50,000 rows with inconsistent brands, invalid NCMs, duplicates  
**Solution:** Automated 8-step pipeline reduces processing from 2-3 days to 15 minutes

### 2. Developer Testing

**Problem:** Need isolated PostgreSQL environment  
**Solution:** Create personal replica via UI in 2 minutes, delete when done

### 3. Quality Assurance

**Problem:** Manual data quality checks  
**Solution:** Automated quality reports with metrics and statistics

---

## Metrics

- **LOC:** ~15,000+
- **Endpoints:** 50+
- **React Components:** 30+
- **Pydantic Schemas:** 60+
- **Technologies:** 20+
