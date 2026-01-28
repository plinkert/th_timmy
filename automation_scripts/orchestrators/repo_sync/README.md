# Repository Sync Service (Step 0.2)

**Model:** Sync on VM04 only, then push the whole project tree to VM01–VM03 via **rsync over SSH**. Targets do not run Git; they receive a file tree (optionally without `.git`). See [docs/REPO_SYNC_DESIGN.md](../../../docs/REPO_SYNC_DESIGN.md).

---

## Requirements

- **Step 0.1 (Remote Execution)** – used for verification only: `execute_remote_command` to read `.sync_rev` on each target. SSH keys and `vms` config are shared.
- **VM04** – Git and rsync; `repository.main_repo_path` is the source of truth.
- **VM01–VM03** – Target paths in `repository.vm_repo_paths`; SSH access from VM04 (keys in `~/.ssh/th_timmy_keys`, same as Step 0.1).

### Git initialization required on VM04

The directory at `repository.main_repo_path` on VM04 **must be a Git repository** (have a `.git` directory and a valid `HEAD`). Sync uses the current commit hash for `.sync_rev` and status; if the path is not a git repo, sync fails with *"could not get commit hash (not a git repo or invalid state)"*.

If the project was copied to VM04 without cloning (e.g. rsync without `.git`), initialize Git in that directory:

```bash
cd /path/to/main_repo_path   # e.g. /home/thadmin/th_timmy
git init
git add .
git commit -m "initial"
```

No remote (GitHub) is required: if `git pull` fails (no origin, no network), the service falls back to the local state and still runs rsync to VM01–VM03.

---

## Config (`configs/config.yml` → `repository`)

- `main_repo_path` – path to repo on VM04
- `vm_repo_paths` – per vm_id, path on target (e.g. `/home/thadmin/th_timmy`)
- `default_branch` – e.g. `main`
- `exclude_dot_git` – do not push `.git` to targets (default true)
- `rsync_excludes` – list of patterns (e.g. `.git`, `__pycache__`, `.vscode`)
- `push_targets` – optional list of vm_ids to push to; default is all enabled vms except vm04
- `secret_scanning` – `enabled`, `tool` (gitleaks), `config_path`, `block_on_secrets`

See `configs/config.example.yml` for a full example.

---

## Usage

From project root with `PYTHONPATH` set to repo root (e.g. via `run_python.sh`):

```python
from automation_scripts.orchestrators.repo_sync import (
    sync_repository_to_vm,
    sync_repository_to_all_vms,
    check_repo_status,
    verify_sync,
    RepoStatus,
    scan_repository,
    SecretScanResult,
)

# Sync VM04, then push to vm01
status = sync_repository_to_vm("vm01", branch="main", force=False)

# Sync and push to all targets (vm01–vm03)
all_status = sync_repository_to_all_vms(branch="main", force=False)

# Check status (reads .sync_rev on target via execute_remote_command)
st = check_repo_status("vm01")

# Verify all targets match VM04 commit
ok = verify_sync()

# Optional: secret scan before sync (also used inside sync when run_secret_scan=True)
result = scan_repository("/path/to/repo", config_path=".gitleaks.toml")
if result.has_secrets:
    # block sync, log alert
    pass
```

---

## Tests

- **Unit:** `./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v -k "repo_sync or git_manager or secret_scanner"`
- **Integration:** `./tests/integration/run_repo_sync_integration.sh` (from project root on VM04). See script header and [TESTING.md](../../../docs/TESTING.md) for prerequisites and run instructions.

---

## Branch protection and secret scanning

- **Branch protection** (main: PR, 2 reviews, tests, no direct push) – configured in GitHub/GitLab/self-hosted; see project docs.
- **Secret scanning (gitleaks)** – run before sync from this module; on secrets, sync is blocked and an alert is logged. Recommend also running gitleaks in CI on push.
