#!/bin/bash
set -e

MODEL_PATH="${MODEL_PATH:-models/threat_fusion_v1.pt}"

if [ "${TRAIN_MODEL}" = "true" ] || [ ! -f "$MODEL_PATH" ]; then
    echo "=== Training ThreatFusionModel ==="
    python -m src.ai_engine.train
    echo "=== Training complete ==="
else
    echo "=== Model found at $MODEL_PATH, skipping training ==="
fi

echo "=== Starting AI Threat Fusion Engine ==="
exec python -m src.ai_engine.server
