# Enhanced Architecture Documentation

## Overview

This document provides a comprehensive view of the Threat Hunting Automation Lab architecture, including all implemented phases (Phase 0-4) with detailed component descriptions, integration points, and system interactions.

## System Architecture

The Threat Hunting Automation Lab is a distributed system consisting of 4 virtual machines, each serving a specific role in the automated threat hunting pipeline. The architecture supports end-to-end workflow from hunt selection through data ingestion, analysis, AI validation, and final reporting.

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Data Sources                        │
│  EDR/SIEM Systems (Microsoft Defender, Sentinel, Splunk, etc.) │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  VM-01: Ingest/Parser                                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Collectors (File, API)                                   │  │
│  │  Parsers (CSV, JSON, Defender, Sentinel, Splunk)         │  │
│  │  Normalizers (Generic, Tool-specific)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  VM-02: Database (PostgreSQL)                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Data Storage                                             │  │
│  │  - Raw logs                                              │  │
│  │  - Normalized data                                       │  │
│  │  - Findings & Evidence                                   │  │
│  │  - Anonymization mapping table                           │  │
│  │  - 90-day retention policy                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  VM-03: Analysis/Jupyter                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Playbook Engine (Deterministic Analysis)                 │  │
│  │  JupyterLab (Interactive Analysis)                       │  │
│  │  MITRE ATT&CK Playbooks                                 │  │
│  │  Query Generator                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  VM-04: Orchestrator (n8n)                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Management Dashboard                                    │  │
│  │  Pipeline Orchestrator                                   │  │
│  │  AI Service Integration                                  │  │
│  │  Deanonymization Service                                 │  │
│  │  Final Report Generator                                  │  │
│  │  Executive Summary Generator                             │  │
│  │  Remote Execution Service                                │  │
│  │  Repository Sync Service                                 │  │
│  │  Health Monitoring                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### VM-01: Ingest/Parser

**Purpose**: Data collection, parsing, and normalization from various security data sources.

**Components**:
- **Collectors**: Retrieve data from files or APIs
  - File collectors for CSV, JSON, log files
  - API collectors for EDR/SIEM systems (planned)
- **Parsers**: Extract structured data from raw logs
  - CSV parser
  - JSON parser
  - Microsoft Defender parser
  - Microsoft Sentinel parser
  - Splunk parser
  - Generic log parser
- **Normalizers**: Standardize data format
  - Generic normalizer
  - Tool-specific normalizers

**Data Flow**:
1. Collect raw data from sources
2. Parse into structured format
3. Normalize to standard schema (DataPackage)
4. Send to VM-02 (Database)

**Technologies**:
- Python 3.10+
- pandas, pyarrow for data processing
- psycopg2 for database connectivity

### VM-02: Database

**Purpose**: Centralized data storage with retention policies, anonymization mapping, and backup capabilities.

**Components**:
- **PostgreSQL 14+**: Primary database
- **Schema**: Tables for logs, findings, evidence, metadata, anonymization mappings
- **Retention Policy**: Automatic cleanup of data older than 90 days
- **Backup System**: Daily automated backups
- **Anonymization Mapping Table**: Stores mappings for deterministic anonymization/deanonymization

**Key Tables**:
- `raw_logs`: Original log data
- `normalized_logs`: Processed and standardized data
- `findings`: Threat hunting findings
- `evidence`: Supporting evidence for findings
- `anonymization_mapping`: Mapping table for anonymization/deanonymization
- `cleanup_log`: Audit trail for data retention

**Configuration**:
- Connection pooling for performance
- Access control via pg_hba.conf
- Firewall rules for network security
- SSL/TLS encryption support

**Technologies**:
- PostgreSQL 14+
- pg_cron extension (preferred) or system cron for cleanup

### VM-03: Analysis/Jupyter

**Purpose**: Interactive analysis environment and deterministic playbook execution.

**Components**:
- **JupyterLab**: Interactive notebook environment
- **Playbook Engine**: Deterministic playbook execution engine
- **Playbooks**: MITRE ATT&CK-based threat hunting playbooks
- **Query Generator**: Generate queries for different SIEM/EDR tools
- **Analysis Scripts**: Python scripts for data analysis

**Playbook Structure**:
```
playbooks/
├── template/
│   ├── metadata.yml          # Playbook metadata
│   ├── queries/              # Queries for different tools
│   │   ├── splunk.spl
│   │   ├── sentinel.kql
│   │   └── defender.kql
│   └── scripts/              # Analysis scripts
│       └── analyzer.py
```

**Playbook Engine Features**:
- Deterministic analysis (no AI dependencies)
- DataPackage processing
- Findings generation
- Evidence collection
- Integration with DeterministicAnonymizer

**Technologies**:
- JupyterLab 4.0+
- Python 3.10+
- pandas, numpy for data analysis

### VM-04: Orchestrator

