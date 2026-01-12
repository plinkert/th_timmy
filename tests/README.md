# Test Suite - Threat Hunting Lab

## Overview

This directory contains the test suite for Phase 0-01: Remote Execution Service.

## Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_ssh_client.py
│   └── test_remote_executor.py
├── integration/            # Integration tests
│   ├── test_remote_execution_integration.py
│   └── test_remote_api.py
└── fixtures/               # Test fixtures and utilities
```

## Test Coverage

### Phase 0-01: Remote Execution Service

#### Unit Tests
- **TC-0-01-01**: Basic command execution
- **TC-0-01-02**: Remote VM script execution
- **TC-0-01-03**: File upload
- **TC-0-01-04**: File download
- **TC-0-01-05**: Command timeout
- **TC-0-01-06**: Invalid command
- **TC-0-01-07**: SSH security

#### Integration Tests
- **TS-0-01-01**: Sequential execution of multiple commands
- **TS-0-01-02**: Parallel command execution

#### API Tests
- REST API endpoints testing
- Health check
- Command execution via API
- File operations via API

## Running Tests

### Prerequisites

1. **Configuration**: Ensure `configs/config.yml` exists with valid VM configurations
2. **SSH Access**: SSH key or password must be configured for VM access
3. **VM Connectivity**: All VMs must be reachable from test machine

### Install Dependencies

```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio httpx
```

### Run All Tests

```bash
# From project root
pytest tests/
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_remote_executor.py

# Specific test case
pytest tests/unit/test_remote_executor.py::TestBasicCommandExecution::test_execute_simple_command
```

### Run with Coverage

```bash
pytest --cov=automation_scripts --cov-report=html --cov-report=term tests/
```

### Run with Verbose Output

```bash
pytest -v -s tests/
```

## Test Configuration

### Environment Variables

- `SSH_KEY_PATH`: Path to SSH private key (optional, will use default locations if not set)
- `SSH_PASSWORD`: SSH password (fallback if key not available)
- `CONFIG_PATH`: Path to config.yml (defaults to `configs/config.yml`)

### Test Fixtures

Fixtures are defined in `conftest.py`:

- `test_config`: Loads configuration from config.yml
- `vm_configs`: Extracts VM configurations
- `ssh_key_path`: Finds SSH key path
- `remote_executor`: Creates RemoteExecutor instance
- `ssh_client_vm01/vm02/vm03`: Creates SSH clients for specific VMs
- `temp_dir`: Creates temporary directory for test files
- `test_file`: Creates test file with content
- `test_script`: Creates test bash script

## Test Data

Test data is generated dynamically:
- Test files are created in temporary directories
- Test scripts are generated on-the-fly
- Remote files are cleaned up after tests

## Skipping Tests

Tests will be automatically skipped if:
- VMs are not configured in config.yml
- SSH authentication is not available
- VMs are not reachable (connectivity check)

## Test Results

Test results are stored in:
- Console output (pytest default)
- Optional: HTML coverage report in `htmlcov/`
- Optional: JUnit XML report (with `--junitxml`)

## Troubleshooting

### Tests Skipped: "VM not configured"
- Ensure `configs/config.yml` exists and contains VM configurations
- Check that VM IDs match: vm01, vm02, vm03, vm04

### Tests Skipped: "No SSH key or password available"
- Set `SSH_KEY_PATH` environment variable
- Or set `SSH_PASSWORD` environment variable
- Or ensure default SSH keys exist in `~/.ssh/`

### Tests Failed: "VM not reachable"
- Check network connectivity to VMs
- Verify SSH port (default 22) is open
- Check firewall rules

### Import Errors
- Ensure you're running tests from project root
- Check that `automation-scripts` directory exists
- Verify Python path includes project root

## Writing New Tests

### Unit Test Template

```python
import pytest
from services.your_module import YourClass

class TestYourFeature:
    """Test description."""
    
    def test_feature_name(self, fixture_name):
        """Test case description."""
        # Arrange
        # Act
        # Assert
        assert condition
```

### Integration Test Template

```python
import pytest

class TestIntegrationFeature:
    """Integration test description."""
    
    def test_integration_scenario(self, remote_executor, skip_if_vm_unreachable):
        """Integration test case."""
        # Test integration between components
        pass
```

## Best Practices

1. **Use fixtures**: Leverage existing fixtures from `conftest.py`
2. **Clean up**: Always clean up remote files after tests
3. **Skip appropriately**: Use `skip_if_vm_unreachable` for tests requiring VM access
4. **Assert clearly**: Use descriptive assertion messages
5. **Test isolation**: Each test should be independent
6. **Error handling**: Test both success and failure cases

## Continuous Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ --junitxml=test-results.xml
```

## Support

For issues or questions:
- Check test logs for detailed error messages
- Review `PLAN_TESTOW.md` for test requirements
- Consult project documentation in `docs/`

