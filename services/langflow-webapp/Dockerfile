FROM node:18-alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache curl python3 make g++

# Copy package files
COPY services/langflow-webapp/package*.json ./
RUN npm ci --only=production

# Copy application code
COPY services/langflow-webapp/ .

# Build the application
RUN npm run build

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001 && \
    chown -R nextjs:nodejs /app
USER nextjs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

EXPOSE 3000

CMD ["npm", "start"]