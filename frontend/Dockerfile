# syntax=docker/dockerfile:1

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Demo credentials on the login page are opt-in per build (docker-compose passes true).
ARG VITE_DEMO_MODE=false
ENV VITE_DEMO_MODE=$VITE_DEMO_MODE
RUN npm run build

FROM nginx:1.27-alpine AS runtime
# Both servers ship in the image; select-config.sh links one in at start (TLS unless NGINX_TLS=false).
COPY nginx/http.conf nginx/https.conf /etc/nginx/servers/
COPY nginx/app.conf nginx/security-headers.conf /etc/nginx/snippets/
COPY --chmod=755 nginx/select-config.sh /docker-entrypoint.d/40-select-config.sh
COPY --from=build /app/dist /usr/share/nginx/html
ENV NGINX_TLS=true
EXPOSE 80 443
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/healthz >/dev/null || exit 1
