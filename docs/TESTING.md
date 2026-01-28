# Testing Guide

This guide explains how to use the testing scripts for connectivity, data flow validation, and the Remote Execution Service (Step 0.1).

## Remote Execution Service tests (Step 0.1)

### Unit tests

Unit tests for the Remote Execution module (`audit_logger`, `remote_executor`, `ssh_client`, `ssh_key_manager`) are run via the VM04 Python entrypoint so the same venv and bootstrap guarantees apply as in n8n:

```bash
cd /path/to/th_timmy
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v
```

Do not call `python` or `pytest` directly; always use `run_python.sh`.

### Integration test

The script `tests/integration/run_remote_executor_integration.sh` runs bootstrap (via `run_python.sh`), unit tests, and sanity checks. Run it from the project root on VM04 (or a host with access to the project and config).

**Requirements:** VM04 context, `configs/config.yml` (or copy from `configs/config.example.yml` and edit), SSH keys in `~/.ssh/th_timmy_keys` (see `hosts/vm04-orchestrator/setup_ssh_keys.sh`).

**What it does:** Ensures the environment is ready, runs unit tests, performs a short sanity check, and writes results under `results/` (e.g. `remote_executor_integration_YYYYMMDD_HHMMSS.txt`).

```bash
cd /path/to/th_timmy
./tests/integration/run_remote_executor_integration.sh
```

**Details:** [automation_scripts/orchestrators/remote_executor/README.md](../automation_scripts/orchestrators/remote_executor/README.md) (usage, troubleshooting, security).

---

## Repository Sync Service tests (Step 0.2)

### Unit tests

Unit tests for the Repository Sync module (`git_manager`, `repo_sync`, `secret_scanner`) are run via `run_python.sh`:

```bash
cd /path/to/th_timmy
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/test_git_manager.py tests/unit/test_secret_scanner.py tests/unit/test_repo_sync.py -v
```

Or run all unit tests including repo_sync:

```bash
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v
```

### Integration test

The script `tests/integration/run_repo_sync_integration.sh` runs bootstrap (via `run_python.sh`), repo_sync unit tests, and a sanity check (import + config.repository). Run it from the project root on VM04.

**Requirements:** VM04 context, `configs/config.yml` with `repository.main_repo_path` and `repository.vm_repo_paths` (see `config.example.yml`). Optional: SSH keys in `~/.ssh/th_timmy_keys` for live verify/check tests.

**Instructions:** See the script header (INSTRUKCJA URUCHAMIANIA) for steps. In short:

```bash
cd /path/to/th_timmy
chmod +x tests/integration/run_repo_sync_integration.sh
./tests/integration/run_repo_sync_integration.sh
```

Results are written to `results/repo_sync_integration_YYYYMMDD_HHMMSS.txt`.

**Details:** [automation_scripts/orchestrators/repo_sync/README.md](../automation_scripts/orchestrators/repo_sync/README.md), [docs/REPO_SYNC_DESIGN.md](REPO_SYNC_DESIGN.md).

---

## Overview

The testing suite includes three main scripts:

1. **`test_connections.sh`** - Tests connectivity between VMs
2. **`test_data_flow.sh`** - Tests data flow between VMs
3. **`test_before_after_hardening.sh`** - Tests before and after hardening

## Prerequisites

- All 4 VMs must be installed and running
- `configs/config.yml` must be configured with correct IP addresses
- Network connectivity between VMs must be established
- Required tools installed (ping, nc/netcat, curl, python3)

## Connection Testing

### Basic Usage

```bash
cd /path/to/th_timmy
./hosts/shared/test_connections.sh [config_file]
```

### What It Tests

- **Ping connectivity**: Tests basic network connectivity to all VMs
- **SSH connectivity**: Tests SSH access (optional, may require keys)
- **Service ports**: Tests PostgreSQL (5432), JupyterLab (8888), n8n (5678)
- **Database connection**: Tests PostgreSQL connection from VM-01 to VM-02
- **JupyterLab connection**: Tests JupyterLab accessibility from VM-04 to VM-03
- **n8n connection**: Tests n8n accessibility from VM-03 to VM-04

### Output

The script provides:
- Color-coded output (✓ for pass, ✗ for fail, ⚠ for warning)
- Summary statistics (passed/failed/warnings)
- JSON results file in `test_results/connections_YYYYMMDD_HHMMSS.json`

### Example Output

```
==========================================
VM Connectivity Tests
==========================================

ℹ Current host: vm01
ℹ Date: 2024-01-15 10:30:00

ℹ VM-01 (Ingest): 10.0.0.10
ℹ VM-02 (Database): 10.0.0.11
ℹ VM-03 (Analysis): 10.0.0.12
ℹ VM-04 (Orchestrator): 10.0.0.13

==========================================
Basic Connectivity (Ping)
==========================================
✓ Ping to VM-01 (10.0.0.10)
✓ Ping to VM-02 (10.0.0.11)
✓ Ping to VM-03 (10.0.0.12)
✓ Ping to VM-04 (10.0.0.13)

==========================================
Connection Test Summary
==========================================
  Passed: 8
  Failed: 0
  Warnings: 2
==========================================

ℹ Results saved to: test_results/connections_20240115_103000.json
✓ All connection tests passed!
```

