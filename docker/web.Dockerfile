FROM node:22-alpine
WORKDIR /workspace/ute-dual-frontend
COPY ute-dual-frontend/package.json ute-dual-frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY ute-dual-frontend/ ./
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--strictPort"]
