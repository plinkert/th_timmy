# Schemas Module

This directory contains JSON schemas used for validation of data structures throughout the Threat Hunting Automation Lab system.

## Overview

Schemas provide standardized structure definitions and validation rules for key data structures in the system, ensuring data consistency and integrity.

## Schemas

### `data_package_schema.json`

JSON schema for DataPackage structure validation.

Defines the structure for:
- Package metadata (package_id, created_at, version, source_type, etc.)
- Query information (query_id, technique_id, playbook_id)
- Data records array
- Validation rules and required fields

**Usage:**
```python
from automation_scripts.utils.data_package import DataPackage

package = DataPackage(...)
# Schema validation happens automatically during package creation
is_valid = package.validate()  # Uses data_package_schema.json
```

### `playbook_schema.json`

JSON schema for playbook metadata.yml validation.

Defines the structure for:
- Playbook metadata (id, name, description, author, etc.)
- MITRE ATT&CK information (technique_id, tactic, etc.)
- Data sources and queries
- Hypothesis and analysis logic

**Usage:**
```python
from automation_scripts.utils.playbook_validator import PlaybookValidator

validator = PlaybookValidator()
# Schema validation happens during playbook validation
result = validator.validate_playbook("T1566-phishing")
```

### `findings_schema.json`

JSON schema for findings structure validation.

Defines the structure for:
- Finding metadata (finding_id, timestamp, severity, etc.)
- Evidence and indicators
- Related events
- Analysis results

**Usage:**
```python
# Schema is used internally by playbook engine and analysis modules
# for validating findings structure
```

## Schema Validation

All schemas use JSON Schema Draft 7 specification and are validated using the `jsonschema` library.

## Schema Updates

When updating schemas:
1. Maintain backward compatibility when possible
2. Update version numbers in schema files
3. Update validation code in corresponding modules
4. Update documentation
5. Test with existing data

## Integration

Schemas are used by:
- `DataPackage` class for package validation
- `PlaybookValidator` for playbook validation
- `PlaybookEngine` for findings validation
- API endpoints for request/response validation

## Schema Structure

All schemas follow JSON Schema Draft 7 format:
- `$schema`: Schema specification version
- `type`: Root type (usually "object")
- `properties`: Object properties definitions
- `required`: List of required properties
- `definitions`: Reusable schema definitions

