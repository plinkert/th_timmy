# VM-04: Orchestrator

This folder contains scripts and config for VM-04 (Orchestrator host with n8n in Docker). Use this README as a step-by-step guide.

---

## Overview

VM-04 is the orchestrator node. It runs:
- **n8n** (workflow automation) in Docker
- **Python** tooling and automation scripts
- **SSH** access to VM01–VM03 for remote execution

All Python-based automation on VM04, including the **Remote Execution Service (Step 0.1)** (remote commands and file transfer via `automation_scripts.orchestrators.remote_executor`), uses `run_python.sh` and `bootstrap_env.sh` as the single entrypoint — see sections below.

Recommended order of actions:

1. **Bootstrap environment** – `./bootstrap_env.sh` (Python venv, dependencies, sanity check)
2. **Install VM-04** – `sudo ./install_vm04.sh` (Docker, n8n, system packages)
3. **Verify** – `./health_check.sh` (checks installation)
4. **SSH keys** – `./setup_ssh_keys.sh` (keys for VM01–VM03)
5. **Harden** (optional) – `sudo ./harden_vm04.sh` (security hardening)

---

## Folder Contents and Script Purposes

| File / folder | Purpose |
|---------------|--------|
| **run_python.sh** | **Single entrypoint for all Python runs** (n8n, tests, automation). Runs bootstrap on demand (idempotent), then executes `.venv/bin/python` with the given args. **Rule: n8n must never call `python` directly; always call this script.** See *run_python.sh and n8n* below. |
| **bootstrap_env.sh** | Prepares Python env (idempotent): checks python3/pip/ssh, creates/validates `.venv`, installs from `requirements.txt` (+ `requirements-dev.txt` if present), runs import and sanity checks. Used by `run_python.sh` on every run; can also be run manually. Exit 0 = env ready; non‑zero = stop. |
| **install_vm04.sh** | Full VM-04 setup: system tools, Docker, Python 3.10+, pip, venv, n8n (Docker), firewall. Requires sudo. Use after bootstrap if you want install automation. |
| **health_check.sh** | Verifies installed components: OS, Docker, Python, venv, packages, n8n container, ports, firewall. Run after install. |
| **setup_ssh_keys.sh** | Generates SSH keys for VM01–VM03, copies them to targets, enforces key-only auth, writes `~/.ssh/config`. Run when you need passwordless SSH to VM01/02/03. |
| **harden_vm04.sh** | Security hardening: SSH, firewall, Docker, Fail2ban, logrotate. Optional, usually after install. |
| **requirements.txt** | Python dependencies for this host (pyyaml, docker, loguru, etc.). Used by `bootstrap_env.sh` and install logic. |
| **docker-compose.yml** | Defines n8n container and options. Used by `install_vm04.sh` and when you run `docker compose`. |
| **config.example.yml** | Example config for n8n (user, password, port). Copy to `config.yml` and edit. |
| **config.yml** | Your local n8n config (create from `config.example.yml`). Not committed. |
| **.env** | Generated for docker-compose (e.g. n8n credentials). Created by install/scripts. Not committed. |

Paths are relative to the project root (th_timmy). Scripts that need the project root accept it via argument or `BOOTSTRAP_PROJECT_ROOT` / `PROJECT_ROOT` where relevant.

---

## Step-by-Step: How to Use This Folder

### Step 0: Get the project and open this folder

```bash
cd /path/to/th_timmy
cd hosts/vm04-orchestrator
```

### Step 1: Bootstrap the environment (required for dev/test/CI)

**Purpose:** One canonical way to get a working Python environment. No manual `pip install` or `python -m venv` outside this script.

```bash
# From project root (recommended)
cd /path/to/th_timmy
./hosts/vm04-orchestrator/bootstrap_env.sh

# Or from this folder (project root = parent of hosts/)
./bootstrap_env.sh

# With custom project root
BOOTSTRAP_PROJECT_ROOT=/path/to/th_timmy ./bootstrap_env.sh
./bootstrap_env.sh /path/to/th_timmy
```

