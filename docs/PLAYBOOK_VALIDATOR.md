# Playbook Validator

## Overview

The Playbook Validator provides comprehensive validation of threat hunting playbooks to ensure they are correctly structured and ready for use. It validates directory structure, metadata.yml files, required files, and query syntax.

## Purpose

- **Structure Validation**: Ensures playbooks follow the correct directory structure
- **Metadata Validation**: Validates metadata.yml against JSON schema
- **File Validation**: Checks for required files and directories
- **Query Validation**: Basic syntax validation for query files
- **User-Friendly**: Clear error messages and warnings

## Features

### 1. Directory Structure Validation

Validates that playbooks have the correct directory structure:

**Required Directories:**
- `queries/` - Query files directory

**Optional Directories:**
- `scripts/` - Python scripts
- `config/` - Configuration files
- `tests/` - Test files
- `examples/` - Example data

### 2. Metadata Validation

Validates `metadata.yml` file:

- **YAML Syntax**: Checks for valid YAML syntax
- **Schema Validation**: Validates against JSON schema
- **Required Fields**: Checks for required fields (playbook, mitre, hypothesis, data_sources)
- **Field Formats**: Validates format of IDs, dates, versions
- **Query References**: Validates that referenced query files exist

### 3. Required Files Validation

Checks for required files:

- `metadata.yml` - Playbook metadata
- `README.md` - Playbook documentation

### 4. Query File Validation

Validates query files:

- **File Existence**: Checks that query files referenced in metadata exist
- **File Type**: Validates file extensions (.kql, .spl, .json, .txt)
- **Syntax Validation**: Basic syntax checks for JSON, KQL, SPL
- **Content Validation**: Checks that files are not empty

## Usage

### Basic Usage

```python
from automation_scripts.utils import PlaybookValidator

# Initialize validator
validator = PlaybookValidator()

# Validate a single playbook
is_valid, errors, warnings = validator.validate_playbook("playbooks/T1566-phishing")

if is_valid:
    print("Playbook is valid!")
else:
    print(f"Validation failed with {len(errors)} error(s)")
    for error in errors:
        print(f"  - {error}")
```

### Validate All Playbooks

```python
# Validate all playbooks
results = validator.validate_all_playbooks()

# Get summary
summary = validator.get_validation_summary(results)
print(f"Total playbooks: {summary['total_playbooks']}")
print(f"Valid: {summary['valid']}")
print(f"Invalid: {summary['invalid']}")
print(f"Total errors: {summary['total_errors']}")
print(f"Total warnings: {summary['total_warnings']}")

# Check individual results
for playbook_id, result in results.items():
    if not result['is_valid']:
        print(f"\n{playbook_id}:")
        for error in result['errors']:
            print(f"  ERROR: {error}")
        for warning in result['warnings']:
            print(f"  WARNING: {warning}")
```

### Strict Mode

```python
# Raise exception on validation failure
try:
    validator.validate_playbook("playbooks/T1566-phishing", strict=True)
except PlaybookValidationError as e:
    print(f"Validation failed: {e}")
```

## Validation Checks

### Directory Structure

- ✅ Required directories exist
- ✅ Required directories are actually directories
- ⚠️ Optional directories structure (warnings only)

### Metadata.yml

