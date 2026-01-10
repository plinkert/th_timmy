# Test Execution Guide - Phase 0-01

## Quick Start

### 1. Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio httpx

# Ensure config.yml exists
cp configs/config.example.yml configs/config.yml
# Edit configs/config.yml with your VM IPs
```

### 2. Configure SSH Access

Option A: SSH Key (Recommended)
```bash
# Ensure SSH key exists
ls ~/.ssh/id_rsa  # or id_ed25519

# Or set environment variable
export SSH_KEY_PATH=/path/to/your/key
```

Option B: SSH Password
```bash
export SSH_PASSWORD=your_password
```

### 3. Run Tests

```bash
# Run all tests
pytest tests/

# Or use helper script
./tests/run_tests.sh all

# Run specific test category
pytest tests/unit/
pytest tests/integration/

# Run with verbose output
pytest -v -s tests/

# Run with coverage
pytest --cov=automation-scripts --cov-report=html tests/
```

## Test Execution Order

### Recommended Execution Order

1. **Unit Tests First** (Fast, no VM required for some)
   ```bash
   pytest tests/unit/test_ssh_client.py -v
   ```

2. **Basic Integration Tests** (Require VM connectivity)
   ```bash
   pytest tests/integration/test_remote_execution_integration.py::TestSequentialCommandExecution -v
   ```

3. **Full Integration Tests**
   ```bash
   pytest tests/integration/ -v
   ```

4. **API Tests** (Require FastAPI test client)
   ```bash
   pytest tests/integration/test_remote_api.py -v
   ```

## Test Cases Coverage

### TC-0-01-01: Podstawowe wykonanie komendy
```bash
pytest tests/unit/test_remote_executor.py::TestBasicCommandExecution::test_execute_simple_command -v
```

### TC-0-01-02: Wykonanie skryptu na zdalnym VM
```bash
pytest tests/unit/test_remote_executor.py::TestScriptExecution::test_execute_remote_script -v
```

### TC-0-01-03: Upload pliku
```bash
pytest tests/unit/test_remote_executor.py::TestFileUpload::test_upload_file -v
```

### TC-0-01-04: Download pliku
```bash
pytest tests/unit/test_remote_executor.py::TestFileDownload::test_download_file -v
```

### TC-0-01-05: Timeout komendy
```bash
pytest tests/unit/test_remote_executor.py::TestCommandTimeout::test_command_timeout -v
```

### TC-0-01-06: Błędna komenda
```bash
pytest tests/unit/test_remote_executor.py::TestErrorHandling::test_nonexistent_command -v
```

### TC-0-01-07: Bezpieczeństwo SSH
```bash
pytest tests/unit/test_ssh_client.py::TestSSHSecurity -v
```

### TS-0-01-01: Wykonanie wielu komend sekwencyjnie
```bash
pytest tests/integration/test_remote_execution_integration.py::TestSequentialCommandExecution -v
```

### TS-0-01-02: Wykonanie komend równolegle
```bash
pytest tests/integration/test_remote_execution_integration.py::TestParallelCommandExecution -v
```

## Expected Results

### Success Criteria

- **Unit Tests**: 100% pass rate
- **Integration Tests**: ≥80% pass rate (network conditions may vary)
- **Execution Time**: 
  - Unit tests: < 30 seconds total
  - Integration tests: < 2 minutes total
  - Individual command: < 5 seconds

### Sample Output

```
tests/unit/test_remote_executor.py::TestBasicCommandExecution::test_execute_simple_command PASSED
tests/unit/test_remote_executor.py::TestFileUpload::test_upload_file PASSED
tests/integration/test_remote_execution_integration.py::TestSequentialCommandExecution::test_multiple_commands_sequential PASSED

======================== 15 passed, 2 skipped in 45.23s ========================
```

## Troubleshooting

### Issue: Tests Skipped - "VM not configured"
**Solution**: 
- Check `configs/config.yml` exists
- Verify VM IDs: vm01, vm02, vm03, vm04
- Ensure all VMs have `enabled: true`

### Issue: Tests Skipped - "No SSH key or password"
**Solution**:
```bash
# Check for default keys
ls ~/.ssh/id_rsa ~/.ssh/id_ed25519

# Or set environment variable
export SSH_KEY_PATH=/path/to/key
export SSH_PASSWORD=your_password
```

### Issue: Tests Failed - "Connection timeout"
**Solution**:
- Verify VM IPs in config.yml are correct
- Check network connectivity: `ping <VM_IP>`
- Verify SSH port is open: `nc -zv <VM_IP> 22`
- Check firewall rules

### Issue: Tests Failed - "Authentication failed"
**Solution**:
- Verify SSH key has correct permissions: `chmod 600 ~/.ssh/id_rsa`
- Check SSH key is added to VM: `ssh-copy-id user@VM_IP`
- Verify username in config.yml matches VM user

### Issue: Import Errors
**Solution**:
```bash
# Ensure you're in project root
cd /home/user/Desktop/TH/th_timmy

# Check Python path
python -c "import sys; print(sys.path)"

# Install dependencies
pip install -r requirements.txt
```

## Continuous Testing

### Watch Mode (if pytest-watch installed)
```bash
pip install pytest-watch
ptw tests/
```

### Run Tests on File Change
```bash
# Using entr (if installed)
find tests/ -name "*.py" | entr pytest tests/
```

## Test Reports

### Generate HTML Report
```bash
pytest --html=test_report.html --self-contained-html tests/
```

### Generate JUnit XML (for CI/CD)
```bash
pytest --junitxml=test_results.xml tests/
```

### Coverage Report
```bash
pytest --cov=automation-scripts --cov-report=html tests/
# Open htmlcov/index.html in browser
```

## Performance Benchmarks

Expected performance metrics:

| Test Type | Expected Time | Max Time |
|-----------|---------------|----------|
| Unit Tests | < 30s | 60s |
| Integration Tests | < 2min | 5min |
| Single Command | < 5s | 10s |
| File Upload | < 2s | 5s |
| File Download | < 2s | 5s |

## Next Steps

After successful test execution:

1. Review test coverage report
2. Fix any failing tests
3. Update documentation if needed
4. Proceed to next phase testing