- **Exit 0:** Environment ready. You can run tests and automation.
- **Exit ≠ 0:** Stop; fix the reported error before running tests or other scripts that assume the env is ready.

See the **Bootstrap script (bootstrap_env.sh)** section below for details.

### Step 2: Create n8n config (required for install)

```bash
cp config.example.yml config.yml
nano config.yml   # set basic_auth_password and any other required values
```

### Step 3: Install VM-04 (Docker, n8n, system packages)

```bash
sudo ./install_vm04.sh [PROJECT_ROOT] [CONFIG_FILE]
# Examples:
sudo ./install_vm04.sh
sudo ./install_vm04.sh $HOME/th_timmy config.yml
```

This installs system tools, Docker, Python 3.10+, pip, venv, packages from `requirements.txt`, n8n via Docker, and configures the firewall for port 5678.

### Step 4: Verify installation

```bash
./health_check.sh [PROJECT_ROOT] [CONFIG_FILE]
# Example:
./health_check.sh $HOME/th_timmy config.yml
```

Resolve any failed checks before relying on n8n or automation.

### Step 5: Configure SSH access to VM01–VM03 (when needed)

```bash
./setup_ssh_keys.sh
# Or with sudo if you need elevated permissions for SSH config/key placement:
sudo ./setup_ssh_keys.sh
```

Ensures key-based SSH to VM01/02/03 and disables password auth on those hosts (see **SSH Key Management** below).

### Step 6 (optional): Harden the host

```bash
sudo ./harden_vm04.sh
```

---

## Bootstrap script (bootstrap_env.sh)

### Purpose

- **Single entrypoint** for preparing the Python environment for DEV, TEST, CI, and automation.
- **Rule:** No manual `pip install` or `python -m venv` outside this script.
- Ensures a consistent, testable environment before any tests or automation run.

### What it does

1. **System checks (fail fast)**  
   - python3 ≥ 3.10  
   - pip  
   - python3-venv  
   - openssh-client  

2. **Virtualenv**  
   - Uses project root `.venv/` (by default two levels up from `hosts/vm04-orchestrator/`).  
   - If missing → create.  
   - If broken → remove and recreate.  

3. **Dependencies**  
   - `pip install -r requirements.txt` (required).  
   - `pip install -r requirements-dev.txt` if that file exists (optional).  

4. **Validation**  
   - Imports: `paramiko`, `pytest`, `yaml`, `requests`.  
   - If any import fails, bootstrap fails.  

5. **Sanity**  
   - Short self-test (e.g. `import paramiko` + print).  
   - Bootstrap succeeds only if this passes.  

### How to run

From **project root** (recommended):

```bash
cd /path/to/th_timmy
./hosts/vm04-orchestrator/bootstrap_env.sh
```

From **this folder**:

```bash
cd /path/to/th_timmy/hosts/vm04-orchestrator
./bootstrap_env.sh
```

With **explicit project root**:

```bash
BOOTSTRAP_PROJECT_ROOT=/path/to/th_timmy ./bootstrap_env.sh
# or
./bootstrap_env.sh /path/to/th_timmy
```

### Output and exit codes

- **Exit 0:** Environment ready. Message includes `BOOTSTRAP SUCCESS` and paths.
- **Exit ≠ 0:** Bootstrap failed. Do not run tests or automation until this passes.

All messages are in English and deterministic so that CI and scripts can parse success/failure clearly.

---

## run_python.sh – single Python entrypoint (n8n / automation)

### Rule

**Every Python run from n8n (or automation) must use `.venv` and guarantee that `.venv` is correct.**

- **n8n must never call `python` or `python3` directly.**  
- **n8n always calls `run_python.sh`.**  

This avoids “works only on one host”, “QA skipped bootstrap”, “after deploy something broke”: each run ensures bootstrap has been applied (idempotent; fast if env is OK, repairs if broken).

### What run_python.sh does

