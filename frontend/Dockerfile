FROM node:20-alpine AS builder
WORKDIR /app

# Install deps and build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/dist ./dist
WORKDIR /app
ENV NODE_ENV=production
EXPOSE 4173
# Use `npm run preview` to serve the built site in a simple way
COPY frontend/package*.json ./
RUN npm ci --omit=dev
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]
