# Architecture Documentation

## System Overview

The Threat Hunting Automation Lab is a distributed system designed to automate and standardize threat hunting operations. The architecture follows a modular approach with clear separation of concerns across four virtual machines.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EDR/SIEM Systems                         │
│              (Data Sources - External)                      │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  VM-01: Ingest/Parser                                        │
│  - Collectors (File, API)                                   │
│  - Parsers (CSV, JSON, Defender, etc.)                      │
│  - Normalizers (Generic, Defender-specific)                │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  VM-02: Database (PostgreSQL)                               │
│  - Raw log storage                                          │
│  - Normalized data storage                                  │
│  - Findings and evidence                                    │
│  - 90-day retention policy                                  │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  VM-03: Analysis/Jupyter                                    │
│  - JupyterLab for interactive analysis                      │
│  - MITRE ATT&CK playbooks                                   │
│  - ML/AI models for anomaly detection                      │
│  - Query generation and execution                           │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  VM-04: Orchestrator (n8n)                                 │
│  - Workflow automation                                      │
│  - Management dashboard                                     │
│  - Remote execution service                                 │
│  - Repository synchronization                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### VM-01: Ingest/Parser

**Purpose:** Collect, parse, and normalize data from various sources before storing in the database.

**Components:**
- **Collectors**: Retrieve data from files or APIs
  - File collectors for CSV, JSON, log files
  - API collectors for EDR/SIEM systems
- **Parsers**: Extract structured data from raw logs
  - CSV parser
  - JSON parser
  - Microsoft Defender parser
  - Generic log parser
- **Normalizers**: Standardize data format
  - Generic normalizer
  - Defender-specific normalizer

**Data Flow:**
1. Collect raw data from sources
2. Parse into structured format
3. Normalize to standard schema
4. Send to VM-02 (Database)

**Technologies:**
- Python 3.10+
- pandas, pyarrow for data processing
- psycopg2 for database connectivity

### VM-02: Database

**Purpose:** Centralized data storage with retention policies and backup capabilities.

**Components:**
- **PostgreSQL 14+**: Primary database
- **Schema**: Tables for logs, findings, evidence, metadata
- **Retention Policy**: Automatic cleanup of data older than 90 days
- **Backup System**: Daily automated backups

**Key Tables:**
- `raw_logs`: Original log data
- `normalized_logs`: Processed and standardized data
- `findings`: Threat hunting findings
- `evidence`: Supporting evidence for findings
- `cleanup_log`: Audit trail for data retention

**Configuration:**
- Connection pooling for performance
- Access control via pg_hba.conf
- Firewall rules for network security

**Technologies:**
- PostgreSQL 14+
- pg_cron extension (preferred) or system cron for cleanup

### VM-03: Analysis/Jupyter

**Purpose:** Interactive analysis environment for threat hunters to execute playbooks and analyze data.

**Components:**
- **JupyterLab**: Interactive notebook environment
- **Playbooks**: MITRE ATT&CK-based threat hunting playbooks
- **Query Generator**: Generate queries for different SIEM/EDR tools
- **ML Models**: Anomaly detection and classification models
- **Analysis Scripts**: Python scripts for data analysis

**Playbook Structure:**
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

**Technologies:**
- JupyterLab 4.0+
- Python 3.10+
- scikit-learn, matplotlib, seaborn for ML/visualization
- pandas, numpy for data analysis

### VM-04: Orchestrator

**Purpose:** Central management and workflow automation hub.

**Components:**
- **n8n**: Workflow automation platform
- **Management Dashboard**: Central interface for system management
- **Remote Execution Service**: Execute commands on remote VMs
- **Repository Sync Service**: Synchronize code across all VMs
- **Health Monitoring**: Monitor system health and metrics
- **Configuration Management**: Centralized configuration management

**Key Services:**
- `remote_executor.py`: Execute commands via SSH
- `repo_sync.py`: Git repository synchronization
- `ssh_client.py`: SSH connection management

**Workflows:**
- System health monitoring
- Repository synchronization
- Deployment management
- Testing management
- Hardening management
- Threat hunting pipeline orchestration

**Technologies:**
- n8n (Docker container)
- Python 3.10+
- Docker and Docker Compose
- paramiko for SSH

## Data Flow

### Standard Threat Hunting Flow

1. **Data Ingestion** (VM-01)
   - Collect data from EDR/SIEM or files
   - Parse raw logs
   - Normalize to standard format
   - Store in VM-02 database

2. **Data Storage** (VM-02)
   - Receive normalized data
   - Store in PostgreSQL
   - Apply retention policies

3. **Analysis** (VM-03)
   - Threat hunter selects playbook
   - Query generator creates queries
   - Execute analysis scripts
   - Generate findings

4. **Orchestration** (VM-04)
   - Coordinate workflow via n8n
   - Manage playbook execution
   - Aggregate results
   - Generate reports

### Management Flow

1. **Configuration Changes** (VM-04)
   - Update central config
   - Sync to all VMs via repository sync
   - Apply changes remotely

2. **Health Monitoring** (VM-04)
   - Periodic health checks
   - Collect metrics from all VMs
   - Alert on issues

3. **Deployment** (VM-04)
   - Trigger installation scripts remotely
   - Monitor progress
   - Verify installation

## Network Architecture

### Network Requirements

- All VMs must be on the same network or have network connectivity
- SSH access required between VMs (especially VM-04 to others)
- Database port (5432) must be accessible from VM-01 and VM-03
- JupyterLab port (8888) must be accessible from VM-04
- n8n port (5678) must be accessible from VM-03

### Security Considerations

- Firewall rules restrict access to necessary ports only
- SSH key-based authentication preferred
- Database access restricted to specific IPs
- All services use authentication (tokens, passwords)

## Scalability

The current architecture is designed for a single deployment. For scaling:

- **Horizontal Scaling**: Add additional VM-01 instances for higher ingestion rates
- **Database Scaling**: PostgreSQL can be configured with replication
- **Analysis Scaling**: Multiple VM-03 instances can run playbooks in parallel
- **Orchestration**: n8n can handle multiple concurrent workflows

## Security Architecture

### Defense in Depth

1. **Network Layer**: Firewall rules, network segmentation
2. **Application Layer**: Authentication, authorization
3. **Data Layer**: Encryption at rest, data anonymization
4. **Access Layer**: SSH keys, strong passwords, fail2ban

### Data Protection

- **Anonymization**: PII data anonymized before AI analysis
- **Retention**: Automatic cleanup of old data (90 days)
- **Backup**: Regular backups of critical data
- **Audit**: Logging of all operations

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

## Future Enhancements

- **API Integration**: Direct API connections to EDR/SIEM systems
- **Real-time Processing**: Stream processing for real-time threat detection
- **Distributed Processing**: Distributed analysis across multiple nodes
- **Cloud Deployment**: Support for cloud-based deployments
- **Multi-tenant**: Support for multiple organizations

## Troubleshooting Architecture

### Health Checks

Each VM has a `health_check.sh` script that verifies:
- System requirements
- Service status
- Configuration validity
- Network connectivity

### Monitoring

- System metrics collected by VM-04
- Health status displayed in management dashboard
- Alerts for critical issues

### Logging

- Application logs in `logs/` directory
- System logs via journalctl
- Database logs in PostgreSQL logs
- n8n logs in Docker container

