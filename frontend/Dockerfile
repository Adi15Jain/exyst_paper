FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Default command (overridden in docker-compose for dev)
CMD ["npm", "run", "dev"]
