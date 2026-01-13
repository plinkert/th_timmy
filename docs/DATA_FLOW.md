# Data Flow Documentation

## Overview

This document describes the complete data flow through the Threat Hunting Automation Lab system, from initial hunt selection through data ingestion, analysis, AI validation, and final reporting. It includes detailed diagrams and explanations for each stage of the pipeline.

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Flow Pipeline                          │
└─────────────────────────────────────────────────────────────────────┘

1. Hunt Selection (VM-04/n8n)
   │
   ├─▶ Select MITRE ATT&CK techniques
   ├─▶ Select SIEM/EDR tools
   └─▶ Generate queries
        │
        ▼
2. Query Generation (VM-04)
   │
   ├─▶ Generate queries for selected tools
   └─▶ Prepare queries for execution
        │
        ▼
3. Data Ingestion (VM-01) [Optional]
   │
   ├─▶ Execute queries via API (if API mode)
   ├─▶ Parse results
   └─▶ Normalize data
        │
        ▼
4. Data Storage (VM-02)
   │
   ├─▶ Store normalized data
   ├─▶ Anonymize sensitive data (if requested)
   └─▶ Store anonymization mappings
        │
        ▼
5. Playbook Execution (VM-03)
   │
   ├─▶ Load playbook
   ├─▶ Execute deterministic analysis
   └─▶ Generate findings
        │
        ▼
6. AI Review (VM-04) [Optional]
   │
   ├─▶ Anonymize findings (if not already anonymized)
   ├─▶ Send to AI for validation
   └─▶ Update finding status
        │
        ▼
7. Deanonymization (VM-04) [For Reporting]
   │
   ├─▶ Load anonymization mappings
   └─▶ Restore original values
        │
        ▼
8. Final Report Generation (VM-04)
   │
   ├─▶ Generate executive summary
   ├─▶ Create comprehensive report
   └─▶ Include deanonymized data
        │
        ▼
9. Report Delivery
```

## Detailed Data Flow Diagrams

### Stage 1: Hunt Selection and Query Generation

```
┌─────────────────────────────────────────────────────────────────┐
│  VM-04: n8n (Hunt Selection Form)                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  User Input:                                              │  │
│  │  - MITRE ATT&CK Techniques (T1566, T1059, etc.)          │  │
│  │  - Tools (Microsoft Defender, Sentinel, Splunk)          │  │
│  │  - Ingest Mode (Manual/API)                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Query Generator                                          │  │
│  │  - Load playbook metadata                                 │  │
│  │  - Generate queries for each tool                         │  │
│  │  - Format queries (KQL, SPL, etc.)                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Output: Generated Queries                                │  │
│  │  - Ready-to-use queries for each tool                     │  │
│  │  - Copy-paste format                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Data Structures**:
- Input: `{technique_ids: ["T1566"], tool_names: ["Microsoft Defender"], mode: "manual"}`
- Output: `{queries: [{tool: "Microsoft Defender", query: "DeviceProcessEvents | ..."}]}`

### Stage 2: Data Ingestion (Optional)

```
┌─────────────────────────────────────────────────────────────────┐
│  VM-01: Ingest/Parser                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Data Collection                                         │  │
│  │  - Execute queries via API (if API mode)                 │  │
│  │  - Or receive manual upload                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Parsing                                                  │  │
│  │  - Parse CSV, JSON, or tool-specific format             │  │
│  │  - Extract structured data                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Normalization                                            │  │
│  │  - Standardize field names                                │  │
│  │  - Normalize data types                                   │  │
│  │  - Create DataPackage structure                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Output: DataPackage                                      │  │
│  │  - Standardized data structure                           │  │
│  │  - Metadata included                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    Send to VM-02
```

**Data Structures**:
- Input: Raw data from EDR/SIEM or manual upload
- Output: `DataPackage` with standardized structure

### Stage 3: Data Storage with Anonymization

