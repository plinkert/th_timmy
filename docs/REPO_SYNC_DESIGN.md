# Repository Sync Service (Step 0.2) – Design

**Model:** Sync-on-VM04 + push to VM01–VM03 via SSH (rsync).

---

## 1. Sync model

- **VM04** is the single source of truth: the main repository lives at `repository.main_repo_path`.
- **Synchronization** runs only on VM04: `git pull` (or fetch + reset) updates the local tree.
- **Distribution** to VM01–VM03: VM04 pushes the whole project tree via **rsync over SSH** to each target host (similar to `/home/user/Desktop/TH/deploy_to_hosts.sh`).
- **VM01–VM03** do not run Git; they receive a file tree only (optionally excluding `.git`). No clone or `git pull` on targets.
- **Verification:** A sentinel file (e.g. `.sync_rev`) is written with the commit hash before rsync; after push, `check_repo_status` / `verify_sync` use `execute_remote_command` (Step 0.1) to read that file on each target and compare with VM04’s hash.

## 2. Advantages over “git on every VM”

- No Git install or clone on VM01–VM03.
- Only VM04 talks to the Git remote; targets need no network access to the repo.
- Fewer moving parts on targets; logic and failures are centralized on VM04.
- Same pattern as the existing `deploy_to_hosts.sh`: one source, rsync push.

## 3. Components

- **git_manager.py** – Git operations on VM04 only: `get_commit_hash`, `pull_repository`, `fetch_repository`, `reset_to_commit`, `clone_repository`. Auth via SSH or PAT (no plaintext passwords).
- **repo_sync.py** – `sync_repository_to_vm(vm_id, branch, force)`: (1) optional secret scan, (2) git pull/fetch+reset on VM04, (3) write `.sync_rev` with hash, (4) rsync tree to target; `sync_repository_to_all_vms`, `check_repo_status` (read `.sync_rev` via `execute_remote_command`), `verify_sync(expected_commit)`.
- **secret_scanner.py** – gitleaks (or equivalent) before sync; block and alert on secrets; no secrets in logs.

## 4. Config (repository section)

- `main_repo_path` – path to repo on VM04.
- `vm_repo_paths` – per vm_id, path on target (where rsync writes; default e.g. `~/th_timmy` or `/opt/th_timmy`).
- `default_branch`, `exclude_dot_git` (default True), `rsync_excludes` (e.g. `.git`, `__pycache__`, `.vscode`).
- `secret_scanning` – enabled, tool, config_path, block_on_secrets.

## 5. Step 0.1 usage

- **execute_remote_command** – used only for **verification**: e.g. `cat <vm_repo_path>/.sync_rev` on each target to get the last-pushed commit hash. No Git commands run on targets.
- **SSH keys** – same as Step 0.1: `~/.ssh/th_timmy_keys`, `id_ed25519_{vm_id}`; rsync uses `-e "ssh -i <key_path>"` when key path is configured.
- Config: reuses `vms` (ip, ssh_user, ssh_port) and, if present, `remote_execution.key_storage_path` for key lookup.

## 6. Branch protection and secret scanning

- Branch protection (main: PR, 2 reviews, tests, no direct push) – configured in the hosting system; documented in README and docs.
- Secret scanning (gitleaks) – run before each sync from repo_sync; on secrets: block sync and log alert; recommend CI integration for pushes.
