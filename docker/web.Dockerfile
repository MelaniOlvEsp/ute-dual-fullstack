FROM node:22-alpine AS build
WORKDIR /workspace/ute-dual-frontend
COPY ute-dual-frontend/package.json ute-dual-frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY ute-dual-frontend/ ./
RUN npm run build

FROM nginx:stable-alpine
COPY docker/web.nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/web-config.sh /docker-entrypoint.d/40-ute-config.sh
RUN chmod +x /docker-entrypoint.d/40-ute-config.sh
COPY --from=build /workspace/ute-dual-frontend/dist /usr/share/nginx/html
ENV VITE_API_URL=http://127.0.0.1:8001
EXPOSE 8080
