#!/bin/bash
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <vm-public-ip> [ssh-private-key-path]"
    echo ""
    echo "Deploys SENTINEL-X to a production VM."
    echo ""
    echo "Environment variables (optional):"
    echo "  SENTINEL_DB_PASSWORD     - Database password (auto-generated if not set)"
    echo "  SENTINEL_JWT_SECRET      - JWT signing secret (auto-generated if not set)"
    echo "  SENTINEL_GRAFANA_PASSWORD - Grafana admin password (auto-generated if not set)"
    echo "  NASA_API_KEY             - NASA API key for EONET/DONKI"
    exit 1
fi

VM_IP="$1"
SSH_KEY="${2:-$HOME/.ssh/id_rsa}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Generate secrets if not provided
export SENTINEL_DB_PASSWORD="${SENTINEL_DB_PASSWORD:-$(openssl rand -base64 24)}"
export SENTINEL_JWT_SECRET="${SENTINEL_JWT_SECRET:-$(openssl rand -base64 48)}"
export SENTINEL_GRAFANA_PASSWORD="${SENTINEL_GRAFANA_PASSWORD:-$(openssl rand -base64 18)}"
export NASA_API_KEY="${NASA_API_KEY:-}"

echo "=== Deploying SENTINEL-X to $VM_IP ==="
echo "  DB Password:       $SENTINEL_DB_PASSWORD"
echo "  JWT Secret:        ${SENTINEL_JWT_SECRET:0:16}..."
echo "  Grafana Password:  $SENTINEL_GRAFANA_PASSWORD"
echo "  NASA API Key:      ${NASA_API_KEY:-<not set>}"
echo ""

# Update inventory with VM IP and SSH key
sed -i "s/CHANGE_ME_VM_PUBLIC_IP/$VM_IP/g" "$SCRIPT_DIR/inventory.yml"
sed -i "s|CHANGE_ME_PATH_TO_SSH_KEY|$SSH_KEY|g" "$SCRIPT_DIR/inventory.yml"

# Run Ansible playbook
cd "$SCRIPT_DIR"
ansible-playbook -i inventory.yml playbook.yml -v

echo ""
echo "=== Deployment complete! ==="
echo "Access the dashboard at: http://$VM_IP"
echo "Grafana: http://$VM_IP/grafana/ (admin / $SENTINEL_GRAFANA_PASSWORD)"
echo "API docs: http://$VM_IP:8000/docs"
