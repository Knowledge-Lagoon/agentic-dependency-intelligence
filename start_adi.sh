#!/usr/bin/env bash

set -u

PROJECT_DIR="$HOME/agentic-dependency-intelligence"
LLAMA_DIR="$HOME/llama.cpp"

JULIA_MODEL="$HOME/models/Julia-1-Q8_0.gguf"

SMOLVLM_MODEL="$HOME/models/smolvlm2-2.2b/SmolVLM2-2.2B-Instruct-Q4_K_M.gguf"
SMOLVLM_MMPROJ="$HOME/models/smolvlm2-2.2b/SmolVLM2-2.2B-Instruct-mmproj-f16.gguf"

JULIA_PORT=8080
SMOLVLM_PORT=8081
QWEN_PORT=8082


echo "============================================================"
echo " Agentic Dependency Intelligence - Startup"
echo "============================================================"
echo


# ==========================================================
# 1. START NEO4J
# ==========================================================

echo "[1/8] Starting Neo4j..."

if podman ps --format '{{.Names}}' | grep -qx "neo4j-adi"; then
    echo "Neo4j is already running."
else
    podman start neo4j-adi

    if [ $? -ne 0 ]; then
        echo "ERROR: Could not start neo4j-adi."
        exit 1
    fi
fi

echo


# ==========================================================
# 2. WAIT FOR NEO4J
# ==========================================================

echo "[2/8] Waiting for Neo4j..."

for i in $(seq 1 30); do

    if curl -s --connect-timeout 2 \
        http://127.0.0.1:7474 >/dev/null 2>&1; then

        echo "Neo4j is READY."
        break
    fi

    if [ "$i" -eq 30 ]; then
        echo "ERROR: Neo4j did not become ready."
        exit 1
    fi

    sleep 2
done

echo


# ==========================================================
# 3. START JULIA-1 - PORT 8080
# ==========================================================

echo "[3/8] Checking Julia-1 on port 8080..."

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


# ==========================================================
# 4. START SMOLVLM2 - PORT 8081
# ==========================================================

echo "[4/8] Checking SmolVLM2 on port 8081..."

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


# ==========================================================
# 5. START QWEN3.5 - PORT 8082
# ==========================================================

echo "[5/8] Checking Qwen3.5 on port 8082..."

if curl -s --connect-timeout 2 \
    http://127.0.0.1:${QWEN_PORT}/health >/dev/null 2>&1; then

    echo "Qwen3.5 is already running."

else

    echo "Starting Qwen3.5..."

    cd "$LLAMA_DIR" || exit 1

    nohup ./build/bin/llama-server \
        -hf gguf/Qwen3.5-0.8B-GGUF:Q4_K_M \
        --host 127.0.0.1 \
        --port "$QWEN_PORT" \
        -c 4096 \
        --reasoning off \
        > "$HOME/qwen35-llama.log" 2>&1 &

    echo $! > "$HOME/qwen35-llama.pid"

fi

echo


# ==========================================================
# SERVICE WAIT FUNCTION
# ==========================================================

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


# ==========================================================
# 6. WAIT FOR ALL AI SERVICES
# ==========================================================

echo "[6/8] Waiting for AI services..."

wait_for_service "Julia-1" "$JULIA_PORT" || {
    echo "Check log: $HOME/julia-llama.log"
    exit 1
}

wait_for_service "SmolVLM2" "$SMOLVLM_PORT" || {
    echo "Check log: $HOME/smolvlm-llama.log"
    exit 1
}

wait_for_service "Qwen3.5" "$QWEN_PORT" || {
    echo "Check log: $HOME/qwen35-llama.log"
    exit 1
}

echo


# ==========================================================
# 7. CONFIGURE ADI
# ==========================================================

echo "[7/8] Configuring ADI..."

cd "$PROJECT_DIR" || exit 1

if [ ! -x ".venv/bin/python" ]; then
    echo "ERROR: ADI Python virtual environment not found."
    echo "Expected:"
    echo "$PROJECT_DIR/.venv/bin/python"
    exit 1
fi

export NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
export NEO4J_USER="${NEO4J_USER:-neo4j}"

if [ -z "${NEO4J_PASSWORD:-}" ]; then

    echo
    echo "WARNING: NEO4J_PASSWORD is not set."
    echo
    echo "Before running analysis use:"
    echo
    echo 'export NEO4J_PASSWORD="your-password"'
    echo
fi


# Check Neo4j Python driver

if "$PROJECT_DIR/.venv/bin/python" \
    -c "import neo4j" >/dev/null 2>&1; then

    echo "Neo4j Python driver: OK"

else

    echo "ERROR: Neo4j Python driver is missing from .venv."
    echo
    echo "Install with:"
    echo
    echo "$PROJECT_DIR/.venv/bin/python -m pip install neo4j"
    exit 1

fi

echo


# ==========================================================
# 8. FINAL HEALTH CHECK
# ==========================================================

echo "[8/8] Final service check..."
echo

echo "------------------------------------------------------------"
echo " ADI SERVICE STATUS"
echo "------------------------------------------------------------"

printf "%-20s %s\n" "SERVICE" "STATUS"
printf "%-20s %s\n" "--------------------" "--------------------"

if podman ps --format '{{.Names}}' | grep -qx "neo4j-adi"; then
    printf "%-20s %s\n" "Neo4j" "READY (7687)"
else
    printf "%-20s %s\n" "Neo4j" "NOT READY"
fi

if curl -s http://127.0.0.1:8080/health >/dev/null 2>&1; then
    printf "%-20s %s\n" "Julia-1" "READY (8080)"
else
    printf "%-20s %s\n" "Julia-1" "NOT READY"
fi

if curl -s http://127.0.0.1:8081/health >/dev/null 2>&1; then
    printf "%-20s %s\n" "SmolVLM2" "READY (8081)"
else
    printf "%-20s %s\n" "SmolVLM2" "NOT READY"
fi

if curl -s http://127.0.0.1:8082/health >/dev/null 2>&1; then
    printf "%-20s %s\n" "Qwen3.5" "READY (8082)"
else
    printf "%-20s %s\n" "Qwen3.5" "NOT READY"
fi

echo
echo "Neo4j URI : $NEO4J_URI"
echo "Python    : $PROJECT_DIR/.venv/bin/python"

echo
echo "------------------------------------------------------------"
echo " ADI startup complete"
echo "------------------------------------------------------------"

echo
echo "Logs:"
echo "  Julia-1  : $HOME/julia-llama.log"
echo "  SmolVLM2 : $HOME/smolvlm-llama.log"
echo "  Qwen3.5  : $HOME/qwen35-llama.log"

echo
echo "Run analysis using:"
echo
echo "$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/run_analysis.py \"User Database\""
echo