FROM oven/bun:1 AS base

WORKDIR /app

# Install dependencies first for better layer caching
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile --production

# Copy application source
COPY src/ src/
COPY tsconfig.json ./

# Create a non-root user for security
RUN groupadd --system --gid 1001 mcp && \
    useradd --system --uid 1001 --gid mcp --no-create-home mcp && \
    mkdir -p /data && \
    chown mcp:mcp /data

USER mcp

EXPOSE 3200

ENV TRANSPORT=http
ENV PORT=3200
ENV NODE_ENV=production

CMD ["bun", "src/index.ts"]
