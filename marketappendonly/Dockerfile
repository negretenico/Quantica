# Build stage
FROM golang:1.24 AS builder

WORKDIR /app

# Cache dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .

# Build binary
RUN go build -o main ./cmd/server

# Runtime stage
FROM debian:bullseye-slim

# Install CA certs (needed if your code makes HTTPS calls)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root/

# Copy built binary
COPY --from=builder /app/main .

# Run the binary
CMD ["./main"]
