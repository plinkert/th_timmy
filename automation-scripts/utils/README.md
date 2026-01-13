# Utils Module

This directory contains utility modules that provide helper functions and classes for various operations in the Threat Hunting Automation Lab system.

## Overview

Utilities are reusable components that provide common functionality used across multiple services and modules.

## Utilities

### `query_generator.py`

**QueryGenerator** - Automatic query generation for threat hunting.

Generates ready-to-use queries based on:
- Selected MITRE ATT&CK techniques
- Available SIEM/EDR tools (Splunk, Sentinel, Defender, etc.)
- Playbook metadata
- User parameters (time range, severity, etc.)

**Usage:**
```python
from automation_scripts.utils.query_generator import QueryGenerator

generator = QueryGenerator()
queries = generator.generate_queries(
    technique_ids=["T1566", "T1059"],
    tool_names=["Microsoft Defender for Endpoint", "Splunk"],
    mode="manual",
    parameters={"time_range": "7d"}
)
```

### `playbook_validator.py`

**PlaybookValidator** - Playbook structure and content validation.

Validates:
- Directory structure
- metadata.yml syntax and content
- Required files presence
- Query file syntax

**Usage:**
```python
from automation_scripts.utils.playbook_validator import PlaybookValidator

validator = PlaybookValidator()
result = validator.validate_playbook("T1566-phishing")
if result.is_valid:
    print("Playbook is valid")
else:
    print(f"Errors: {result.errors}")
```

### `data_package.py`

**DataPackage** - Standardized data structure for threat hunting data.

Provides:
- Standardized structure independent of data source
- JSON schema validation
- Rich metadata tracking
- Data record management

**Usage:**
```python
from automation_scripts.utils.data_package import DataPackage

package = DataPackage(
    source_type="manual",
    source_name="splunk_export",
    data=[{"event_id": "123", "timestamp": "2025-01-12T10:00:00Z"}]
)
package.add_record({"event_id": "124", "timestamp": "2025-01-12T10:01:00Z"})
is_valid = package.validate()
```

### `deterministic_anonymizer.py`

**DeterministicAnonymizer** - Deterministic data anonymization with mapping table.

Features:
- Deterministic anonymization (same input = same output)
- Mapping table in PostgreSQL database
- Deanonymization capability
- In-memory cache for performance

**Usage:**
```python
from automation_scripts.utils.deterministic_anonymizer import DeterministicAnonymizer

anonymizer = DeterministicAnonymizer(db_config={
    "host": "10.0.0.11",
    "database": "threat_hunting",
    "user": "threat_hunter",
    "password": "password"
})
anonymized = anonymizer.anonymize("192.168.1.1", "ip")
original = anonymizer.deanonymize(anonymized, "ip")
```

### `query_templates.py`

**QueryTemplates** - Query templates for different tools.

Provides base query templates for:
- Microsoft Defender for Endpoint (KQL)
- Microsoft Sentinel (KQL)
- Splunk (SPL)
- Elasticsearch (KQL)
- Generic SIEM

**Usage:**
```python
from automation_scripts.utils.query_templates import QueryTemplates, QueryTool

templates = QueryTemplates()
query = templates.get_template(QueryTool.MICROSOFT_DEFENDER, "T1566")
```

### `git_manager.py`

**GitManager** - Git repository management utilities.

Provides:
- Repository status checking
- Branch management
- Pull operations
- Conflict detection

**Usage:**
```python
from automation_scripts.utils.git_manager import GitManager

git_mgr = GitManager(repo_path="/home/user/th_timmy")
status = git_mgr.get_status()
git_mgr.pull_latest()
```

### `config_validator.py`

**ConfigValidator** - Configuration validation utilities.

Validates:
- Configuration structure
- Required fields presence
- Value types and ranges
- Network configuration

**Usage:**
```python
from automation_scripts.utils.config_validator import ConfigValidator

validator = ConfigValidator()
is_valid, errors = validator.validate_config(config_dict)
```

### `config_backup.py`

**ConfigBackup** - Configuration backup management.

Provides:
- Automatic backup creation
- Backup versioning
- Backup restoration
- Backup listing

**Usage:**
```python
from automation_scripts.utils.config_backup import ConfigBackup

backup_mgr = ConfigBackup(config_path="configs/config.yml")
backup_name = backup_mgr.create_backup()
backup_mgr.restore_backup(backup_name)
```

### `alert_manager.py`

**AlertManager** - Alert management system.

Provides:
- Alert creation with severity levels
- Alert aggregation
- Alert history
- Alert notifications

**Usage:**
```python
from automation_scripts.utils.alert_manager import AlertManager, AlertLevel

alert_mgr = AlertManager()
alert_mgr.create_alert(
    level=AlertLevel.CRITICAL,
    message="VM01 is down",
    source="health_monitor"
)
```

### `security.py`

**DataAnonymizer** - Basic data anonymization utilities.

Provides simple anonymization functions for:
- IP addresses
- Email addresses
- Usernames
- File paths

**Usage:**
```python
from automation_scripts.utils.security import anonymize_data

anonymized = anonymize_data("192.168.1.1", "ip")
```

## Common Patterns

All utilities follow similar patterns:
- Optional logger parameter
- Comprehensive error handling
- Clear, documented interfaces
- Reusable across multiple services

## Error Handling

Utilities raise custom exceptions:
- `QueryGeneratorError` - Query generation errors
- `PlaybookValidatorError` - Playbook validation errors
- `DataPackageError` - Data package errors
- `DeterministicAnonymizerError` - Anonymization errors

## Dependencies

Utilities may depend on:
- External libraries (psycopg2, jsonschema, yaml)
- Services for database operations
- Configuration files

## Integration

Utilities are used by:
- Services in `services/`
- API endpoints in `api/`
- Orchestrators in `orchestrators/`
- n8n workflows