```
┌─────────────────────────────────────────────────────────────────┐
│  VM-02: Database                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Receive DataPackage                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Anonymization Decision                                   │  │
│  │  - Check if anonymization requested                       │  │
│  │  - If yes: Anonymize sensitive fields                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  DeterministicAnonymizer                                  │  │
│  │  - Anonymize IP addresses                                 │  │
│  │  - Anonymize email addresses                              │  │
│  │  - Anonymize usernames                                    │  │
│  │  - Store mappings in database                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Database Storage                                         │  │
│  │  - Store normalized_logs                                  │  │
│  │  - Store anonymization_mapping                            │  │
│  │  - Apply retention policy                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Data Structures**:
- Input: `DataPackage` with original data
- Anonymized: `DataPackage` with anonymized sensitive fields
- Mappings: Stored in `anonymization_mapping` table

### Stage 4: Playbook Execution

```
┌─────────────────────────────────────────────────────────────────┐
│  VM-03: Analysis/Jupyter                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Receive DataPackage (from VM-02)                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Playbook Engine                                          │  │
│  │  - Load playbook metadata                                 │  │
│  │  - Validate playbook structure                            │  │
│  │  - Load analyzer script                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Deterministic Analysis                                   │  │
│  │  - Execute playbook analyzer logic                        │  │
│  │  - Process data records                                   │  │
│  │  - Apply detection rules                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Findings Generation                                      │  │
│  │  - Create finding records                                 │  │
│  │  - Collect evidence                                       │  │
│  │  - Set severity and confidence                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Output: Findings & Evidence                              │  │
│  │  - List of findings                                       │  │
│  │  - Associated evidence                                    │  │
│  │  - Execution metadata                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    Send to VM-04
```

**Data Structures**:
- Input: `DataPackage` (anonymized)
- Output: `{findings: [...], evidence: [...], execution_metadata: {...}}`

### Stage 5: AI Review (Optional)

```
┌─────────────────────────────────────────────────────────────────┐
│  VM-04: Orchestrator (AI Review)                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Receive Findings                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Anonymization Check                                     │  │
│  │  - Check if findings already anonymized                  │  │
│  │  - If not: Anonymize before AI processing                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  AI Service (OpenAI)                                      │  │
│  │  - Prepare prompt with anonymized finding                │  │
│  │  - Send to OpenAI API                                    │  │
│  │  - Receive validation result                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Status Update                                            │  │
│  │  - Update finding status (valid/invalid/needs_review)    │  │
│  │  - Update confidence level                               │  │
│  │  - Update severity if needed                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Data Structures**:
- Input: Findings (potentially with original data)
- Anonymized: Findings with anonymized sensitive fields
- AI Output: `{validation_status: "valid", confidence: 0.95, ...}`
- Updated: Findings with updated status

### Stage 6: Deanonymization (For Reporting)

```
┌─────────────────────────────────────────────────────────────────┐
│  VM-04: Orchestrator (Deanonymization)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Receive Findings (Anonymized)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Deanonymizer Service                                    │  │
│  │  - Load anonymization mappings from VM-02                │  │
│  │  - Match anonymized values to original values            │  │
│  │  - Replace anonymized values with originals              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Output: Deanonymized Findings                            │  │
│  │  - Findings with original values restored                 │  │
│  │  - Evidence with original values                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Data Structures**:
- Input: Findings with anonymized values (e.g., `ip: "10.123.45.67"`)
- Output: Findings with original values (e.g., `ip: "192.168.1.100"`)

### Stage 7: Final Report Generation

```
┌─────────────────────────────────────────────────────────────────┐
│  VM-04: Orchestrator (Report Generation)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Receive Deanonymized Findings                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Executive Summary Generator                              │  │
│  │  - Generate AI-powered executive summary                  │  │
│  │  - Include key findings and statistics                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Final Report Generator                                   │  │
│  │  - Create comprehensive report structure                  │  │
│  │  - Include all findings with evidence                    │  │
│  │  - Add executive summary                                 │  │
│  │  - Format report (Markdown/JSON)                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Output: Final Report                                     │  │
│  │  - Markdown format                                        │  │
│  │  - JSON format                                            │  │
│  │  - Downloadable files                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Data Structures**:
- Input: Deanonymized findings
- Executive Summary: `{executive_summary: "...", key_findings: [...], statistics: {...}}`
- Final Report: Comprehensive report with all sections

