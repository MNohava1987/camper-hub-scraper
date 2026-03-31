#!/bin/bash
set -e

MODEL="${OLLAMA_MODEL:-llama3.2:1b}"

echo "=== Starting Ollama ==="
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
for i in $(seq 1 30); do
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "Ollama ready."
        break
    fi
    sleep 2
done

# Pull model if not already present
if ! ollama list 2>/dev/null | grep -q "^${MODEL}"; then
    echo "Pulling model ${MODEL} (first run only)..."
    ollama pull "${MODEL}"
else
    echo "Model ${MODEL} already present."
fi

echo "=== Running scraper (schedule=${SCHEDULE:-all}) ==="
cd /app
python main.py "${SCHEDULE:-all}"

echo "=== Stopping Ollama ==="
kill "$OLLAMA_PID" 2>/dev/null || true
wait "$OLLAMA_PID" 2>/dev/null || true
