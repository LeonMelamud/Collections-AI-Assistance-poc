# Backend Dockerfile for Node.js/Express API
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Install curl for health checks
RUN apk add --no-cache curl

# Expose port
EXPOSE 8000

# Start the application
CMD ["npm", "start"]