# Frontend: build with Vite, serve with nginx. The nginx config proxies /api/ to the API.
# Build from apps/web: docker build -t periodic-3d-web apps/web
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Live mode: the site asks the API at /api/v1 (same origin, proxied by nginx).
ARG VITE_DATA_MODE=api
ARG VITE_API_URL=/api/v1
ARG VITE_BASE=/
ENV VITE_DATA_MODE=$VITE_DATA_MODE VITE_API_URL=$VITE_API_URL VITE_BASE=$VITE_BASE
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -qO- http://127.0.0.1/ > /dev/null || exit 1
