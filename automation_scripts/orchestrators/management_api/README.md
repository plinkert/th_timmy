# Management API (Step 0.5)

HTTP API for the Management Dashboard – VM status cards, sync repo, backup config.

## Endpoints

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | /api/v1/dashboard/status | read_only+ | VM status (vm01–vm04), colors: green/orange/red |
| POST | /api/v1/dashboard/sync-repo | admin | sync_repository_to_all_vms() |
| POST | /api/v1/dashboard/backup-config | admin | backup_config(vm04, central) |
| POST | /api/v1/dashboard/refresh | hunter/admin | get_health_status(refresh=True) |

## Integration

Mounted in `hunt_api` (same port 8000). n8n workflow `management-dashboard.json` calls these endpoints.

## Authorization

- **X-User-Role**: admin | hunter | read_only (default: read_only)
- **TH_DASHBOARD_API_KEY** (env): if set, require X-API-Key or Authorization header

## Config

`management_dashboard` in `configs/config.yml` (roles, refresh_interval_seconds).
