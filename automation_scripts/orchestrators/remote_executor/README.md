# Remote Execution Service (Step 0.1)

Secure remote command execution and file transfer from VM04 to VM01–VM04 via SSH (Paramiko), key-based auth, strong algorithms, and host key verification.

**Package path:** `automation_scripts.orchestrators.remote_executor` (ticket path "automation-scripts/orchestrators/remote_executor" refers to this directory).

---

## Installation and configuration

### Requirements

- Python 3.10+
- Paramiko >= 2.12, PyYAML >= 6.0
- VM config in `configs/config.yml` (see `config.example.yml`)
- SSH keys in `~/.ssh/th_timmy_keys` (this phase; use `hosts/vm04-orchestrator/setup_ssh_keys.sh` to create and deploy)

### Config

VM settings come from `configs/config.yml` (section `vms`). Optional section `remote_execution`:

```yaml
remote_execution:
  default_timeout: 30
  default_retry: 3
  key_storage_path: "~/.ssh/th_timmy_keys"
  checksum_algorithm: "sha256"
  # allowed_vm_ids: ["vm01", "vm02", "vm03", "vm04"]
```

---

## Usage

From repo root with `PYTHONPATH` set to repo root:

```python
from automation_scripts.orchestrators.remote_executor import (
    execute_remote_command,
    execute_remote_script,
    upload_file,
    download_file,
    RemoteExecutionResult,
)

# Run a command on vm01
result = execute_remote_command("vm01", "echo hello", "operator", 30.0)
# result: RemoteExecutionResult(stdout="hello\n", stderr="", exit_code=0, execution_time=..., ...)

# Run a script (path on remote host)
result = execute_remote_script("vm01", "/tmp/myscript.sh", "operator", 60.0)

# Upload then run: upload_first=True, local_script_path="/local/path"
result = execute_remote_script("vm01", "/tmp/myscript.sh", "operator", 60.0,
    upload_first=True, local_script_path="/path/on/vm04/myscript.sh")

# Upload file (SHA256 verified on remote)
upload_file("vm01", "/local/file.txt", "/remote/file.txt", "operator")

# Download file (SHA256 verified locally)
download_file("vm01", "/remote/out.txt", "/local/out.txt", "operator")
```

Optional kwargs: `config_path`, `config` (dict), `working_directory`, `environment`, `retries`, `timeout` (for upload/download), `verify_checksum`.

---

## Running tests

**All test runs use `run_python.sh`** so the same `.venv` and requirements apply as for n8n and automation. There is no supported path that bypasses it.

### Unit tests (pytest)

From project root (e.g. on VM04):

```bash
cd /path/to/th_timmy
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v --tb=short
```

With coverage:

```bash
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v --tb=short --cov=automation_scripts --cov-report=term-missing
```

Manual venv + pytest (e.g. when debugging run_python.sh) is not the standard path; use `run_python.sh` for normal and CI runs.

### Integration tests (Bash, run on VM04)

Integration tests are in Bash. **Primary run is on VM04** (orchestrator). The script runs **unit tests and the Python sanity check only via `run_python.sh`**; if `run_python.sh` is missing, those steps are skipped with a clear message.

1. **On VM04**, ensure:
   - Full project under `/path/to/th_timmy` (including `hosts/vm04-orchestrator/run_python.sh` and `tests/unit/`).
   - `configs/config.yml` exists (copy from `config.example.yml`, set VM IPs, ssh_user, ssh_port).
   - SSH keys in `~/.ssh/th_timmy_keys/`; run `hosts/vm04-orchestrator/setup_ssh_keys.sh` if needed.
   - Python 3.10+ (for run_python.sh and bootstrap).

2. **Run the integration script:**

   ```bash
   cd /path/to/th_timmy
   chmod +x tests/integration/run_remote_executor_integration.sh
   ./tests/integration/run_remote_executor_integration.sh
   ```

   Or set `PROJECT_ROOT` if not running from project root.

3. **Behaviour:**
   - Checks python3 and config/keys.
   - Runs unit tests and sanity check **via `run_python.sh`** (bootstrap + .venv). No fallback to raw `python3` or `pip install --user`.
   - Writes results under `$PROJECT_ROOT/results/` (or `$RESULTS_DIR`).

4. **Result for DEV:** Exit code 0/1; full log and `results/remote_executor_integration_*.txt` for analysis.

---

## Troubleshooting

| Symptom | Action |
|--------|--------|
| `FileNotFoundError: Config not found` | Ensure `configs/config.yml` exists and `cwd` or `config_path` points to it. |
| `FileNotFoundError: No private key found for vm_id=...` | Run `hosts/vm04-orchestrator/setup_ssh_keys.sh` and/or set `remote_execution.key_storage_path` to the key directory. |
| `ValueError: vm_id ... not in allowed list` | Add vm to `vms` in config with `enabled: true` or to `remote_execution.allowed_vm_ids`. |
| `SSHConnectionError` / `AuthenticationError` | Check VM IP, port, user, and that the matching key in `~/.ssh/th_timmy_keys` is deployed to the target VM. |
| SHA256 mismatch on upload/download | Network or disk issue; retries are used; check stderr and audit logs. |

---

## Security (keys, rotation)

- Keys are read from `~/.ssh/th_timmy_keys` (this phase). Do not store keys in the repo.
- Strong algorithms only (weak ciphers/kex disabled in Paramiko Transport).
- Host key must be verified (no auto-accept). Use known_hosts or supply host_key when required.
- All operations are audit-logged (user_id, vm_id, command/op, start/end, status); no passwords or raw keys in logs.
- Key rotation (90 days) and procedures are described in project hardening/security docs.
