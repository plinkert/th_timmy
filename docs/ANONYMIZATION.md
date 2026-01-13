# Data Anonymization Documentation

## Overview

The system provides two types of data anonymization:

1. **Deterministic Anonymization** (`DeterministicAnonymizer`): Deterministic anonymization with mapping table for deanonymization
2. **Basic Anonymization** (`DataAnonymizer`): Simple anonymization without database dependency

## Deterministic Anonymization

### Features

- **Deterministic**: Same input always produces same anonymized output
- **Mapping Table**: Stores mappings in PostgreSQL database for deanonymization
- **Cache**: In-memory cache for performance
- **Multiple Value Types**: Supports IP, email, username, hostname, and generic values
- **Deanonymization**: Can reverse anonymization using mapping table

### Usage

#### Basic Usage

```python
from automation_scripts.utils.deterministic_anonymizer import DeterministicAnonymizer

# Database configuration
db_config = {
    'host': '10.0.0.11',  # VM02 IP
    'port': 5432,
    'database': 'threat_hunting',
    'user': 'threat_hunter',
    'password': 'your_password'
}

# Initialize anonymizer
anonymizer = DeterministicAnonymizer(db_config=db_config)

# Anonymize a value
anonymized_ip = anonymizer.anonymize('192.168.1.100', value_type='ip')
# Returns: '10.123.45.67' (deterministic)

# Anonymize an email
anonymized_email = anonymizer.anonymize('user@example.com', value_type='email')
# Returns: 'user_abc12345@example.local' (deterministic)

# Deanonymize
original_ip = anonymizer.deanonymize(anonymized_ip, value_type='ip')
# Returns: '192.168.1.100'
```

#### Anonymize Records

```python
# Anonymize a single record
record = {
    'ip': '192.168.1.100',
    'email': 'user@example.com',
    'username': 'john.doe'
}

anonymized_record = anonymizer.anonymize_record(
    record,
    fields_to_anonymize=['ip', 'email', 'username']
)
# Returns: {
#     'ip': '10.123.45.67',
#     'email': 'user_abc12345@example.local',
#     'username': 'user_abc123456789'
# }

# Deanonymize record
original_record = anonymizer.deanonymize_record(
    anonymized_record,
    fields_to_deanonymize=['ip', 'email', 'username']
)
```

#### Batch Anonymization

```python
records = [
    {'ip': '192.168.1.100', 'user': 'john'},
    {'ip': '192.168.1.101', 'user': 'jane'}
]

anonymized_records = anonymizer.anonymize_batch(
    records,
    fields_to_anonymize=['ip', 'user']
)
```

#### Get Statistics

```python
stats = anonymizer.get_mapping_stats()
# Returns: {
#     'total_mappings': 1500,
#     'by_type': {
#         'ip': 500,
#         'email': 300,
#         'username': 700
#     },
#     'cache_size': 1000,
#     'cache_by_type': {...}
# }
```

### Value Types

Supported value types:

- **ip**: IP addresses (e.g., `192.168.1.100` → `10.123.45.67`)
- **email**: Email addresses (e.g., `user@example.com` → `user_abc12345@example.local`)
- **username**: Usernames (e.g., `john.doe` → `user_abc123456789`)
- **hostname**: Hostnames (e.g., `server01.example.com` → `host-abc12345.example.local`)
- **generic**: Generic values (e.g., `any_value` → `anon_abc1234567890123`)

### Database Schema

The anonymization mapping table is automatically created:

```sql
CREATE TABLE anonymization_mapping (
    id SERIAL PRIMARY KEY,
    original_hash VARCHAR(64) NOT NULL,
    original_value TEXT,
    anonymized_value VARCHAR(255) NOT NULL,
    value_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(original_hash, value_type)
);
```

### Security Considerations

1. **Original Values Storage**: Original values are stored in plain text in the database for deanonymization
   - Consider encrypting original values for additional security
   - Restrict database access to authorized users only
   - Use database-level encryption if available

2. **Access Control**: 
   - Limit access to mapping table
   - Use database roles and permissions
   - Audit access to mapping table

