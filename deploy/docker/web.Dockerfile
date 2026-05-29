ARG NUXT_PUBLIC_API_BASE=http://localhost:8100/api/v1

FROM node:22-alpine AS build

ARG NUXT_PUBLIC_API_BASE
ENV NUXT_PUBLIC_API_BASE=${NUXT_PUBLIC_API_BASE}

WORKDIR /app

COPY package.json pnpm-workspace.yaml /app/
COPY apps/web-portal/package.json /app/apps/web-portal/package.json
RUN corepack enable && pnpm install --filter web-portal... --no-frozen-lockfile

COPY apps/web-portal /app/apps/web-portal
RUN corepack enable && pnpm --dir apps/web-portal build

FROM node:22-alpine

WORKDIR /app
ARG NUXT_PUBLIC_API_BASE
ENV NUXT_PUBLIC_API_BASE=${NUXT_PUBLIC_API_BASE}
COPY --from=build /app/apps/web-portal/.output /app/.output
EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
