FROM node:20-alpine AS builder

ARG VITE_API_URL=http://localhost:8000

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json vite.config.ts index.html ./
COPY src/ src/
RUN VITE_API_URL=$VITE_API_URL npm run build

FROM nginx:alpine

COPY --from=builder /build/dist/ /usr/share/nginx/html/
COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
