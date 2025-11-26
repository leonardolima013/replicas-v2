# 1. Usar uma imagem Python leve e moderna
FROM python:3.11-slim

# 2. Definir variáveis de ambiente para evitar arquivos .pyc e logs presos
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Definir diretório de trabalho dentro do container
WORKDIR /app

# 4. Instalar dependências do sistema necessárias para compilar pacotes (se necessário)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 5. Copiar e instalar dependências Python (Cache Layering)
# Copiamos primeiro só o requirements para o Docker usar cache se não houver mudanças
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copiar o restante do código
COPY . .

# 7. Expor a porta 8000
EXPOSE 8000

# 8. Comando para rodar a aplicação
# Note que usamos --host 0.0.0.0 para aceitar conexões externas ao container
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]