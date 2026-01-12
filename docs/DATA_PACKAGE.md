# Data Package - Standardized Data Structure

## Overview

The Data Package provides a standardized structure for threat hunting data that is independent of the data source (manual upload, API, file, database, stream). This ensures consistent data processing regardless of how the data was obtained.

## Purpose

- **Standardization**: Unified data structure regardless of source
- **Validation**: JSON schema-based validation ensures data integrity
- **Metadata**: Rich metadata for tracking data provenance
- **Usability**: Simple, intuitive API interface
- **Flexibility**: Supports various data sources and ingestion modes

## Structure

A Data Package consists of two main sections:

### 1. Metadata

Contains information about the package:

- **package_id**: Unique identifier for the package
- **created_at**: ISO 8601 timestamp when package was created
- **version**: Data package schema version
- **source_type**: Type of data source (`manual`, `api`, `file`, `database`, `stream`)
- **source_name**: Name/identifier of the data source
- **ingest_mode**: Mode of ingestion (`manual` or `api`)
- **query_info**: Information about the query used to obtain data
- **anonymization**: Anonymization information
- **validation**: Validation status and errors
- **statistics**: Package statistics (record count, time range, etc.)

### 2. Data

Array of normalized data records. Each record contains:

- **timestamp**: ISO 8601 timestamp of the event
- **source**: Data source identifier
- **event_type**: Type of event
- **raw_data**: Original raw data from source
- **normalized_fields**: Normalized/extracted fields

## Usage

### Creating a Data Package

```python
from automation_scripts.utils import DataPackage

# Create package from manual upload
package = DataPackage(
    source_type="manual",
    source_name="user_upload",
    ingest_mode="manual"
)

# Add normalized records
package.add_record({
    "timestamp": "2024-01-15T10:30:00Z",
    "source": "Microsoft Defender",
    "event_type": "ProcessCreated",
    "raw_data": {...},
    "normalized_fields": {
        "hostname": "server01",
        "process_name": "powershell.exe",
        "command_line": "powershell -enc ..."
    }
})
```

### Creating from API

```python
# Create package from API query
package = DataPackage(
    source_type="api",
    source_name="Microsoft Defender",
    ingest_mode="api",
    query_info={
        "query_id": "query_123",
        "query_text": "DeviceProcessEvents | where ...",
        "tool": "Microsoft Defender",
        "technique_id": "T1059",
        "time_range": "7d",
        "executed_at": "2024-01-15T10:00:00Z"
    }
)
```

### Validation

```python
# Validate package
is_valid = package.validate(strict=False)

if not is_valid:
    errors = package.metadata["validation"]["validation_errors"]
    warnings = package.metadata["validation"]["validation_warnings"]
    print(f"Errors: {errors}")
    print(f"Warnings: {warnings}")
```

### Saving and Loading

```python
# Save package to file
package.save("data/package_001.json")

# Load package from file
loaded_package = DataPackage.from_file("data/package_001.json")

# Convert to JSON string
json_str = package.to_json()

# Create from JSON string
package = DataPackage.from_json(json_str)
```

### Getting Summary

```python
# Get package summary
summary = package.get_summary()
print(f"Package ID: {summary['package_id']}")
print(f"Total Records: {summary['total_records']}")
print(f"Is Valid: {summary['is_valid']}")
```

## JSON Schema

The Data Package structure is validated against a JSON schema located at:
`automation-scripts/schemas/data_package_schema.json`

### Schema Validation

The schema ensures:

- Required fields are present
- Field types are correct
- Timestamps are in ISO 8601 format
- Enumerated values are valid
- Data structure is consistent

### Validation Errors

When validation fails, errors are stored in:
```python
package.metadata["validation"]["validation_errors"]
```

Warnings (non-critical issues) are stored in:
```python
package.metadata["validation"]["validation_warnings"]
```

## Source Types

### Manual

Data uploaded manually by user:

```python
package = DataPackage(
    source_type="manual",
    source_name="user_upload",
    ingest_mode="manual"
)
```

### API

Data obtained via API:

```python
package = DataPackage(
    source_type="api",
    source_name="Microsoft Defender",
    ingest_mode="api",
    query_info={...}
)
```

