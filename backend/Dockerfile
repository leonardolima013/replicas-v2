# ===== ESTÁGIO 1: BUILD DO FRONTEND =====
FROM node:20-alpine AS frontend-builder

# Definir diretório de trabalho
WORKDIR /frontend

# Copiar package.json e package-lock.json
COPY frontend/package*.json ./

# Copiar arquivos de configuração necessários para o build
COPY frontend/vite.config.ts ./
COPY frontend/postcss.config.js ./
COPY frontend/tsconfig*.json ./
COPY frontend/index.html ./

# Instalar dependências
RUN npm install

# Copiar código-fonte
COPY frontend/src ./src

# Build da aplicação
RUN npm run build

# ===== ESTÁGIO 2: IMAGEM FINAL =====
FROM python:3.11.9-slim

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do backend
COPY backend ./backend

# Copiar arquivo de mapeamento de marcas
COPY mapeamento-marcas-invertido.json ./

# Copiar o frontend buildado do estágio anterior
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Expor porta
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
