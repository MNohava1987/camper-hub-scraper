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

# Install Chromium runtime deps manually (playwright install-deps uses Ubuntu package
# names which don't exist on Debian trixie, so we install them directly)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libatspi2.0-0 libexpat1 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
    libxrandr2 libgbm1 libdrm2 libxcb1 libxkbcommon0 \
    libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright Chromium browser only (deps already installed above)
RUN playwright install chromium

# Copy scraper source
COPY scraper/ .

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
