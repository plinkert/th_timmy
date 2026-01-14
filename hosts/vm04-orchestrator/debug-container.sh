#!/bin/bash
# Debug script to check container issues
# Usage: ./debug-container.sh

echo "=== Container Status ==="
docker ps -a | grep dashboard-api

echo ""
echo "=== Container Logs (last 100 lines) ==="
docker logs threat-hunting-dashboard-api --tail 100

echo ""
echo "=== Testing Container Entrypoint ==="
docker run --rm --entrypoint /bin/bash vm04-orchestrator-dashboard-api -c "
    echo 'PYTHONPATH:' \$PYTHONPATH
    echo 'CONFIG_PATH:' \$CONFIG_PATH
    echo ''
    echo 'Checking Python path:'
    python3 -c 'import sys; print(\"\\n\".join(sys.path))'
    echo ''
    echo 'Checking if api module exists:'
    ls -la /app/automation-scripts/api/ 2>&1 | head -10
    echo ''
    echo 'Testing import:'
    cd /app/automation-scripts && python3 -c 'import api.dashboard_api' 2>&1
"
