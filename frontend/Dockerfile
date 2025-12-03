# Dockerfile para desenvolvimento com Vite
FROM node:20-alpine

WORKDIR /app

# Copiar package.json e package-lock.json
COPY package*.json ./

# Instalar dependências
RUN npm install

# Copiar o resto dos arquivos
COPY . .

# Expor a porta do Vite
EXPOSE 5173

# Comando padrão (será sobrescrito pelo docker-compose)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
