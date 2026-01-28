# Configuration Management Service (Step 0.3)

Central management and sync of config files on all VMs with validation (JSON Schema), encrypted backup, and rollback.

**Package path:** `automation_scripts.orchestrators.config_manager`

---

## Requirements

- **Step 0.1 (Remote Execution)** – `download_file`, `upload_file`, `execute_remote_command` for fetching and writing config files on VMs.
- **Step 0.2 (Repository Sync)** – optional; repo may hold schema files under `config_management.schema_dir`.
- **config_management** section in `configs/config.yml` (see `config.example.yml`).

---

## Config

In `configs/config.yml` add (or copy from `config.example.yml`):

```yaml
config_management:
  backup_location: "/var/backups/th_timmy/config"
  backup_retention_days: 90
  encryption_method: "AES"
  encryption_key_path: ""   # Or set TH_TIMMY_CONFIG_BACKUP_KEY_PATH / TH_TIMMY_CONFIG_BACKUP_PASSPHRASE
  backup_remote_path: ""   # Optional: off-host copy; empty = local only
  config_paths:            # (config_type, vm_id) -> remote path on VM
    central:
      default: "/opt/th_timmy/configs/central.yml"
    vm_specific:
      vm01: "/opt/th_timmy/configs/vm01.yml"
      # ...
  config_schemas:          # config_type -> schema file (relative to schema_dir)
    central: "central_config.schema.json"
    vm_specific: "vm_config.schema.json"
  schema_dir: "configs/schemas"
```

- **Encryption:** Use `TH_TIMMY_CONFIG_BACKUP_PASSPHRASE` (env) or `encryption_key_path` (32-byte key file). Do not store keys in the repo.
- **Backup retention:** Minimum 90 days; older backups are purged on create.
- **backup_location and permissions:** If the directory does not exist, the script creates it. When `backup_location` is under a system directory (e.g. `/var/backups/th_timmy/config`), the process must run with **elevated privileges (e.g. sudo)** so it can create and write to that path. Alternatively, set `backup_location` to a path writable by the current user (e.g. under the project or home directory) so that sudo is not required.

---

## Usage

From project root with `PYTHONPATH` set (e.g. via `run_python.sh`):

```python
from automation_scripts.orchestrators.config_manager import (
    get_config,
    update_config,
    backup_config,
    restore_config,
    sync_config_to_vm,
    validate_config,
    create_backup,
    restore_backup,
    list_backups,
)

# Get current config from VM
data = get_config("vm01", "central")

# Update config (validate, backup, atomic write; rollback on failure)
result = update_config("vm01", "central", {"config_version": "1", "description": "updated"}, validate=True, backup=True)

# Backup current config
backup_id = backup_config("vm01", "central")

# Restore from backup
restore_config("vm01", "central", backup_id)

# Sync config to VM (optional validate/backup)
sync_config_to_vm("vm01", "central", new_data, validate=True, backup=False)

# List backups
backups = list_backups(vm_id="vm01", config_type="central")
```

---

## Atomic write and rollback

- **Write:** Config is written to `remote_path.new`, then `mv remote_path.new remote_path` on the VM.
- **Rollback:** If write fails, the last backup (from the same update) is restored and re-uploaded to the VM.

---

## Tests

- **Unit:**  
  `./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/test_config_validator.py tests/unit/test_config_backup.py tests/unit/test_config_manager.py -v`

- **Integration:**  
  `./tests/integration/run_config_manager_integration.sh` (from project root on VM04).  
  See script header for run instructions and [docs/TESTING.md](../../../docs/TESTING.md).

---

## Security

- Backup files are encrypted (AES-256-GCM). Key from env or secure path; never in repo.
- All remote operations are audit-logged via Step 0.1 (user `config_manager`).
