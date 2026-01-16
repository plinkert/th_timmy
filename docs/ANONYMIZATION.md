# Threat Hunting Lab - Anonymization Policy

## Table of Contents

1. [Overview](#overview)
2. [Anonymization Principles](#anonymization-principles)
3. [Anonymization Methods](#anonymization-methods)
4. [PII Detection](#pii-detection)
5. [Deterministic Anonymization](#deterministic-anonymization)
6. [Deanonymization](#deanonymization)
7. [Implementation](#implementation)
8. [Compliance and Security](#compliance-and-security)
9. [Best Practices](#best-practices)

## Overview

The Threat Hunting Lab implements a comprehensive anonymization policy to protect personally identifiable information (PII) while maintaining data utility for threat hunting operations. The system uses deterministic anonymization methods that allow authorized users to reverse the anonymization when necessary for investigation purposes.

### Objectives

- **Privacy Protection**: Protect PII in threat intelligence data
- **Data Utility**: Maintain data usefulness for threat hunting
- **Reversibility**: Enable authorized deanonymization when needed
- **Compliance**: Meet data protection and privacy requirements
- **Security**: Secure storage of anonymization mappings

## Anonymization Principles

### Core Principles

1. **Deterministic Anonymization**
   - Same input always produces same anonymized output
   - Enables correlation across datasets
   - Maintains referential integrity

2. **Reversible Anonymization**
   - Authorized users can reverse anonymization
   - Secure mapping storage
   - Audit logging of deanonymization operations

3. **Selective Anonymization**
   - Only PII fields are anonymized
   - Non-PII data remains unchanged
   - Configurable anonymization rules

4. **Security First**
   - Secure hash-based anonymization
   - Encrypted mapping storage
   - Access control for deanonymization

## Anonymization Methods

### Hash-Based Anonymization

**Method**: Cryptographic hash function (SHA-256) with salt

**Process**:
1. Identify PII field
2. Apply salt (system-wide secret)
3. Hash salted value
4. Store mapping (encrypted) for deanonymization
5. Replace original value with hash

**Example**:
```
Original IP: 192.168.1.100
Salt: system_secret_salt
Hash: SHA256("192.168.1.100" + salt)
Anonymized: a1b2c3d4e5f6...
```

**Properties**:
- Deterministic: Same input → same output
- One-way: Cannot reverse without mapping
- Collision-resistant: Different inputs → different outputs

### Field-Specific Anonymization

#### IP Addresses

**Method**: Hash-based anonymization with prefix preservation (optional)

**Options**:
- **Full Anonymization**: Complete hash replacement
- **Prefix Preservation**: Preserve network prefix (e.g., 192.168.x.x)

**Example**:
```
Original: 192.168.1.100
Anonymized (full): a1b2c3d4e5f6...
Anonymized (prefix): 192.168.x.x (with hash for host part)
```

#### User Identifiers

**Method**: Hash-based anonymization

**Fields**:
- Usernames
- User IDs
- Account names
- Email addresses

**Example**:
```
Original: john.doe@example.com
Anonymized: user_a1b2c3d4e5f6...
```

#### File Paths

**Method**: Path anonymization with structure preservation

**Process**:
1. Extract path components
2. Anonymize sensitive components (usernames, etc.)
3. Preserve path structure
4. Hash file names if sensitive

**Example**:
```
Original: C:\Users\john.doe\Documents\secret.txt
Anonymized: C:\Users\user_a1b2c3\Documents\file_d4e5f6...
```

#### Email Addresses

**Method**: Hash-based anonymization with domain preservation (optional)

**Options**:
- **Full Anonymization**: Complete hash replacement
- **Domain Preservation**: Preserve domain, hash local part

**Example**:
```
Original: john.doe@example.com
Anonymized (full): email_a1b2c3d4e5f6...
Anonymized (domain): user_a1b2c3@example.com
```

## PII Detection

### Automatic PII Detection

The system automatically detects PII in data fields using:

1. **Pattern Matching**:
   - IP address patterns
   - Email address patterns
   - Credit card patterns
   - SSN patterns
   - Phone number patterns

2. **Field Name Matching**:
   - Common PII field names (username, email, ip_address, etc.)
   - Configurable field name mappings

3. **Data Type Analysis**:
   - Format validation
   - Statistical analysis
   - Context-aware detection

### PII Categories

1. **Identifiers**:
   - Usernames
   - User IDs
   - Account names
   - Employee IDs

2. **Contact Information**:
   - Email addresses
   - Phone numbers
   - Physical addresses

3. **Network Information**:
   - IP addresses
   - MAC addresses
   - Hostnames (if contain PII)

4. **File Information**:
   - File paths with usernames
   - File names with PII

5. **Other PII**:
   - Credit card numbers
   - Social security numbers
   - Other sensitive identifiers

### PII Detection Configuration

```yaml
anonymization:
  pii_detection:
    enabled: true
    patterns:
      ip_address: true
      email: true
      phone: true
      credit_card: true
      ssn: true
    field_names:
      - username
      - user_id
      - email
      - ip_address
      - source_ip
      - destination_ip
```

## Deterministic Anonymization

### Deterministic Properties

**Same Input → Same Output**:
- Enables correlation across different datasets
- Maintains referential integrity
- Allows consistent analysis

**Example**:
```
Input: 192.168.1.100
Output: a1b2c3d4e5f6... (always the same)

Input: 192.168.1.100 (again)
Output: a1b2c3d4e5f6... (same as before)
```

### Use Cases

1. **Cross-Dataset Correlation**:
   - Correlate events across different time periods
   - Link events from different sources
   - Maintain entity relationships

2. **Consistent Analysis**:
   - Reproducible analysis results
   - Consistent reporting
   - Reliable threat hunting

3. **Data Integration**:
   - Merge data from multiple sources
   - Maintain entity consistency
   - Enable advanced analytics

### Implementation

**Hash Function**: SHA-256
**Salt**: System-wide secret (stored securely)
**Encoding**: Hexadecimal or Base64

```python
import hashlib
import os

def anonymize(value, salt):
    """Deterministic anonymization using SHA-256"""
    salted_value = f"{value}{salt}".encode('utf-8')
    hash_obj = hashlib.sha256(salted_value)
    return hash_obj.hexdigest()
```

## Deanonymization

### Deanonymization Process

**Authorized Access Only**:
- Restricted to authorized users
- Audit logging of all operations
- Secure mapping storage

**Process**:
1. User requests deanonymization
2. System verifies authorization
3. System retrieves mapping (decrypted)
4. System returns original value
5. System logs deanonymization operation

### Access Control

**Authorization Levels**:
- **Level 1**: View anonymized data only
- **Level 2**: Deanonymize specific fields (with approval)
- **Level 3**: Full deanonymization access (admin only)

**Approval Workflow**:
- Request deanonymization
- Approval from authorized personnel
- Time-limited access
- Audit logging

### Mapping Storage

**Storage Location**: Encrypted database table
**Encryption**: AES-256 encryption
**Access Control**: Role-based access control
**Backup**: Included in regular backups (encrypted)

**Mapping Table Structure**:
```sql
CREATE TABLE anonymization_mappings (
    id SERIAL PRIMARY KEY,
    original_value TEXT NOT NULL,
    anonymized_value TEXT NOT NULL,
    field_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    encrypted BOOLEAN DEFAULT TRUE
);
```

### Audit Logging

**Logged Information**:
- User identifier
- Timestamp
- Field deanonymized
- Reason for deanonymization
- Approval information

**Log Retention**: 90 days (same as data retention)

## Implementation

### Implementation Locations

1. **VM-01 (Normalizers)**: Initial anonymization during normalization
2. **VM-02 (Database)**: Mapping storage and retrieval
3. **VM-03 (Analysis)**: Deanonymization for authorized users

### Anonymization Module

**Location**: `automation-scripts/normalizers/anonymization.py`

**Key Functions**:
- `detect_pii(data)`: Detect PII in data
- `anonymize_field(value, field_type)`: Anonymize a field
- `anonymize_data(data)`: Anonymize entire dataset
- `store_mapping(original, anonymized, field_type)`: Store mapping

### Deanonymization Module

**Location**: `automation-scripts/utils/deanonymization.py`

**Key Functions**:
- `request_deanonymization(anonymized_value, user)`: Request deanonymization
- `check_authorization(user, field_type)`: Check user authorization
- `retrieve_mapping(anonymized_value)`: Retrieve original value
- `log_deanonymization(user, field, reason)`: Log operation

### Configuration

**Anonymization Configuration**:
```yaml
anonymization:
  enabled: true
  method: "hash_based"
  hash_algorithm: "sha256"
  salt: "CHANGE_ME_SECRET_SALT"  # Store in .env
  preserve_prefixes: false
  preserve_domains: false
```

**Deanonymization Configuration**:
```yaml
deanonymization:
  enabled: true
  require_approval: true
  approval_timeout: 3600  # 1 hour
  audit_logging: true
```

## Compliance and Security

### Data Protection Compliance

- **GDPR**: Compliance with General Data Protection Regulation
- **CCPA**: Compliance with California Consumer Privacy Act
- **HIPAA**: Healthcare data protection (if applicable)
- **Other Regulations**: Configurable compliance rules

### Security Measures

1. **Encryption**:
   - Mapping storage encrypted (AES-256)
   - Salt stored securely (environment variable)
   - Transport encryption (TLS/SSL)

2. **Access Control**:
   - Role-based access control
   - Multi-factor authentication (optional)
   - Time-limited access tokens

3. **Audit Trail**:
   - Complete audit logging
   - Immutable logs
   - Regular audit reviews

4. **Secure Storage**:
   - Encrypted database
   - Secure key management
   - Regular security audits

### Data Retention

- **Anonymized Data**: 90-day retention (same as original data)
- **Mapping Data**: Retained for same period as anonymized data
- **Audit Logs**: 90-day retention
- **Backup**: Included in regular backups (encrypted)

## Best Practices

### Anonymization Best Practices

1. **Comprehensive PII Detection**:
   - Use multiple detection methods
   - Regular pattern updates
   - Context-aware detection

2. **Consistent Anonymization**:
   - Use deterministic methods
   - Maintain salt consistency
   - Document anonymization rules

3. **Secure Mapping Storage**:
   - Encrypt mappings
   - Limit access
   - Regular security audits

4. **Documentation**:
   - Document anonymization methods
   - Maintain mapping documentation
   - Update procedures regularly

### Deanonymization Best Practices

1. **Access Control**:
   - Implement strict authorization
   - Require approvals for sensitive data
   - Time-limited access

2. **Audit Logging**:
   - Log all operations
   - Regular audit reviews
   - Alert on suspicious activity

3. **Data Minimization**:
   - Deanonymize only necessary fields
   - Limit scope of access
   - Remove access when no longer needed

### Operational Best Practices

1. **Regular Reviews**:
   - Review anonymization effectiveness
   - Update detection patterns
   - Audit access controls

2. **Training**:
   - Train users on anonymization
   - Document procedures
   - Regular updates

3. **Incident Response**:
   - Plan for data breaches
   - Incident response procedures
   - Regular drills

## Troubleshooting

### Common Issues

1. **Inconsistent Anonymization**:
   - Check salt consistency
   - Verify hash algorithm
   - Review mapping storage

2. **PII Not Detected**:
   - Update detection patterns
   - Review field name mappings
   - Check configuration

3. **Deanonymization Failures**:
   - Verify authorization
   - Check mapping storage
   - Review audit logs

### Support

For issues or questions regarding anonymization:
- Review this documentation
- Check configuration files
- Review audit logs
- Contact system administrator

## References

- [Architecture Documentation](ARCHITECTURE_ENHANCED.md)
- [Data Flow Documentation](DATA_FLOW.md)
- [Configuration Guide](CONFIGURATION.md)
- [User Guide for Hunters](USER_GUIDE_HUNTER.md)
