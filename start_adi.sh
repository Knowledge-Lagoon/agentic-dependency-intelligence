#!/usr/bin/env bash

set -u

PROJECT_DIR="$HOME/agentic-dependency-intelligence"
LLAMA_DIR="$HOME/llama.cpp"

JULIA_MODEL="$HOME/models/Julia-1-Q8_0.gguf"

SMOLVLM_MODEL="$HOME/models/smolvlm2-2.2b/SmolVLM2-2.2B-Instruct-Q4_K_M.gguf"
SMOLVLM_MMPROJ="$HOME/models/smolvlm2-2.2b/SmolVLM2-2.2B-Instruct-mmproj-f16.gguf"

JULIA_PORT=8080
SMOLVLM_PORT=8081

echo "=============================================="
echo " Agentic Dependency Intelligence - Startup"
echo "=============================================="
echo


# ---------------------------------------------------------
# 1. Start Neo4j
# ---------------------------------------------------------

echo "[1/6] Starting Neo4j..."

if podman ps --format '{{.Names}}' | grep -qx "neo4j-adi"; then
    echo "Neo4j container is already running."
else
    podman start neo4j-adi

    if [ $? -ne 0 ]; then
        echo "ERROR: Could not start neo4j-adi."
        exit 1
    fi
fi

echo


# ---------------------------------------------------------
# 2. Wait for Neo4j
# ---------------------------------------------------------

echo "[2/6] Waiting for Neo4j..."

for i in $(seq 1 30); do
    if curl -s --connect-timeout 2 http://127.0.0.1:7474 >/dev/null 2>&1; then
        echo "Neo4j is responding."
        break
    fi

    if [ "$i" -eq 30 ]; then
        echo "ERROR: Neo4j did not become ready."
        exit 1
    fi

    sleep 2
done

echo


# ---------------------------------------------------------
# 3. Start Julia-1 llama-server on 8080
# ---------------------------------------------------------

echo "[3/6] Checking Julia-1 service on port 8080..."

if curl -s --connect-timeout 2 \
    http://127.0.0.1:${JULIA_PORT}/health >/dev/null 2>&1; then

    echo "Julia-1 is already running."

else

    echo "Starting Julia-1..."

    nohup "$LLAMA_DIR/build/bin/llama-server" \
        -m "$JULIA_MODEL" \
        --host 127.0.0.1 \
        --port "$JULIA_PORT" \
        > "$HOME/julia-llama.log" 2>&1 &

    echo $! > "$HOME/julia-llama.pid"

fi

echo


# ---------------------------------------------------------
# 4. Start SmolVLM2 llama-server on 8081
# ---------------------------------------------------------

echo "[4/6] Checking SmolVLM2 service on port 8081..."

if curl -s --connect-timeout 2 \
    http://127.0.0.1:${SMOLVLM_PORT}/health >/dev/null 2>&1; then

    echo "SmolVLM2 is already running."

else

    echo "Starting SmolVLM2..."

    nohup "$LLAMA_DIR/build/bin/llama-server" \
        -m "$SMOLVLM_MODEL" \
        --mmproj "$SMOLVLM_MMPROJ" \
        --host 127.0.0.1 \
        --port "$SMOLVLM_PORT" \
        > "$HOME/smolvlm-llama.log" 2>&1 &

    echo $! > "$HOME/smolvlm-llama.pid"

fi

echo


# ---------------------------------------------------------
# 5. Wait for both AI services
# ---------------------------------------------------------

echo "[5/6] Waiting for AI services..."

wait_for_service() {

    NAME="$1"
    PORT="$2"

    for i in $(seq 1 60); do

        if curl -s --connect-timeout 2 \
            "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then

            echo "$NAME is READY on port $PORT"
            return 0
        fi

        sleep 2
    done

    echo "ERROR: $NAME failed to start on port $PORT."
    return 1
}


wait_for_service "Julia-1" "$JULIA_PORT" || {
    echo "Check: $HOME/julia-llama.log"
    exit 1
}

wait_for_service "SmolVLM2" "$SMOLVLM_PORT" || {
    echo "Check: $HOME/smolvlm-llama.log"
    exit 1
}

echo


# ---------------------------------------------------------
# 6. Configure ADI environment
# ---------------------------------------------------------

echo "[6/6] Configuring ADI..."

cd "$PROJECT_DIR" || exit 1

if [ ! -f ".venv/bin/activate" ]; then
    echo "ERROR: ADI virtual environment not found."
    exit 1
fi

source .venv/bin/activate

export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"

if [ -z "${NEO4J_PASSWORD:-}" ]; then

    echo
    echo "WARNING: NEO4J_PASSWORD is not set."
    echo
    echo "Set it before running analysis:"
    echo
    echo 'export NEO4J_PASSWORD="your-password"'

fi


# ---------------------------------------------------------
# Health summary
# ---------------------------------------------------------

echo
echo "=============================================="
echo " ADI SERVICE STATUS"
echo "=============================================="

echo
echo "Neo4j:"
podman ps --filter name=neo4j-adi \
    --format '  {{.Names}} - {{.Status}}'

echo

if curl -s http://127.0.0.1:8080/health >/dev/null 2>&1; then
    echo "Julia-1       : READY (8080)"
else
    echo "Julia-1       : NOT READY"
fi

if curl -s http://127.0.0.1:8081/health >/dev/null 2>&1; then
    echo "SmolVLM2      : READY (8081)"
else
    echo "SmolVLM2      : NOT READY"
fi

echo
echo "Neo4j URI     : $NEO4J_URI"
echo "Python        : $(which python)"

echo
echo "=============================================="
echo " ADI startup complete"
echo "=============================================="
echo
echo 'Run analysis with:'
echo
echo 'python run_analysis.py "User Database"'
echo
echo "Logs:"
echo "  Julia-1  : $HOME/julia-llama.log"
echo "  SmolVLM2 : $HOME/smolvlm-llama.log"
echo