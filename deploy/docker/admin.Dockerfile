ARG VITE_API_BASE_URL=http://localhost:8100/api/v1

FROM node:22-alpine AS build

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /app

COPY package.json pnpm-workspace.yaml /app/
COPY apps/admin-console/package.json /app/apps/admin-console/package.json
RUN corepack enable && pnpm install --filter admin-console... --no-frozen-lockfile

COPY apps/admin-console /app/apps/admin-console
RUN corepack enable && pnpm --dir apps/admin-console build

FROM nginx:1.27-alpine

COPY deploy/docker/nginx.admin.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/admin-console/dist /usr/share/nginx/html