## Data Flow Testing

### Basic Usage

```bash
cd /path/to/th_timmy
./hosts/shared/test_data_flow.sh [config_file]
```

### What It Tests

- **Database write**: Tests writing data from VM-01 to VM-02 (PostgreSQL)
- **Database read**: Tests reading data from VM-02 to VM-03
- **n8n integration**: Tests n8n connectivity and health endpoints

### Prerequisites

- PostgreSQL must be running on VM-02
- Database credentials must be set in environment variable `POSTGRES_PASSWORD`
- Virtual environment with psycopg2 installed (optional, for database tests)

### Output

- Color-coded test results
- JSON results file in `test_results/data_flow_YYYYMMDD_HHMMSS.json`
- Automatic cleanup of test data

### Example

```bash
export POSTGRES_PASSWORD="your_password"
./hosts/shared/test_data_flow.sh
```

## Before/After Hardening Testing

### Basic Usage

```bash
cd /path/to/th_timmy
./hosts/shared/test_before_after_hardening.sh [config_file]
```

### Workflow

1. **Phase 1**: Runs connection and data flow tests BEFORE hardening
2. **Phase 2**: Waits for user to apply hardening on all VMs
3. **Phase 3**: Runs connection and data flow tests AFTER hardening
4. **Phase 4**: Compares results and shows differences

### Output Files

- `test_results/before_hardening_connections_YYYYMMDD_HHMMSS.json`
- `test_results/before_hardening_data_flow_YYYYMMDD_HHMMSS.json`
- `test_results/after_hardening_connections_YYYYMMDD_HHMMSS.json`
- `test_results/after_hardening_data_flow_YYYYMMDD_HHMMSS.json`

### Comparison Report

The script automatically compares before/after results and shows:
- Summary statistics (passed/failed/warnings)
- Individual test status changes
- Differences in test outcomes

### Example Workflow

```bash
# Start the test suite
./hosts/shared/test_before_after_hardening.sh

# Phase 1: Tests run automatically
# ... (tests complete)

# Phase 2: Script waits for user input
# Apply hardening on all VMs now
# Press Enter to continue...

# Phase 3: Tests run automatically after hardening
# ... (tests complete)

# Phase 4: Comparison report shown
# ... (comparison results)
```

## Interpreting Results

### Test Status

- **PASS (✓)**: Test completed successfully
- **FAIL (✗)**: Test failed - investigate the issue
- **WARN (⚠)**: Test completed but with warnings (e.g., service not running)

### Common Issues

#### Connection Tests Fail

- **Ping fails**: Check network connectivity, firewall rules
- **Port test fails**: Service may not be running, check service status
- **SSH fails**: May require password/key authentication (this is expected)

#### Data Flow Tests Fail

- **Database write fails**: Check PostgreSQL is running, verify credentials
- **Database read fails**: Check database connection, verify test data exists
- **n8n test fails**: n8n may not be running, check Docker container status

### JSON Results Format

```json
{
  "timestamp": "2024-01-15T10:30:00+00:00",
  "hostname": "vm01",
  "config_file": "/path/to/configs/config.yml",
  "summary": {
    "passed": 8,
    "failed": 0,
    "warnings": 2,
    "total": 10
  },
  "vm_ips": {
    "vm01": "10.0.0.10",
    "vm02": "10.0.0.11",
    "vm03": "10.0.0.12",
    "vm04": "10.0.0.13"
  },
  "tests": [
    {
      "name": "Ping to VM-01 (10.0.0.10)",
      "status": "PASS"
    },
    ...
  ]
}
```

## Troubleshooting

### Problem: Script cannot find config.yml

**Solution**: 
- Ensure `configs/config.yml` exists
- Or provide path as argument: `./test_connections.sh /path/to/config.yml`

### Problem: Tests fail with "command not found"

**Solution**:
- Install required tools: `apt-get install netcat-openbsd curl`
- Ensure Python 3 is installed: `apt-get install python3`

### Problem: Database tests fail

**Solution**:
- Set `POSTGRES_PASSWORD` environment variable
- Verify PostgreSQL is running: `systemctl status postgresql`
- Check database credentials in config.yml

### Problem: Results not saved

**Solution**:
- Check `test_results/` directory exists and is writable
- Verify disk space: `df -h`
- Check permissions: `ls -ld test_results/`

## Best Practices

1. **Run tests regularly**: Test connectivity after any network changes
2. **Save results**: Keep JSON result files for comparison
3. **Test before/after changes**: Always test before and after configuration changes
4. **Document issues**: Note any failures and their resolutions
5. **Automate testing**: Consider adding tests to CI/CD pipeline

## Integration with CI/CD

The test scripts can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Test Connections
  run: |
    cd ${{ github.workspace }}
    ./hosts/shared/test_connections.sh
  continue-on-error: true
```