3. **Salt**: 
   - Use a strong, unique salt for deterministic hashing
   - Store salt securely
   - Rotate salt periodically if needed

## Basic Anonymization

### Features

- **No Database Dependency**: Works without database connection
- **Simple Methods**: Basic anonymization methods
- **Non-Deterministic**: Different runs may produce different results

### Usage

```python
from automation_scripts.utils.security import DataAnonymizer

# Initialize anonymizer
anonymizer = DataAnonymizer(salt='your_salt')

# Anonymize IP
anonymized_ip = anonymizer.anonymize_ip('192.168.1.100')
# Returns: '192.168.1.0' (last octet zeroed)

# Hash user ID
hashed_user = anonymizer.hash_user_id('john.doe')
# Returns: 'abc1234567890123' (first 16 chars of hash)

# Tokenize email
tokenized_email = anonymizer.tokenize_email('user@example.com')
# Returns: 'us***@example.com'

# Anonymize record
record = {'ip': '192.168.1.100', 'email': 'user@example.com'}
anonymized = anonymizer.anonymize_record(record)
```

## When to Use Which

### Use DeterministicAnonymizer when:

- You need to deanonymize data later
- You need consistent anonymization across multiple runs
- You're sending data to AI and need to reverse results
- You have database access (VM02)

### Use DataAnonymizer when:

- You don't need deanonymization
- You don't have database access
- You need simple, quick anonymization
- You're doing one-time anonymization

## Integration with AI

### Before AI Analysis

```python
# Anonymize data before sending to AI
anonymizer = DeterministicAnonymizer(db_config=db_config)
anonymized_data = anonymizer.anonymize_batch(
    sensitive_data,
    fields_to_anonymize=['ip', 'email', 'username']
)

# Send anonymized_data to AI
ai_results = ai_service.analyze(anonymized_data)
```

### After AI Analysis

```python
# Deanonymize AI results
deanonymized_results = anonymizer.deanonymize_record(
    ai_results,
    fields_to_deanonymize=['ip', 'email', 'username']
)

# Use deanonymized results in final report
generate_report(deanonymized_results)
```

## Best Practices

1. **Use DeterministicAnonymizer for AI workflows**: Ensures you can reverse anonymization
2. **Store original values securely**: Consider encryption for original values in mapping table
3. **Limit access to mapping table**: Use database permissions
4. **Use cache for performance**: Enable cache for frequently accessed mappings
5. **Monitor mapping table size**: Clean up old mappings if needed
6. **Use appropriate value types**: Helps generate realistic anonymized values

## Troubleshooting

### Database Connection Issues

```python
# Check database connection
try:
    anonymizer = DeterministicAnonymizer(db_config=db_config)
    stats = anonymizer.get_mapping_stats()
    print("✅ Connection successful")
except DeterministicAnonymizerError as e:
    print(f"❌ Connection failed: {e}")
```

### Cache Issues

```python
# Clear cache if needed
anonymizer.clear_cache()

# Reload cache
anonymizer._load_cache()
```

### Deanonymization Not Working

- Ensure original values are stored in mapping table
- Check that value_type matches
- Verify database connection
- Check cache if enabled

## Deanonymization Service

### Overview

The `Deanonymizer` service provides a high-level interface for deanonymizing data before generating reports. It uses `DeterministicAnonymizer` internally to reverse anonymization using the mapping table stored in PostgreSQL.

### Features

- **Finding Deanonymization**: Deanonymize individual findings with all related fields
- **Batch Deanonymization**: Deanonymize multiple findings at once
- **Evidence Deanonymization**: Deanonymize evidence records
- **Report Deanonymization**: Deanonymize complete reports
- **Text Deanonymization**: Deanonymize text fields containing anonymized values
- **Nested Structure Support**: Handles nested JSON structures

### Usage

#### Basic Usage

