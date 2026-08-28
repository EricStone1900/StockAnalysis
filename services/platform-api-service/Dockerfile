FROM node:24-alpine
WORKDIR /workspace
COPY . .
RUN corepack enable && pnpm install --frozen-lockfile
CMD ["pnpm", "--filter", "@stock/platform-api-service", "dev"]