**Purpose**: Central management and workflow automation hub with AI integration and reporting.

**Components**:
- **n8n**: Workflow automation platform
- **Management Dashboard**: Central interface for system management
- **Pipeline Orchestrator**: End-to-end pipeline coordination
- **AI Service**: OpenAI API integration for findings validation
- **Deanonymization Service**: Deterministic deanonymization for reporting
- **Final Report Generator**: Comprehensive report generation with real data
- **Executive Summary Generator**: AI-powered executive summaries
- **Remote Execution Service**: Execute commands on remote VMs
- **Repository Sync Service**: Synchronize code across all VMs
- **Health Monitoring**: Monitor system health and metrics
- **Configuration Management**: Centralized configuration management

**Key Services**:
- `remote_executor.py`: Execute commands via SSH
- `repo_sync.py`: Git repository synchronization
- `ssh_client.py`: SSH connection management
- `pipeline_orchestrator.py`: End-to-end pipeline orchestration
- `ai_service.py`: AI integration for findings validation
- `deanonymizer.py`: Deanonymization service
- `final_report_generator.py`: Final report generation
- `executive_summary_generator.py`: Executive summary generation

**Workflows**:
- System health monitoring
- Repository synchronization
- Deployment management
- Testing management
- Hardening management
- Threat hunting pipeline orchestration
- AI review workflow
- Complete hunt workflow (end-to-end)

**Technologies**:
- n8n (Docker container)
- Python 3.10+
- Docker and Docker Compose
- paramiko for SSH
- OpenAI API for AI services

## Phase-by-Phase Architecture

### Phase 0: Central Management Infrastructure

**Components**:
- Remote Execution Service (PHASE0-01)
- Repository Sync Service (PHASE0-02)
- Configuration Management (PHASE0-03)
- Health Monitoring (PHASE0-04)
- Management Dashboard (PHASE0-05)
- Testing Management Interface (PHASE0-06)
- Deployment Management Interface (PHASE0-07)
- Hardening Management Interface (PHASE0-08)

**Architecture Impact**:
- Foundation for all remote operations
- Centralized management capabilities
- System monitoring and health checks
- Automated testing and deployment

### Phase 1: Threat Hunting Foundations

**Components**:
- Playbook Structure (PHASE1-01)
- Query Generator (PHASE1-02)
- Deterministic Anonymization (PHASE1-03)
- n8n Hunt Selection Form (PHASE1-04)
- Data Package Structure (PHASE1-05)
- Playbook Validator (PHASE1-06)
- Playbook Management Interface (PHASE1-07)

**Architecture Impact**:
- Standardized playbook structure
- Multi-tool query generation
- Data anonymization capabilities
- User-friendly hunt selection interface

### Phase 2: Playbook Engine and Analysis

**Components**:
- Playbook Engine (PHASE2-01)
- Pipeline Integration (PHASE2-02)
- Evidence & Findings Structure (PHASE2-03)

**Architecture Impact**:
- Deterministic playbook execution
- End-to-end data pipeline
- Structured findings and evidence storage

### Phase 3: AI Integration

**Components**:
- AI Service (PHASE3-01)
- AI Review Workflow (PHASE3-02)
- Executive Summary Generator (PHASE3-03)

**Architecture Impact**:
- AI-powered findings validation
- Automated review workflows
- Executive summary generation

**AI Service Architecture**:
```
Findings → Anonymization → AI Service (OpenAI) → Validation Results
                                                      ↓
                                            Status Updates
```

### Phase 4: Deanonymization and Reporting

**Components**:
- Deanonymization Service (PHASE4-01)
- Final Report Generator (PHASE4-02)
- Complete Hunt Workflow (PHASE4-03)

**Architecture Impact**:
- Deanonymization for reporting
- Comprehensive final reports
- Complete end-to-end workflow

**Reporting Architecture**:
```
Findings → Deanonymization → Report Generator → Executive Summary → Final Report
```

## Data Flow Architecture

### Complete End-to-End Flow

```
1. Hunt Selection (VM-04/n8n)
   ↓
2. Query Generation (VM-04)
   ↓
3. Data Ingestion (VM-01) [Optional]
   ↓
4. Data Storage with Anonymization (VM-02)
   ↓
5. Playbook Execution (VM-03)
   ↓
6. Findings Generation (VM-03)
   ↓
7. AI Review (VM-04) [Optional]
   ↓
8. Deanonymization (VM-04)
   ↓
9. Final Report Generation (VM-04)
   ↓
10. Report Delivery
```

## Integration Points

### Service Integration

- **Remote Execution**: All VMs communicate via SSH through RemoteExecutor
- **Database Access**: VM-01 and VM-03 access VM-02 database
- **API Integration**: n8n workflows use REST APIs for service communication
- **AI Integration**: AI Service integrates with OpenAI API
- **Anonymization**: DeterministicAnonymizer uses VM-02 database for mapping storage

