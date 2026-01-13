# Findings and Evidence Structure

## Overview

The Findings and Evidence structure provides a comprehensive system for storing and managing threat hunting findings with references to supporting evidence. This structure supports both inline evidence (for backward compatibility) and separate evidence records with references.

## Purpose

- **Structured Storage**: Organized storage of findings with evidence references
- **Evidence Reusability**: Multiple findings can reference the same evidence
- **Data Integrity**: Foreign key relationships ensure data consistency
- **Query Performance**: Indexed tables and views for efficient queries
- **Schema Validation**: JSON schema for validating finding structure

## Database Schema

### Evidence Table

Stores evidence records separately from findings, allowing multiple findings to reference the same evidence.

**Key Fields:**
- `evidence_id`: Unique identifier
- `evidence_type`: Type of evidence (log_entry, file, process, network, registry, other)
- `source`: Data source
- `timestamp`: When the evidence was collected
- `raw_data`: Original raw data (JSONB)
- `normalized_fields`: Normalized fields (JSONB)
- `metadata`: Additional metadata (JSONB)

### Findings Table

Stores threat hunting findings with references to evidence.

**Key Fields:**
- `finding_id`: Unique identifier
- `playbook_id`: ID of the playbook that generated the finding
- `execution_id`: ID of the playbook execution
- `technique_id`: MITRE ATT&CK technique ID
- `technique_name`: MITRE ATT&CK technique name
- `tactic`: MITRE ATT&CK tactic
- `severity`: Severity level (low, medium, high, critical)
- `title`: Finding title
- `description`: Detailed description
- `confidence`: Confidence score (0.0 to 1.0)
- `status`: Status (new, investigating, confirmed, false_positive, resolved)
- `evidence_count`: Number of linked evidence records (auto-updated)
- `indicators`: Array of IOCs
- `recommendations`: Array of recommendations

### Finding_Evidence Junction Table

Junction table for many-to-many relationship between findings and evidence.

**Key Fields:**
- `finding_id`: Reference to finding
- `evidence_id`: Reference to evidence
- `relevance_score`: Relevance score (0.0 to 1.0)

## JSON Schema

The `findings_schema.json` defines the structure for findings:

```json
{
  "finding_id": "T1566_20240115_103000_5",
  "technique_id": "T1566",
  "technique_name": "Phishing",
  "tactic": "Initial Access",
  "severity": "high",
  "title": "Suspicious activity detected: Phishing",
  "description": "Detected 5 suspicious records matching Phishing patterns.",
  "confidence": 0.85,
  "timestamp": "2024-01-15T10:30:00Z",
  "source": "Microsoft Defender",
  "playbook_id": "T1566-phishing",
  "execution_id": "exec_20240115_103000",
  "evidence_references": [
    {
      "evidence_id": "evid_001",
      "evidence_type": "log_entry",
      "relevance_score": 0.9
    }
  ],
  "indicators": ["Process: powershell.exe", "Command: -enc ..."],
  "recommendations": ["Review all 5 suspicious records"],
  "status": "new"
}
```

## Usage

### Creating Findings

Findings are typically created by the Playbook Engine during analysis:

```python
from automation_scripts.orchestrators.playbook_engine import PlaybookEngine
from automation_scripts.utils.data_package import DataPackage

# Execute playbook
engine = PlaybookEngine()
result = engine.execute_playbook(
    playbook_id="T1566-phishing",
    data_package=data_package
)

# Findings are in result['findings']
findings = result['findings']
```

### Storing Findings in Database