## Complete End-to-End Data Flow

### Full Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Complete Data Flow Pipeline                        │
└─────────────────────────────────────────────────────────────────────┘

User (n8n Dashboard)
    │
    ├─▶ Select Techniques & Tools
    │
    ▼
VM-04: Query Generation
    │
    ├─▶ Generate Queries
    │
    ▼
[Optional: API Mode]
    │
    ▼
VM-01: Data Ingestion
    │
    ├─▶ Collect Data
    ├─▶ Parse Data
    └─▶ Normalize Data
         │
         ▼
VM-02: Data Storage
    │
    ├─▶ Anonymize Data (if requested)
    ├─▶ Store Data
    └─▶ Store Mappings
         │
         ▼
VM-03: Playbook Execution
    │
    ├─▶ Load Playbook
    ├─▶ Execute Analysis
    └─▶ Generate Findings
         │
         ▼
VM-04: AI Review (Optional)
    │
    ├─▶ Anonymize Findings
    ├─▶ AI Validation
    └─▶ Update Status
         │
         ▼
VM-04: Deanonymization (For Reporting)
    │
    ├─▶ Load Mappings
    └─▶ Restore Original Values
         │
         ▼
VM-04: Report Generation
    │
    ├─▶ Generate Executive Summary
    ├─▶ Create Final Report
    └─▶ Deliver Report
         │
         ▼
User: Final Report
```

## Data Structures at Each Stage

### Stage 1: Hunt Selection Output

```json
{
  "technique_ids": ["T1566", "T1059"],
  "tool_names": ["Microsoft Defender for Endpoint", "Splunk"],
  "mode": "manual",
  "queries": [
    {
      "tool": "Microsoft Defender for Endpoint",
      "technique_id": "T1566",
      "query": "DeviceProcessEvents | where ...",
      "format": "kql"
    }
  ]
}
```

### Stage 2: DataPackage Structure

```json
{
  "package_id": "pkg_abc123",
  "metadata": {
    "created_at": "2025-01-12T10:00:00Z",
    "source_type": "manual",
    "source_name": "splunk_export",
    "version": "1.0.0"
  },
  "query_info": {
    "query_id": "qry_xyz789",
    "technique_id": "T1566",
    "playbook_id": "T1566-phishing"
  },
  "data": [
    {
      "timestamp": "2025-01-12T09:00:00Z",
      "event_id": "evt_001",
      "ip": "192.168.1.100",
      "username": "john.doe",
      "action": "process_creation"
    }
  ]
}
```

### Stage 3: Anonymized DataPackage

```json
{
  "package_id": "pkg_abc123",
  "metadata": {
    "anonymized": true,
    "anonymization_timestamp": "2025-01-12T10:01:00Z"
  },
  "data": [
    {
      "timestamp": "2025-01-12T09:00:00Z",
      "event_id": "evt_001",
      "ip": "10.123.45.67",  // Anonymized
      "username": "user_abc123456789",  // Anonymized
      "action": "process_creation"
    }
  ]
}
```

### Stage 4: Findings Structure

```json
{
  "execution_id": "exec_123",
  "playbook_id": "T1566-phishing",
  "findings": [
    {
      "finding_id": "T1566_001",
      "technique_id": "T1566",
      "severity": "high",
      "confidence": 0.85,
      "status": "new",
      "description": "Suspicious email activity detected",
      "timestamp": "2025-01-12T10:05:00Z"
    }
  ],
  "evidence": [
    {
      "evidence_id": "evd_001",
      "finding_id": "T1566_001",
      "evidence_type": "event",
      "data": {...}
    }
  ]
}
```

### Stage 5: AI Review Output

```json
{
  "finding_id": "T1566_001",
  "validation_status": "valid",
  "recommended_status": "confirmed",
  "false_positive_risk": "low",
  "confidence_assessment": {
    "current": 0.85,
    "recommended": 0.92
  },
  "ai_review": {
    "review_text": "Finding appears valid based on evidence...",
    "reasoning": "..."
  }
}
```

### Stage 6: Deanonymized Findings

```json
{
  "finding_id": "T1566_001",
  "ip": "192.168.1.100",  // Deanonymized
  "username": "john.doe",  // Deanonymized
  "description": "Activity from 192.168.1.100 by john.doe"
}
```

### Stage 7: Final Report

```markdown
# Threat Hunting Report

