# Threat Hunting Lab - Data Flow Documentation

## Table of Contents

1. [Overview](#overview)
2. [Data Collection Flow](#data-collection-flow)
3. [Data Processing Flow](#data-processing-flow)
4. [Data Storage Flow](#data-storage-flow)
5. [Data Analysis Flow](#data-analysis-flow)
6. [Data Retention Flow](#data-retention-flow)
7. [Backup Flow](#backup-flow)
8. [Anonymization Flow](#anonymization-flow)
9. [Data Formats](#data-formats)
10. [Error Handling](#error-handling)

## Overview

The Threat Hunting Lab processes threat intelligence data through multiple stages: collection, parsing, normalization, storage, analysis, and retention. This document describes the complete data flow through the system.

### Data Flow Stages

1. **Collection**: Data collection from external sources (EDR/SIEM)
2. **Parsing**: Parsing raw data into structured format
3. **Normalization**: Normalizing data to common schema
4. **Storage**: Storing normalized data in PostgreSQL
5. **Analysis**: Analyzing data using playbooks and AI/ML
6. **Retention**: Automated data cleanup after retention period
7. **Backup**: Automated backup operations

## Data Collection Flow

### Collection Sources

- **EDR Systems**: Endpoint Detection and Response systems
- **SIEM Systems**: Security Information and Event Management systems
- **API Endpoints**: RESTful APIs for data retrieval
- **File Imports**: Manual file imports (CSV, JSON, etc.)

### Collection Process

```
┌──────────────┐
│ External     │
│ Sources      │
│ (EDR/SIEM)   │
└──────┬───────┘
       │
       │ API Calls / File Imports
       │
       ▼
┌──────────────┐
│ VM-01        │
│ Collectors   │
│ Module       │
└──────┬───────┘
       │
       │ Raw Data
       │
       ▼
┌──────────────┐
│ Validation   │
│ & Logging    │
└──────────────┘
```

### Collection Components

**Location**: `automation-scripts/collectors/`

**Key Functions**:
- API authentication and connection management
- Data retrieval from external sources
- Rate limiting and error handling
- Initial data validation
- Collection logging

**Configuration**:
- API endpoints and credentials (stored in `.env`)
- Collection schedules (via n8n workflows)
- Rate limits and retry policies
- Data source-specific configurations

### Collection Data Format

**Input**: Raw data from external sources (varies by source)
**Output**: Raw structured data (JSON, CSV, or source-specific format)

## Data Processing Flow

### Parsing Stage

```
┌──────────────┐
│ Raw Data     │
│ (from        │
│ Collectors)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ VM-01        │
│ Parsers      │
│ Module       │
└──────┬───────┘
       │
       │ Parsed Data
       │
       ▼
┌──────────────┐
│ Structured   │
│ Data         │
└──────────────┘
```

**Location**: `automation-scripts/parsers/`

**Key Functions**:
- Format detection and parsing
- Field extraction and mapping
- Data type conversion
- Error handling for malformed data
- Parser-specific logging

**Supported Formats**:
- JSON
- CSV
- Syslog
- Windows Event Log
- Custom formats (extensible)

### Normalization Stage

```
┌──────────────┐
│ Parsed Data  │
│ (from        │
│ Parsers)     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ VM-01        │
│ Normalizers  │
│ Module       │
└──────┬───────┘
       │
       │ Normalized Data
       │
       ▼
┌──────────────┐
│ Common       │
│ Schema       │
└──────────────┘
```

**Location**: `automation-scripts/normalizers/`

**Key Functions**:
- Schema mapping to common format
- Field standardization
- Data type normalization
- PII detection and flagging
- Anonymization preparation

**Common Schema**:
- Timestamp (ISO 8601)
- Source system identifier
- Event type/category
- Source IP address
- Destination IP address
- User identifier
- Process/command information
- File information
- Network information
- Metadata fields

## Data Storage Flow

### Storage Process

```
┌──────────────┐
│ Normalized   │
│ Data         │
│ (from        │
│ Normalizers) │
└──────┬───────┘
       │
       │ Database Write
       │
       ▼
┌──────────────┐
│ VM-02        │
│ PostgreSQL   │
│ Database     │
└──────┬───────┘
       │
       │ Stored Data
       │
       ▼
┌──────────────┐
│ Tables:      │
│ - events     │
│ - metadata   │
│ - audit_logs │
└──────────────┘
```

### Storage Components

**Location**: VM-02 (PostgreSQL)

**Key Functions**:
- Data insertion with transaction management
- Index management for performance
- Constraint validation
- Storage logging
- Error handling and rollback

**Database Schema**:
- **events**: Main event data table
- **metadata**: Metadata and source information
- **audit_logs**: Audit trail for data operations
- **cleanup_log**: Retention cleanup operations log

### Storage Configuration

- **Connection Pooling**: Configurable pool size and overflow
- **Transaction Management**: ACID compliance
- **Indexing**: Automatic indexing on key fields
- **Constraints**: Data integrity constraints

## Data Analysis Flow

### Analysis Process

```
┌──────────────┐
│ VM-02        │
│ PostgreSQL   │
│ (Stored Data)│
└──────┬───────┘
       │
       │ SQL Queries
       │
       ▼
┌──────────────┐
│ VM-03        │
│ JupyterLab   │
│ Playbooks    │
└──────┬───────┘
       │
       │ Analysis Results
       │
       ▼
┌──────────────┐
│ AI/ML        │
│ Analysis     │
│ (Optional)   │
└──────┬───────┘
       │
       │ Enhanced Results
       │
       ▼
┌──────────────┐
│ Reports      │
│ Generation   │
└──────────────┘
```

### Analysis Components

**Location**: VM-03 (JupyterLab)

**Key Functions**:
- Playbook execution
- SQL query execution
- Data visualization
- AI/ML model integration
- Report generation

**Analysis Types**:
- **MITRE ATT&CK Mapping**: Mapping events to MITRE techniques
- **Anomaly Detection**: ML-based anomaly detection
- **Threat Correlation**: Correlating events across time and sources
- **Behavioral Analysis**: Analyzing user and system behaviors

### Playbook Execution

**Playbook Structure**:
- Hypothesis definition
- Data source identification
- Query construction
- Result analysis
- Report generation

**Playbook Types**:
- Hypothesis-based hunts
- Baseline hunts
- Model-assisted hunts

## Data Retention Flow

### Retention Process

```
┌──────────────┐
│ VM-02        │
│ PostgreSQL   │
│ (All Data)   │
└──────┬───────┘
       │
       │ Daily at 3:00 AM
       │
       ▼
┌──────────────┐
│ Retention    │
│ Manager      │
│ (cleanup_old │
│ _data())     │
└──────┬───────┘
       │
       │ Check Age
       │
       ▼
┌──────────────┐
│ Data > 90    │
│ Days Old?    │
└──────┬───────┘
       │
   Yes │ No
       │
       ▼         ┌──────────┐
┌──────────────┐ │ Keep     │
│ Delete Data  │ │ Data     │
└──────┬───────┘ └──────────┘
       │
       ▼
┌──────────────┐
│ Log Cleanup  │
│ Operation    │
│ (cleanup_log)│
└──────────────┘
```

### Retention Components

**Location**: VM-02 (PostgreSQL)

**Key Functions**:
- Age calculation for data records
- Automated cleanup execution
- Cleanup logging
- Retention policy enforcement

**Retention Policy**:
- **Default**: 90 days
- **Configurable**: Per-table retention policies
- **Schedule**: Daily at 3:00 AM (configurable)
- **Logging**: All cleanup operations logged

### Retention Configuration

```yaml
retention:
  retention_days: 90          # Retention period
  auto_cleanup: true           # Enable automatic cleanup
  cleanup_schedule: "0 3 * * *"  # Cron schedule
  log_cleanup: true           # Log cleanup operations
```

## Backup Flow

### Backup Process

```
┌──────────────┐
│ VM-02        │
│ PostgreSQL   │
│ (Database)   │
└──────┬───────┘
       │
       │ Daily at 2:00 AM
       │
       ▼
┌──────────────┐
│ Backup       │
│ Manager      │
│ (pg_dump)    │
└──────┬───────┘
       │
       │ Create Backup
       │
       ▼
┌──────────────┐
│ Backup File  │
│ (timestamped) │
└──────┬───────┘
       │
       │ Store Backup
       │
       ▼
┌──────────────┐
│ Backup       │
│ Storage      │
│ (/var/backups│
│ /threat-     │
│ hunting)     │
└──────┬───────┘
       │
       │ Rotate Old Backups
       │
       ▼
┌──────────────┐
│ Remove       │
│ Backups > 30 │
│ Days Old     │
└──────────────┘
```

### Backup Components

**Location**: VM-02 (PostgreSQL)

**Key Functions**:
- Database backup creation (pg_dump)
- Backup file management
- Backup rotation
- Backup verification

**Backup Policy**:
- **Schedule**: Daily at 2:00 AM
- **Retention**: 30 days
- **Format**: PostgreSQL dump format
- **Compression**: Optional compression

### Backup Configuration

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"  # Daily at 2:00 AM
  retention_days: 30      # Keep backups for 30 days
  backup_dir: "/var/backups/threat-hunting"
```

## Anonymization Flow

### Anonymization Process

```
┌──────────────┐
│ Raw Data     │
│ (with PII)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ PII Detection│
│ Module       │
└──────┬───────┘
       │
       │ PII Identified
       │
       ▼
┌──────────────┐
│ Anonymization│
│ Module       │
│ (Deterministic│
│ Hash-based)  │
└──────┬───────┘
       │
       │ Anonymized Data
       │
       ▼
┌──────────────┐
│ Mapping      │
│ Storage      │
│ (for         │
│ deanonymization)│
└──────┬───────┘
       │
       │ Store Mapping
       │
       ▼
┌──────────────┐
│ Anonymized   │
│ Data to DB   │
└──────────────┘
```

### Anonymization Components

**Location**: VM-01 (Normalizers) and VM-03 (Analysis)

**Key Functions**:
- PII detection and identification
- Deterministic anonymization
- Hash-based mapping creation
- Secure mapping storage
- Deanonymization (authorized users only)

**Anonymization Methods**:
- **IP Addresses**: Hash-based anonymization
- **User Identifiers**: Hash-based anonymization
- **Email Addresses**: Hash-based anonymization
- **File Paths**: Path anonymization
- **Other PII**: Configurable anonymization rules

See [ANONYMIZATION.md](ANONYMIZATION.md) for detailed anonymization policy.

## Data Formats

### Input Formats

- **JSON**: Structured JSON data from APIs
- **CSV**: Comma-separated values
- **Syslog**: Standard syslog format
- **Windows Event Log**: Windows event log format
- **Custom Formats**: Extensible parser support

### Internal Format

**Normalized Schema** (JSON-like structure):
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "source_system": "edr_system_1",
  "event_type": "process_execution",
  "source_ip": "192.168.1.100",
  "destination_ip": "192.168.1.200",
  "user_id": "user123",
  "process_name": "cmd.exe",
  "command_line": "whoami",
  "file_path": "C:\\Windows\\System32\\cmd.exe",
  "metadata": {
    "anonymized": true,
    "pii_fields": ["user_id", "source_ip"]
  }
}
```

### Output Formats

- **JSON**: Analysis results in JSON format
- **CSV**: Tabular data export
- **XLSX**: Excel-compatible format
- **Reports**: Formatted reports (PDF, HTML)

## Error Handling

### Error Handling Strategy

1. **Collection Errors**:
   - Retry with exponential backoff
   - Log errors for investigation
   - Continue with other sources

2. **Parsing Errors**:
   - Log malformed data
   - Skip invalid records
   - Continue processing

3. **Normalization Errors**:
   - Log normalization failures
   - Use default values where appropriate
   - Flag data quality issues

4. **Storage Errors**:
   - Transaction rollback on errors
   - Log database errors
   - Alert on critical failures

5. **Analysis Errors**:
   - Log analysis failures
   - Continue with other analyses
   - Report errors in results

### Error Logging

- **Structured Logging**: JSON-formatted logs
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Rotation**: Automatic log rotation
- **Centralized Logging**: Optional centralized logging

### Monitoring and Alerting

- **Health Checks**: Automated health monitoring
- **Error Alerts**: Critical error notifications
- **Performance Monitoring**: Query performance tracking
- **Capacity Monitoring**: Storage capacity alerts

## Performance Considerations

### Data Volume

- **Collection Rate**: Configurable rate limits
- **Processing Throughput**: Batch processing for efficiency
- **Storage Capacity**: 90-day retention keeps size manageable
- **Query Performance**: Indexed queries for fast retrieval

### Optimization Strategies

- **Batch Processing**: Process data in batches
- **Connection Pooling**: Reuse database connections
- **Indexing**: Strategic database indexing
- **Caching**: Cache frequently accessed data
- **Parallel Processing**: Parallel processing where possible

## References

- [Architecture Documentation](ARCHITECTURE_ENHANCED.md)
- [Anonymization Policy](ANONYMIZATION.md)
- [Configuration Guide](CONFIGURATION.md)
- [User Guide for Hunters](USER_GUIDE_HUNTER.md)
