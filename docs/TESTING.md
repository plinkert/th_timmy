# Testing Guide

This guide covers the testing scripts we use to verify that everything is working correctly. These scripts help catch connectivity issues, data flow problems, and verify that hardening didn't break anything.

## Overview

We have three main testing scripts:

1. **`test_connections.sh`** - Checks if all VMs can talk to each other
2. **`test_data_flow.sh`** - Verifies the data pipeline works end-to-end
3. **`test_before_after_hardening.sh`** - Compares system state before and after hardening

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

### What to Expect

When everything is working, you'll see output like this:

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

If you see warnings (like SSH tests), that's usually fine - they might just need SSH keys set up. Failures are what you need to investigate.

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

Before running data flow tests, make sure:
- PostgreSQL is running on VM-02 (check with `systemctl status postgresql`)
- You have the database password set as an environment variable
- The virtual environment has psycopg2 installed (it should be there if you installed from requirements.txt)

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

## Understanding the Results

### What the Symbols Mean

- **✓ (PASS)**: Everything worked as expected
- **✗ (FAIL)**: Something broke - you need to fix this
- **⚠ (WARN)**: It worked, but there's something to be aware of (like a service that's not running but isn't critical)

Don't panic if you see warnings - they're usually informational. Failures are what need your attention.

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

Here's what we've found works well:

1. **Run tests after changes** - Any time you modify network settings, firewall rules, or service configurations, run the tests. It's quick and catches problems early.

2. **Keep test results** - The JSON files are timestamped, so you can compare results over time. This is especially useful when troubleshooting "it worked yesterday" issues.

3. **Test before and after hardening** - The `test_before_after_hardening.sh` script is specifically designed for this. It saves you from wondering if a problem existed before or was introduced by hardening.

4. **Document what you fixed** - If a test fails and you fix it, make a note. Someone else (or future you) might hit the same issue.

5. **Automate if possible** - If you're setting up CI/CD, these tests are perfect candidates. They're fast and catch real problems.

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