```python
import psycopg2
from psycopg2.extras import Json

# Connect to database
conn = psycopg2.connect(
    host='vm02',
    database='threat_hunting',
    user='threat_hunter',
    password='password'
)
cur = conn.cursor()

# Insert finding
cur.execute("""
    INSERT INTO findings (
        finding_id, playbook_id, execution_id, technique_id,
        technique_name, tactic, severity, title, description,
        confidence, source, status, indicators, recommendations,
        timestamp, created_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
""", (
    finding['finding_id'],
    finding['playbook_id'],
    finding['execution_id'],
    finding['technique_id'],
    finding['technique_name'],
    finding['tactic'],
    finding['severity'],
    finding['title'],
    finding['description'],
    finding['confidence'],
    finding['source'],
    finding.get('status', 'new'),
    finding.get('indicators', []),
    finding.get('recommendations', []),
    finding['timestamp'],
    finding['timestamp']
))

conn.commit()
```

### Linking Evidence to Findings

```python
# Insert evidence
cur.execute("""
    INSERT INTO evidence (
        evidence_id, evidence_type, source, timestamp,
        raw_data, normalized_fields, metadata
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s
    )
""", (
    evidence['evidence_id'],
    evidence['evidence_type'],
    evidence['source'],
    evidence['timestamp'],
    Json(evidence['raw_data']),
    Json(evidence.get('normalized_fields', {})),
    Json(evidence.get('metadata', {}))
))

# Link evidence to finding
cur.execute("""
    INSERT INTO finding_evidence (
        finding_id, evidence_id, relevance_score
    ) VALUES (
        %s, %s, %s
    )
""", (
    finding['finding_id'],
    evidence['evidence_id'],
    evidence.get('relevance_score', 1.0)
))

conn.commit()
```

### Querying Findings with Evidence

```python
# Query findings with evidence summary
cur.execute("""
    SELECT * FROM findings_with_evidence_summary
    WHERE technique_id = %s AND severity = %s
    ORDER BY timestamp DESC
    LIMIT 100
""", ('T1566', 'high'))

findings = cur.fetchall()
```

## Views

### findings_with_evidence_summary

View that includes findings with evidence summary statistics:

- `linked_evidence_count`: Number of linked evidence records
- `avg_relevance_score`: Average relevance score of linked evidence

### evidence_with_findings

View that includes evidence with finding references:

- `referenced_by_findings_count`: Number of findings referencing this evidence
- `referenced_by_findings`: Array of finding IDs referencing this evidence

## Triggers

### Auto-update updated_at

Automatically updates `updated_at` timestamp when records are modified.

### Auto-update evidence_count

Automatically updates `evidence_count` in findings table when evidence links are added or removed.

## Indexes

Comprehensive indexing for performance:

- Primary keys and unique constraints
- Foreign key indexes
- JSONB GIN indexes for JSON fields
- Composite indexes for common queries
- Timestamp indexes for time-based queries

## Migration

To apply the schema updates:

```bash
# On VM02
psql -U threat_hunter -d threat_hunting -f schema_updates.sql
```

Or via remote execution:

```python
from automation_scripts.services.remote_executor import RemoteExecutor

executor = RemoteExecutor()
executor.upload_file(
    vm_id="vm02",
    local_path="hosts/vm02-database/schema_updates.sql",
    remote_path="/tmp/schema_updates.sql"
)

executor.execute_remote_command(
    vm_id="vm02",
    command="psql -U threat_hunter -d threat_hunting -f /tmp/schema_updates.sql"
)
```

## Integration

### With Playbook Engine

The Playbook Engine generates findings in the correct format:

```python
result = engine.execute_playbook(playbook_id, data_package)
findings = result['findings']  # Already in correct format
```

### With Data Package

Findings can reference evidence from DataPackage:

```python
# Evidence from DataPackage
for record in data_package.data:
    evidence_id = f"evid_{record.get('id', uuid.uuid4())}"
    # Store evidence and link to finding
```

## Best Practices

1. **Use Evidence References**: Store evidence separately and reference it from findings
2. **Set Relevance Scores**: Use relevance scores to indicate importance
3. **Update Status**: Keep finding status up to date
4. **Use Tags**: Tag findings for better organization
5. **Validate Schema**: Validate findings against JSON schema before storing

## Future Enhancements

- Evidence deduplication
- Evidence enrichment
- Automated evidence linking
- Evidence versioning
- Evidence retention policies

