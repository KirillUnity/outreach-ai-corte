# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=10s \
  CMD wget -q -O /dev/null http://127.0.0.1:3000/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
