# Troubleshooting Dashboard API Container

## Problem: Container in "Restarting (1)" state

### Quick Diagnosis

1. **Check container logs:**
   ```bash
   docker logs threat-hunting-dashboard-api --tail 100
   ```

2. **Run debug script:**
   ```bash
   cd /home/thadmin/th_timmy/hosts/vm04-orchestrator
   ./debug-container.sh
   ```

3. **Test container manually:**
   ```bash
   docker run --rm --entrypoint /bin/bash vm04-orchestrator-dashboard-api
   # Inside container:
   cd /app/automation-scripts
   python3 -c "import api.dashboard_api"
   ```

### Common Issues and Solutions

#### Issue 1: Import Error - ModuleNotFoundError

**Symptoms:**
```
ModuleNotFoundError: No module named 'api'
```

**Solution:**
- Verify WORKDIR is `/app/automation-scripts` in Dockerfile
- Check that `api/__init__.py` exists
- Verify PYTHONPATH includes `/app`

#### Issue 2: Import Error - Relative imports

**Symptoms:**
```
ImportError: attempted relative import with no known parent package
```

**Solution:**
- Ensure CMD uses `python3 -m uvicorn api.dashboard_api:app`
- Do NOT use direct script execution
- Verify module structure is correct

#### Issue 3: Missing dependencies

**Symptoms:**
```
ModuleNotFoundError: No module named 'xxx'
```

**Solution:**
- Check if package is in `requirements-api.txt`
- Rebuild image: `docker compose build dashboard-api`

#### Issue 4: Config file not found

**Symptoms:**
```
FileNotFoundError: configs/config.yml
```

**Solution:**
- Verify config file exists in mounted volume
- Check CONFIG_PATH environment variable
- Ensure volume mount in docker-compose.yml is correct

### Manual Container Testing

```bash
# Start container with shell
docker run -it --rm \
  -v /home/thadmin/th_timmy/configs:/app/configs:ro \
  -v /home/thadmin/th_timmy/logs:/app/logs \
  -v /home/thadmin/th_timmy/automation-scripts:/app/automation-scripts \
  -e CONFIG_PATH=/app/configs/config.yml \
  -e PYTHONPATH=/app \
  --entrypoint /bin/bash \
  vm04-orchestrator-dashboard-api

# Inside container, test imports:
cd /app/automation-scripts
python3 -c "import sys; print(sys.path)"
python3 -c "import api.dashboard_api; print('OK')"
python3 -m uvicorn api.dashboard_api:app --host 0.0.0.0 --port 8000
```

### Rebuild and Restart

```bash
cd /home/thadmin/th_timmy/hosts/vm04-orchestrator
docker compose down dashboard-api
docker compose build --no-cache dashboard-api
docker compose up -d dashboard-api
docker compose logs -f dashboard-api
```