- ✅ Valid YAML syntax
- ✅ Required fields present
- ✅ Field formats correct (IDs, dates, versions)
- ✅ MITRE technique ID format (T#### or T####.###)
- ✅ Playbook ID format (recommended: T####-name)
- ✅ Query file references exist
- ⚠️ API endpoint format (warnings)

### Required Files

- ✅ `metadata.yml` exists
- ✅ `README.md` exists

### Query Files

- ✅ Query files referenced in metadata exist
- ✅ Query files are not empty
- ✅ File extensions are recognized
- ✅ JSON syntax valid (for .json files)
- ⚠️ KQL/SPL syntax patterns (warnings)

## Error Messages

### Structure Errors

```
Required directory not found: queries/
Required file not found: metadata.yml
```

### Metadata Errors

```
Invalid YAML syntax in metadata.yml: ...
Schema validation failed: ...
Invalid MITRE technique ID format: T123
Query file not found: queries/microsoft_defender_manual.kql
```

### Query Errors

```
queries/defender.kql: Query file is empty
queries/query.json: Invalid JSON syntax: ...
```

## Warning Messages

### Structure Warnings

```
Optional path is not a directory: scripts/
```

### Metadata Warnings

```
Playbook ID 'playbook-1' does not follow recommended format (e.g., 'T1566-phishing')
API endpoint does not start with http:// or https://: api.example.com/query
```

### Query Warnings

```
queries/defender.kql: Unknown query file extension: .kql
queries/query.kql: KQL query may be missing common operators
queries/query.spl: SPL query may be missing common commands
No query files found in queries/ directory
```

## JSON Schema

The validator uses a JSON schema located at:
`automation-scripts/schemas/playbook_schema.json`

The schema validates:

- **playbook**: Playbook metadata (id, name, version, author, dates, description)
- **mitre**: MITRE ATT&CK information (technique_id, technique_name, tactic, sub_techniques)
- **hypothesis**: Threat hunting hypothesis
- **data_sources**: Data sources with queries (manual and API)
- **inputs**: Input parameters
- **outputs**: Output definitions
- **dependencies**: Dependencies (Python packages)

## Integration

### With Query Generator

```python
from automation_scripts.utils import PlaybookValidator, QueryGenerator

# Validate playbook first
validator = PlaybookValidator()
is_valid, errors, warnings = validator.validate_playbook("playbooks/T1566-phishing")

if is_valid:
    # Use with Query Generator
    query_gen = QueryGenerator()
    queries = query_gen.generate_queries(
        technique_ids=["T1566"],
        tool_names=["Microsoft Defender"]
    )
```

### With CI/CD

```python
# In CI/CD pipeline
validator = PlaybookValidator()
results = validator.validate_all_playbooks()

summary = validator.get_validation_summary(results)
if summary['invalid'] > 0:
    print("Validation failed!")
    exit(1)
```

## Best Practices

1. **Validate Before Use**: Always validate playbooks before using them
2. **Fix Errors First**: Address errors before warnings
3. **Check Warnings**: Review warnings for potential issues
4. **Use Strict Mode**: Use strict mode in automated environments
5. **Regular Validation**: Validate all playbooks regularly

## Examples

### Example 1: Validate Single Playbook

```python
from automation_scripts.utils import PlaybookValidator

validator = PlaybookValidator()
is_valid, errors, warnings = validator.validate_playbook("playbooks/T1566-phishing")

if not is_valid:
    print("Errors:")
    for error in errors:
        print(f"  - {error}")
    
    print("\nWarnings:")
    for warning in warnings:
        print(f"  - {warning}")
```

### Example 2: Validate All Playbooks

```python
from automation_scripts.utils import PlaybookValidator

validator = PlaybookValidator()
results = validator.validate_all_playbooks()

summary = validator.get_validation_summary(results)
print(f"Validation Summary:")
print(f"  Total: {summary['total_playbooks']}")
print(f"  Valid: {summary['valid']}")
print(f"  Invalid: {summary['invalid']}")
print(f"  Errors: {summary['total_errors']}")
print(f"  Warnings: {summary['total_warnings']}")
```

### Example 3: CI/CD Integration

```python
from automation_scripts.utils import PlaybookValidator, PlaybookValidationError

validator = PlaybookValidator()

try:
    results = validator.validate_all_playbooks(strict=True)
    summary = validator.get_validation_summary(results)
    
    if summary['invalid'] > 0:
        print("❌ Playbook validation failed!")
        for playbook_id, result in results.items():
            if not result['is_valid']:
                print(f"\n{playbook_id}:")
                for error in result['errors']:
                    print(f"  ERROR: {error}")
        exit(1)
    else:
        print("✅ All playbooks are valid!")
        
except PlaybookValidationError as e:
    print(f"❌ Validation error: {e}")
    exit(1)
```

## Error Handling

```python
from automation_scripts.utils import (
    PlaybookValidator,
    PlaybookValidatorError,
    PlaybookValidationError
)

try:
    validator = PlaybookValidator()
    is_valid, errors, warnings = validator.validate_playbook("playbooks/T1566-phishing", strict=True)
except PlaybookValidationError as e:
    print(f"Validation failed: {e}")
except PlaybookValidatorError as e:
    print(f"Validator error: {e}")
```

## Future Enhancements

- Advanced query syntax validation
- Query performance analysis
- Metadata completeness scoring
- Automated fix suggestions
- Integration with playbook creation tools