### File

Data loaded from file:

```python
package = DataPackage(
    source_type="file",
    source_name="log_file.csv",
    ingest_mode="manual"
)
```

### Database

Data loaded from database:

```python
package = DataPackage(
    source_type="database",
    source_name="PostgreSQL",
    ingest_mode="api"
)
```

### Stream

Data from streaming source:

```python
package = DataPackage(
    source_type="stream",
    source_name="Kafka",
    ingest_mode="api"
)
```

## Anonymization

Set anonymization information:

```python
package.set_anonymization_info(
    is_anonymized=True,
    method="deterministic",
    mapping_table_id="mapping_123"
)
```

## Statistics

Package statistics are automatically calculated:

```python
stats = package.metadata["statistics"]
print(f"Total Records: {stats['total_records']}")
print(f"Unique Sources: {stats['unique_sources']}")
print(f"Unique Event Types: {stats['unique_event_types']}")
print(f"Time Range: {stats['time_range']}")
```

## Integration

### With Query Generator

```python
from automation_scripts.utils import QueryGenerator, DataPackage

# Generate queries
query_gen = QueryGenerator()
queries = query_gen.generate_queries(
    technique_ids=["T1566"],
    tool_names=["Microsoft Defender"],
    mode="api"
)

# Create package with query info
package = DataPackage(
    source_type="api",
    source_name="Microsoft Defender",
    ingest_mode="api",
    query_info={
        "query_id": queries["queries"]["T1566"]["Microsoft Defender"]["query_id"],
        "query_text": queries["queries"]["T1566"]["Microsoft Defender"]["query"],
        "tool": "Microsoft Defender",
        "technique_id": "T1566"
    }
)
```

### With Anonymization

```python
from automation_scripts.utils import DeterministicAnonymizer, DataPackage

# Anonymize data before creating package
anonymizer = DeterministicAnonymizer(...)
anonymized_data = anonymizer.anonymize_batch(normalized_data)

# Create package with anonymized data
package = DataPackage(
    source_type="api",
    source_name="Microsoft Defender",
    data=anonymized_data
)

# Set anonymization info
package.set_anonymization_info(
    is_anonymized=True,
    method="deterministic",
    mapping_table_id=anonymizer.mapping_table_id
)
```

## Best Practices

1. **Always Validate**: Validate packages before processing
2. **Include Query Info**: When using API mode, include query information
3. **Set Anonymization**: If data is anonymized, set anonymization info
4. **Use Statistics**: Check statistics to understand data characteristics
5. **Save Packages**: Save packages for audit and reproducibility

## Error Handling

```python
from automation_scripts.utils import DataPackage, DataPackageError, DataPackageValidationError

try:
    package = DataPackage.from_file("data/package.json")
    package.validate(strict=True)
except DataPackageValidationError as e:
    print(f"Validation failed: {e}")
except DataPackageError as e:
    print(f"Package error: {e}")
```

## Examples

### Example 1: Manual Upload

```python
# User uploads CSV file
package = DataPackage(
    source_type="manual",
    source_name="user_upload_csv",
    ingest_mode="manual"
)

# Parse and normalize CSV data
for row in csv_data:
    normalized = normalize_record(row)
    package.add_record(normalized)

# Validate and save
package.validate()
package.save("data/manual_upload_001.json")
```

### Example 2: API Query

```python
# Execute API query
query_result = defender_api.execute_query(query_text)

# Create package
package = DataPackage(
    source_type="api",
    source_name="Microsoft Defender",
    ingest_mode="api",
    query_info={
        "query_text": query_text,
        "tool": "Microsoft Defender",
        "technique_id": "T1566",
        "executed_at": datetime.utcnow().isoformat()
    }
)

# Add query results
for record in query_result:
    normalized = normalize_defender_record(record)
    package.add_record(normalized)

# Validate and save
package.validate()
package.save("data/api_query_001.json")
```

## Schema Version

Current schema version: **1.0.0**

Schema version is stored in:
```python
package.metadata["version"]
```

## Future Enhancements

- Support for streaming data packages
- Compression for large packages
- Incremental package updates
- Package merging capabilities
- Version migration utilities

