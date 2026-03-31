FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama (install.sh requires systemd; download tarball directly instead)
RUN apt-get update && apt-get install -y --no-install-recommends zstd tar \
    && curl -fsSL https://github.com/ollama/ollama/releases/download/v0.19.0/ollama-linux-arm64.tar.zst \
       -o /tmp/ollama.tar.zst \
    && tar -I zstd -xf /tmp/ollama.tar.zst -C /usr/local \
    && rm /tmp/ollama.tar.zst \
    && apt-get purge -y zstd && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Python deps
WORKDIR /app
COPY scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright + Chromium
RUN playwright install chromium && playwright install-deps chromium

# Copy scraper source
COPY scraper/ .

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
