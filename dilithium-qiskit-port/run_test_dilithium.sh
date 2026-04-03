#!/bin/bash
# ====================================================================
# Quantum Dilithium JS ↔ Python Authentication Test Runner
# Platform: Linux & macOS (Bash)
# ====================================================================

set -e  # Exit on error

echo ""
echo "===================================================================="
echo "   QUANTUM DILITHIUM AUTHENTICATION TEST (JSON-based Protocol)"
echo "     Board Client (LyCheeRVnano) ↔ Python Server"
echo "===================================================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ ERROR: Python not found!"
    echo "   Please install Python from: https://python.org/"
    exit 1
fi

# Get versions
PYTHON_CMD=$(command -v python3 || command -v python)
PYTHON_VERSION=$($PYTHON_CMD --version)

echo "✅ Python detected: $PYTHON_VERSION"
echo ""

# Create data directory
mkdir -p data
echo "📁 Created ./data directory"
echo ""

echo "===================================================================="
echo "PHASE 1: PREPARE ENVIRONMENT"
echo "===================================================================="
echo ""

# Clean up old files (JSON format)
rm -f data/publickey.json data/challenge.json data/signature.json data/verification_result.json logs_alice.txt

echo "✅ Environment prepared"
echo ""

echo "===================================================================="
echo "PHASE 2: SERVER - RUNNING TEST (JSON Protocol)"
echo "===================================================================="
echo ""
echo "📦 This server waits for JSON from board client:"
echo "    - Waiting for: ./data/publickey.json"
echo "    - Will create: ./data/challenge.json"
echo "    - Will read:   ./data/signature.json"
echo "    - Result file: ./data/verification_result.json"
echo ""
Running: $PYTHON_CMD run_test_dilithium_quantum.py
echo ""

# Run Python server (Quantum version with Qiskit)
$PYTHON_CMD run_test_dilithium_quantum.py

SERVER_STATUS=$?

if [ $SERVER_STATUS -ne 0 ]; then
    echo ""
    echo "❌ ERROR: Server verification failed!"
    exit 1
fi

echo ""
echo "===================================================================="
echo "PHASE 3: RESULTS"
echo "===================================================================="
echo ""

# Display file contents
echo "[GENERATED FILES - JSON Format]"
echo ""

[ -f "data/publickey.json" ] && echo "✅ ./data/publickey.json (Public Key)"
[ -f "data/challenge.json" ] && echo "✅ ./data/challenge.json (Challenge)"
[ -f "data/signature.json" ] && echo "✅ ./data/signature.json (Signature)"
[ -f "data/verification_result.json" ] && echo "✅ ./data/verification_result.json (Verification Result)"

echo ""
echo "===================================================================="
echo "✅ AUTHENTICATION WORKFLOW COMPLETE!"
echo "===================================================================="
echo ""
echo "📚 For more details, see: WORKFLOW_JS_PYTHON.md"
echo ""