1. Resolves project root (`BOOTSTRAP_PROJECT_ROOT`, or `PROJECT_ROOT`, or two levels up from the script).
2. Runs `bootstrap_env.sh` (idempotent: quick check if env is OK, full fix if not).
3. `cd` to project root, sets `PYTHONPATH`, then `exec .venv/bin/python "$@"`.

So: “run Python” = “ensure env, then run Python from .venv”.

### Usage

```bash
# From project root (recommended)
cd /path/to/th_timmy
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v

# From this folder
cd /path/to/th_timmy/hosts/vm04-orchestrator
./run_python.sh -m pytest tests/unit/ -v

# With explicit project root (e.g. from n8n when cwd is not project root)
BOOTSTRAP_PROJECT_ROOT=/path/to/th_timmy ./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v
```

### n8n: how to call Python

In n8n “Execute Command” (or equivalent):

- **Command:** absolute path to `run_python.sh`, e.g. `/home/thadmin/th_timmy/hosts/vm04-orchestrator/run_python.sh`
- **Arguments:** the Python invocation, e.g. `-m pytest tests/unit/ -v` or `-c "from automation_scripts.orchestrators.remote_executor import execute_remote_command; ..."`
- **Working directory:** project root, e.g. `/home/thadmin/th_timmy`, so that `tests/unit/` and imports resolve.

If the node cannot set working directory, pass project root via env:

```text
BOOTSTRAP_PROJECT_ROOT=/home/thadmin/th_timmy /home/thadmin/th_timmy/hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v
```

Ensure `run_python.sh` is executable: `chmod +x /path/to/th_timmy/hosts/vm04-orchestrator/run_python.sh`.

---

## Running tests via run_python.sh

**All test runs go through `run_python.sh`** so the same `.venv` and bootstrap guarantees apply as for n8n. The integration script does not fall back to raw `python3` or `pip install --user`; if `run_python.sh` is missing, it skips Python steps with a clear message.

### Unit tests (pytest)

```bash
cd /path/to/th_timmy
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v --tb=short
```

With coverage:

```bash
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v --tb=short --cov=automation_scripts --cov-report=term-missing
```

### Integration test script (Bash)

The integration script (`tests/integration/run_remote_executor_integration.sh`) runs **all Python steps (unit tests and sanity check) only via `run_python.sh`**. There is no fallback to raw `python3` or `pip install --user`; if `run_python.sh` is missing or not executable, unit tests and the sanity check are skipped with a clear message. This keeps the same guarantee as n8n: one entrypoint, one venv, one set of requirements.

```bash
cd /path/to/th_timmy
./tests/integration/run_remote_executor_integration.sh
```

The script expects a full project tree (including `hosts/vm04-orchestrator/run_python.sh` and `tests/unit/`). From a different location, set `PROJECT_ROOT` or `BOOTSTRAP_PROJECT_ROOT` to the project root.

### One-liner from anywhere (with project root set)

```bash
BOOTSTRAP_PROJECT_ROOT=/home/thadmin/th_timmy /home/thadmin/th_timmy/hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v
```

---

## Requirements (system)

- Ubuntu Server 22.04 LTS (or similar)
- sudo for install and hardening
- Internet for packages and Docker
- Valid `config.yml` (from `config.example.yml`) with at least `basic_auth_password` set for n8n

---

## Installation details (install_vm04.sh)

- Installs basic tools (git, curl, wget, vim, nano, etc.)
- Docker Engine and Docker Compose from official repo
- Python 3.10+ with pip and venv
- libssl-dev, libffi-dev
- Python packages from project `requirements.txt` (and VM-04–specific requirements if used)
- n8n via Docker (docker-compose.yml, .env)
- Firewall rules for port 5678

Post-install layout (conceptually):

```
$HOME/th_timmy/
├── hosts/vm04-orchestrator/   # this folder
│   ├── bootstrap_env.sh
│   ├── install_vm04.sh
│   ├── health_check.sh
│   ├── setup_ssh_keys.sh
│   ├── harden_vm04.sh
│   ├── requirements.txt
│   ├── docker-compose.yml
│   ├── config.example.yml
│   ├── config.yml (you create)
│   └── .env (created by install)
└── .venv/                     # created by bootstrap_env.sh
```

