FROM node:22-alpine AS build

WORKDIR /app

COPY package.json pnpm-workspace.yaml /app/
COPY apps/admin-console/package.json /app/apps/admin-console/package.json
RUN corepack enable && pnpm install --filter admin-console... --no-frozen-lockfile

COPY apps/admin-console /app/apps/admin-console
RUN corepack enable && pnpm --dir apps/admin-console build

FROM nginx:1.27-alpine

COPY deploy/docker/nginx.admin.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/admin-console/dist /usr/share/nginx/html