```python
from automation_scripts.utils.deanonymizer import Deanonymizer

# Initialize deanonymizer
deanonymizer = Deanonymizer(config_path='configs/config.yml')

# Deanonymize a finding
finding = {
    'finding_id': 'T1566_001',
    'ip': '10.123.45.67',  # Anonymized IP
    'username': 'user_abc123456789',  # Anonymized username
    'description': 'Activity from 10.123.45.67 by user_abc123456789'
}

deanonymized_finding = deanonymizer.deanonymize_finding(finding)
# Returns finding with original values restored:
# {
#     'finding_id': 'T1566_001',
#     'ip': '192.168.1.100',  # Original IP
#     'username': 'john.doe',  # Original username
#     'description': 'Activity from 192.168.1.100 by john.doe'
# }
```

#### Batch Deanonymization

```python
findings = [finding1, finding2, finding3]

deanonymized_findings = deanonymizer.deanonymize_findings(findings)
```

#### Evidence Deanonymization

```python
evidence = {
    'evidence_id': 'evd_001',
    'ip': '10.123.45.67',
    'raw_data': {
        'source_ip': '10.123.45.67',
        'username': 'user_abc123456789'
    }
}

deanonymized_evidence = deanonymizer.deanonymize_evidence(evidence)
```

#### Report Deanonymization

```python
report = {
    'findings': [finding1, finding2],
    'evidence': [evidence1, evidence2],
    'summary': 'Report summary with 10.123.45.67'
}

deanonymized_report = deanonymizer.deanonymize_report(report)
```

### Integration with Reporting

```python
from automation_scripts.utils.deanonymizer import Deanonymizer
from automation_scripts.utils.final_report_generator import FinalReportGenerator

# Deanonymize findings before reporting
deanonymizer = Deanonymizer(config_path='configs/config.yml')
deanonymized_findings = deanonymizer.deanonymize_findings(findings)

# Generate report with deanonymized data
report_generator = FinalReportGenerator(config_path='configs/config.yml')
report = report_generator.generate_final_report(
    findings=deanonymized_findings,
    deanonymize=False,  # Already deanonymized
    include_executive_summary=True
)
```

### Security Considerations

1. **Controlled Deanonymization**: Deanonymization should only be performed when generating reports for authorized stakeholders
2. **Access Control**: Limit access to deanonymization service
3. **Audit Logging**: Log all deanonymization operations
4. **Mapping Table Security**: Protect the anonymization mapping table with proper database permissions

## API Reference

### DeterministicAnonymizer

#### `__init__(db_config, db_connection, use_cache, hash_original, salt, logger)`
Initialize deterministic anonymizer.

#### `anonymize(value, value_type='generic') -> str`
Anonymize a single value.

#### `deanonymize(anonymized_value, value_type='generic') -> Optional[str]`
Deanonymize a value.

#### `anonymize_record(record, fields_to_anonymize, field_types) -> Dict`
Anonymize fields in a record.

#### `deanonymize_record(record, fields_to_deanonymize) -> Dict`
Deanonymize fields in a record.

#### `anonymize_batch(records, fields_to_anonymize, field_types) -> List[Dict]`
Anonymize a batch of records.

#### `get_mapping_stats() -> Dict`
Get mapping table statistics.

#### `clear_cache() -> None`
Clear in-memory cache.

### DataAnonymizer

#### `anonymize_ip(ip) -> str`
Anonymize IP address.

#### `hash_user_id(user_id) -> str`
Hash user ID.

#### `tokenize_email(email) -> str`
Tokenize email address.

#### `anonymize_record(record, fields_to_anonymize) -> Dict`
Anonymize fields in a record.

### Deanonymizer

#### `__init__(config_path, anonymizer, logger)`
Initialize deanonymizer service.

#### `deanonymize_finding(finding, fields_to_deanonymize) -> Dict`
Deanonymize a finding.

#### `deanonymize_findings(findings, fields_to_deanonymize) -> List[Dict]`
Deanonymize multiple findings.

#### `deanonymize_evidence(evidence, fields_to_deanonymize) -> Dict`
Deanonymize evidence.

#### `deanonymize_report(report, fields_to_deanonymize) -> Dict`
Deanonymize a complete report.

#### `deanonymize_text(text, value_types) -> str`
Deanonymize text containing anonymized values.