## Executive Summary
[AI-generated executive summary]

## Key Findings
- Finding 1: ...
- Finding 2: ...

## Detailed Findings
[Comprehensive findings with evidence]

## Statistics
[Summary statistics]
```

## Data Flow Patterns

### Pattern 1: Manual Data Upload

```
User → Upload Data → VM-01 (Parse/Normalize) → VM-02 (Store) → VM-03 (Analyze)
```

### Pattern 2: API Data Collection

```
n8n → Query Generation → API Call → VM-01 (Collect/Parse) → VM-02 (Store) → VM-03 (Analyze)
```

### Pattern 3: Complete Pipeline with AI

```
Hunt Selection → Query Gen → Data Ingestion → Storage → Analysis → AI Review → Deanonymization → Report
```

### Pattern 4: Quick Analysis (No AI)

```
Hunt Selection → Query Gen → Data Ingestion → Storage → Analysis → Report (No Deanonymization)
```

## Data Retention and Cleanup

### Retention Policy

- **Raw Logs**: 90 days retention
- **Normalized Data**: 90 days retention
- **Findings**: Permanent (unless manually deleted)
- **Evidence**: Permanent (linked to findings)
- **Anonymization Mappings**: Permanent (needed for deanonymization)

### Cleanup Process

```
VM-02: Database
    │
    ├─▶ Scheduled Cleanup (Daily)
    │   ├─▶ Identify data older than 90 days
    │   ├─▶ Delete from raw_logs
    │   ├─▶ Delete from normalized_logs
    │   └─▶ Log cleanup operations
    │
    └─▶ Anonymization Mapping Cleanup (Optional)
        └─▶ Clean up unused mappings (if configured)
```

## Error Handling and Data Recovery

### Error Handling Flow

```
Data Processing
    │
    ├─▶ Success → Continue to next stage
    │
    └─▶ Error → Error Handling
            ├─▶ Log error
            ├─▶ Retry (if applicable)
            ├─▶ Skip record (if non-critical)
            └─▶ Alert (if critical)
```

### Data Recovery

- **Database Backups**: Daily automated backups
- **Configuration Backups**: Before each config change
- **Anonymization Mappings**: Critical for deanonymization, backed up separately

## Performance Considerations

### Data Flow Optimization

- **Batch Processing**: Process multiple records in batches
- **Caching**: Cache anonymization mappings in memory
- **Parallel Processing**: Process multiple playbooks in parallel
- **Database Indexing**: Optimize database queries with proper indexes

### Bottleneck Points

1. **Data Ingestion**: Can be slow with large datasets
2. **Anonymization**: Database lookups can be slow (mitigated with caching)
3. **AI Review**: API calls to OpenAI can be slow (batch processing recommended)
4. **Report Generation**: Can be slow with many findings (pagination recommended)

## Summary

The data flow through the Threat Hunting Automation Lab is designed to be:

- **Flexible**: Supports multiple data sources and ingestion modes
- **Secure**: Anonymization protects sensitive data during AI processing
- **Traceable**: Complete audit trail of data transformations
- **Recoverable**: Backup and recovery mechanisms in place
- **Scalable**: Can handle varying data volumes

Each stage of the pipeline is designed to be independent, allowing for parallel processing and easy troubleshooting.

