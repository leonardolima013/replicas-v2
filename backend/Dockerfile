# ===== ESTÁGIO 1: BUILD DO FRONTEND =====
FROM node:20-alpine AS frontend-builder

# Definir diretório de trabalho
WORKDIR /frontend

# Copiar arquivos de configuração do frontend
COPY frontend/package*.json ./
COPY frontend/vite.config.ts ./
COPY frontend/postcss.config.js ./
COPY frontend/tsconfig*.json ./
COPY frontend/index.html ./

# Instalar dependências
RUN npm install

# Copiar código fonte do frontend
COPY frontend/src ./src

# Build do frontend (gera a pasta /frontend/dist)
RUN npm run build

# ===== ESTÁGIO 2: PRODUÇÃO (BACKEND + FRONTEND) =====
FROM python:3.11.9-slim

# Definir variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do backend
COPY backend ./backend

# Copiar arquivos do frontend buildado do ESTÁGIO 1
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Expor a porta 8000
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]