---

## Managing n8n

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator

# Start
docker compose up -d

# Stop
docker compose down

# Restart
docker compose restart

# Status
docker compose ps

# Logs
docker compose logs -f n8n
```

**Web UI:** `http://<VM04_IP>:5678`  
**Login:** from `config.yml`: `basic_auth_user` and `basic_auth_password`.

---

## SSH Key Management (setup_ssh_keys.sh)

**Purpose:** Configure SSH keys and key-only auth from VM-04 to VM01–VM03.

- Generates ed25519 keys per target VM
- Copies public keys to VM01/02/03
- On remote hosts: disables password auth, enforces `PubkeyAuthentication yes`
- Writes `~/.ssh/config` with entries for `vm01`, `vm02`, `vm03`

**Config:** Reads `configs/config.yml` (project root) for VM IPs, users, ports.

**Run:**

```bash
./setup_ssh_keys.sh
# or, if needed for permissions:
sudo ./setup_ssh_keys.sh
```

**After running:** `ssh vm01`, `ssh vm02`, `ssh vm03` should work without a password.

**Config source:** `configs/config.yml` under `vms.vm01|vm02|vm03` (e.g. `ip`, `ssh_user`, `ssh_port`). Example:

```yaml
vms:
  vm01:
    ip: "10.0.0.10"
    ssh_user: "thadmin"
    ssh_port: 22
  vm02:
    ip: "10.0.0.11"
    ssh_user: "thadmin"
    ssh_port: 22
  vm03:
    ip: "10.0.0.12"
    ssh_user: "thadmin"
    ssh_port: 22
```

**SSH troubleshooting:** If `~/.ssh/config` or `~/.ssh/th_timmy_keys` end up owned by root, run `sudo chown -R $USER:$USER ~/.ssh/config ~/.ssh/th_timmy_keys`. If "Could not resolve hostname vm01", ensure `~/.ssh/config` exists and has mode 600. For remote sudo password prompts, the script will ask interactively; for non-interactive use, configure NOPASSWD for the SSH user on targets.

---

## Hardening (harden_vm04.sh)

**Purpose:** Tighten security (SSH, firewall, Docker, Fail2ban, logrotate).

**Run:** `sudo ./harden_vm04.sh`

**Config:** Uses `configs/config.yml` under `hardening.*` (e.g. `hardening.firewall.allowed_network`, `hardening.vm04.enable_auditd`).

After hardening, restart n8n if needed:

```bash
docker compose down && docker compose up -d
```

---

## Troubleshooting

- **Docker “Cannot connect to the Docker daemon”**  
  Log out and back in after being added to the `docker` group, or run Docker commands with `sudo`. Check: `sudo systemctl status docker`.

- **n8n container not starting**  
  Inspect: `docker compose logs n8n`. Ensure port 5678 is free and `.env`/`config.yml` are correct.

- **n8n login fails**  
  Check `.env` and `config.yml` passwords match, then `docker compose restart n8n`.

- **Permission denied with docker**  
  Ensure user is in group `docker`: `groups`; if not, `sudo usermod -aG docker $USER` and log in again.

- **Port 5678 in use**  
  `sudo lsof -i :5678` to find the process; stop it or change the port in `config.yml` and `docker-compose.yml`.

---

## Documentation and security

- **Docs:**  
  - [Architecture](../../docs/ARCHITECTURE_ENHANCED.md)  
  - [Configuration](../../docs/CONFIGURATION.md)  

- **Security:**  
  - Do not commit `config.yml` or `.env`.  
  - Use strong n8n passwords.  
  - Restrict firewall to trusted IPs where possible.  
  - Keep images and Docker updated.  
  - Run `harden_vm04.sh` in production.

---

## Updating n8n

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose pull
docker compose up -d
```