### Workflow Integration

- **n8n Workflows**: Coordinate all phases through webhook-based workflows
- **Pipeline Orchestrator**: Manages end-to-end data flow
- **Management Dashboard**: Provides unified interface for all operations

## Security Architecture

### Defense in Depth

1. **Network Layer**: Firewall rules, network segmentation
2. **Application Layer**: Authentication, authorization, API keys
3. **Data Layer**: Encryption at rest, data anonymization
4. **Access Layer**: SSH keys, strong passwords, fail2ban

### Data Protection

- **Anonymization**: PII data anonymized before AI analysis
- **Deanonymization**: Controlled deanonymization only for reporting
- **Retention**: Automatic cleanup of old data (90 days)
- **Backup**: Regular backups of critical data
- **Audit**: Logging of all operations

### Access Control

- **SSH**: Key-based authentication preferred
- **Database**: Role-based access control
- **API**: Bearer token authentication
- **n8n**: Basic Auth or OAuth

## Scalability Considerations

### Current Architecture

Designed for single deployment with:
- Single instance of each VM
- PostgreSQL single-node configuration
- n8n single-instance deployment

### Scaling Options

- **Horizontal Scaling**: Add additional VM-01 instances for higher ingestion rates
- **Database Scaling**: PostgreSQL can be configured with replication
- **Analysis Scaling**: Multiple VM-03 instances can run playbooks in parallel
- **Orchestration**: n8n can handle multiple concurrent workflows

## Deployment Architecture

### Installation Order

1. VM-02 (Database) - Foundation for data storage
2. VM-01 (Ingest) - Can start collecting data
3. VM-03 (Analysis) - Can analyze stored data
4. VM-04 (Orchestrator) - Manages everything

### Configuration Management

- Central configuration in `configs/config.yml`
- VM-specific configurations in `hosts/vmXX-*/config.yml`
- Environment variables in `.env` (sensitive data)
- All configurations synchronized via repository sync

## Monitoring and Observability

### Health Monitoring

- **Health Checks**: Automated health checks every 5 minutes
- **Metrics Collection**: CPU, memory, disk usage for all VMs
- **Service Status**: PostgreSQL, JupyterLab, n8n, Docker status
- **Alerting**: Automatic alerts for critical issues

### Logging

- **Application Logs**: In `logs/` directory
- **System Logs**: Via journalctl
- **Database Logs**: PostgreSQL logs
- **n8n Logs**: Docker container logs
- **Audit Logs**: All operations logged for audit trail

## Future Enhancements

- **API Integration**: Direct API connections to EDR/SIEM systems
- **Real-time Processing**: Stream processing for real-time threat detection
- **Distributed Processing**: Distributed analysis across multiple nodes
- **Cloud Deployment**: Support for cloud-based deployments
- **Multi-tenant**: Support for multiple organizations
- **Advanced AI**: Integration with additional AI models and services

## Troubleshooting Architecture

### Health Checks

Each VM has a `health_check.sh` script that verifies:
- System requirements
- Service status
- Configuration validity
- Network connectivity

### Diagnostic Tools

- **Management Dashboard**: Visual system overview
- **Testing Management Interface**: Automated test execution
- **Health Monitoring**: Real-time metrics and status
- **Log Analysis**: Centralized log access

## Architecture Diagrams

### Network Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   VM-01     │     │   VM-02     │     │   VM-03     │     │   VM-04     │
│  Ingest     │────▶│  Database   │◀────│  Analysis   │     │ Orchestrator│
│             │     │             │     │             │     │             │
│ 10.0.0.10   │     │ 10.0.0.11   │     │ 10.0.0.12   │     │ 10.0.0.13   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
      │                    │                    │                    │
      └────────────────────┴────────────────────┴────────────────────┘
                           │
                    Private Network
```

### Service Communication

```
VM-04 (Orchestrator)
    │
    ├──▶ SSH ──▶ VM-01 (Remote Execution)
    ├──▶ SSH ──▶ VM-02 (Remote Execution)
    ├──▶ SSH ──▶ VM-03 (Remote Execution)
    │
    ├──▶ API ──▶ Database (VM-02) - Anonymization Mapping
    ├──▶ API ──▶ OpenAI - AI Services
    │
    └──▶ n8n Workflows ──▶ All Services
```

## Summary

The Threat Hunting Automation Lab architecture provides a comprehensive, scalable, and secure platform for automated threat hunting. The distributed design with clear separation of concerns enables:

- **Modularity**: Each VM serves a specific purpose
- **Scalability**: Components can be scaled independently
- **Security**: Defense in depth with multiple security layers
- **Automation**: End-to-end workflow automation
- **Extensibility**: Easy to add new features and integrations

The architecture supports the complete threat hunting lifecycle from hunt selection through data collection, analysis, AI validation, and final reporting.

