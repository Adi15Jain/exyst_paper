FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Copy application code
COPY . .

# Build
RUN npm run build

# Expose port
EXPOSE 3000

CMD ["npm", "start"]
