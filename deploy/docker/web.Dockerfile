FROM node:22-alpine AS build

WORKDIR /app

COPY package.json pnpm-workspace.yaml /app/
COPY apps/web-portal/package.json /app/apps/web-portal/package.json
RUN corepack enable && pnpm install --filter web-portal... --no-frozen-lockfile

COPY apps/web-portal /app/apps/web-portal
RUN corepack enable && pnpm --dir apps/web-portal build

FROM node:22-alpine

WORKDIR /app
COPY --from=build /app/apps/web-portal/.output /app/.output
EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
