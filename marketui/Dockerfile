FROM node:22-alpine AS base

WORKDIR /app

# --- deps ---
FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci

# --- build ---
FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_DATA_BASE_URL
ENV NEXT_PUBLIC_DATA_BASE_URL=$NEXT_PUBLIC_DATA_BASE_URL
ENV NEXT_OUTPUT=standalone

RUN npm run build

# --- run ---
FROM base AS runner

ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static     ./.next/static

USER nextjs

EXPOSE 3001

ENV PORT=3001
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
