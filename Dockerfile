FROM ubuntu:24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    pkg-config \
    libcap-dev \
    gcc \
    g++ \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    default-jdk \
    golang-go \
    rustc \
    cargo \
    curl \
    ca-certificates \
    libseccomp-dev \
    libsystemd-dev \
    systemd \
    && rm -rf /var/lib/apt/lists/*

# Install Typescript using npm
RUN npm install -g typescript

# Build & install isolate
RUN git clone https://github.com/ioi/isolate.git --branch v2.2 /tmp/isolate \
    && cd /tmp/isolate \
    && make -j$(nproc) isolate isolate-cg-keeper \
    && cp isolate /usr/local/bin/ \
    && cp isolate-cg-keeper /usr/local/bin/ \
    && rm -rf /tmp/isolate

# Ensure isolate binary is setuid root
RUN chmod 4755 /usr/local/bin/isolate

# Isolate configuration
COPY config/isolate.conf /tmp/isolate.raw
RUN tr -d '\r' < /tmp/isolate.raw > /usr/local/etc/isolate \
    && sed -i 's/ *= */=/g' /usr/local/etc/isolate \
    && rm /tmp/isolate.raw

# ── Kernel tuning for isolate ────────────────────────────────────────────
# These are applied at container runtime via docker-compose privileged mode.
# Swap off + protected_hardlinks are configured in compose / host.

# ── cgroup v2 setup ─────────────────────────────────────────────────────
# Create the cgroup subtree isolate will use.  In a privileged container
# with cgroup v2 mounted, this path is writable by root.
RUN mkdir -p /sys/fs/cgroup/system.slice/isolate.scope 2>/dev/null || true


FROM base AS app

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY . .
RUN uv sync --frozen --no-dev

COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
