# Threat Hunting Lab - Enhanced Architecture Documentation

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Details](#component-details)
4. [Network Architecture](#network-architecture)
5. [Data Flow Architecture](#data-flow-architecture)
6. [Security Architecture](#security-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Technology Stack](#technology-stack)
9. [Integration Points](#integration-points)
10. [Scalability and Performance](#scalability-and-performance)

## Overview

The Threat Hunting Lab is a comprehensive, automated threat hunting system designed to collect, normalize, store, analyze, and orchestrate threat intelligence data. The system is built on a distributed architecture with four virtual machines, each serving a specific role in the threat hunting workflow.

### Key Objectives

- **Standardization**: MITRE ATT&CK-based playbooks for consistent threat hunting
- **Automation**: Full workflow automation with n8n orchestration
- **Integration**: EDR/SIEM API integrations for data collection
- **Analysis**: AI/ML-powered analysis capabilities
- **Security**: Deterministic anonymization and secure data handling
- **Compliance**: 90-day data retention with automated backups

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Threat Hunting Lab System                    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   VM-01      │      │   VM-02      │      │   VM-03      │
│  Ingest/     │─────▶│  Database    │◀─────│  Analysis/   │
│  Parser      │      │  PostgreSQL  │      │  Jupyter     │
└──────────────┘      └──────────────┘      └──────────────┘
        │                     │                     │
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                      ┌──────────────┐
                      │   VM-04      │
                      │ Orchestrator │
                      │     n8n      │
                      └──────────────┘
```

### Component Roles

1. **VM-01: Ingest/Parser**
   - Data collection from EDR/SIEM systems
   - Data parsing and normalization
   - Initial data validation
   - Forwarding to database

2. **VM-02: Database**
   - Central PostgreSQL database
   - Data storage with 90-day retention
   - Automated backups
   - Data retention management

3. **VM-03: Analysis/Jupyter**
   - Interactive analysis environment
   - Playbook execution
   - AI/ML model integration
   - Report generation

4. **VM-04: Orchestrator**
   - n8n workflow automation
   - Remote command execution
   - Repository synchronization
   - Health monitoring
   - Configuration management

## Component Details

### VM-01: Ingest/Parser

**Purpose**: Collect, parse, and normalize threat intelligence data from various sources.

**Key Components**:
- **Collectors**: Modules for collecting data from EDR/SIEM APIs
- **Parsers**: Data parsing modules for different log formats
- **Normalizers**: Data normalization to common schema
- **Validators**: Data validation and quality checks

**Technologies**:
- Python 3.10+
- pandas, numpy for data processing
- pyarrow for efficient data handling
- psycopg2 for database connectivity
- requests for API integrations

**Data Flow**:
```
External Sources → Collectors → Parsers → Normalizers → Database (VM-02)
```

**Configuration**:
- Collector endpoints and credentials (stored in `.env`)
- Parser configurations for different log formats
- Normalization rules and schemas
- Database connection settings

### VM-02: Database

**Purpose**: Central data storage with retention and backup management.

**Key Components**:
- **PostgreSQL 14+**: Primary database server
- **Retention Manager**: Automated data cleanup (90-day retention)
- **Backup System**: Automated daily backups with rotation
- **Access Control**: IP-based access restrictions via pg_hba.conf

**Technologies**:
- PostgreSQL 14+
- pg_cron extension (preferred) or system cron
- rsync for backup transfers
- Python scripts for retention management

**Data Schema**:
- Normalized threat intelligence data
- Metadata tables
- Audit logs
- Cleanup operation logs

**Retention Policy**:
- Default: 90 days
- Configurable per table
- Automated daily cleanup at 3:00 AM
- Logged cleanup operations

**Backup Policy**:
- Daily backups at 2:00 AM
- 30-day backup retention
- Automated rotation
- Backup verification

### VM-03: Analysis/Jupyter

**Purpose**: Interactive analysis environment for threat hunting operations.

**Key Components**:
- **JupyterLab**: Interactive notebook environment
- **Playbook Engine**: Execution engine for MITRE ATT&CK playbooks
- **AI Integration**: ChatGPT-5+ integration for analysis
- **Visualization Tools**: matplotlib, seaborn for data visualization
- **ML Models**: scikit-learn for anomaly detection

**Technologies**:
- JupyterLab
- Python 3.10+ with scientific computing libraries
- Node.js 18.x LTS (for JupyterLab extensions)
- PostgreSQL client libraries
- OpenAI API integration

**Features**:
- Interactive data exploration
- Playbook execution and automation
- AI-assisted analysis
- Report generation
- Deanonymization capabilities (authorized users only)

**Access Control**:
- Token-based authentication
- Optional password protection
- IP-based firewall restrictions
- File upload restrictions (configurable)

### VM-04: Orchestrator

**Purpose**: Central orchestration and workflow automation.

**Key Components**:
- **n8n**: Workflow automation platform
- **Remote Executor**: Module for remote command execution on VMs
- **Repository Sync**: Git synchronization across VMs
- **Health Monitor**: System health monitoring and alerting
- **Configuration Manager**: Centralized configuration management

**Technologies**:
- n8n (Docker container)
- Docker Engine
- Python 3.10+ for automation scripts
- Git for repository management

**Workflow Capabilities**:
- Automated data collection workflows
- Scheduled playbook execution
- Health check automation
- Backup orchestration
- Alert and notification workflows

**Security**:
- Basic authentication for n8n
- SSH key-based remote access
- Encrypted communication
- Audit logging

## Network Architecture

### Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    Private Network                          │
│                    10.0.0.0/24                             │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         │              │              │              │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │ VM-01   │    │ VM-02   │    │ VM-03   │    │ VM-04   │
    │10.0.0.10│    │10.0.0.11│    │10.0.0.12│    │10.0.0.13│
    └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

### Network Configuration

- **Subnet**: Private network (configurable, default: 10.0.0.0/24)
- **Gateway**: Network gateway (configurable)
- **DNS**: Custom DNS servers (optional, default: 8.8.8.8, 8.8.4.4)

### Communication Patterns

1. **VM-01 → VM-02**: Data ingestion (PostgreSQL port 5432)
2. **VM-03 → VM-02**: Data queries and analysis (PostgreSQL port 5432)
3. **VM-04 → All VMs**: Remote execution via SSH
4. **VM-04 → VM-03**: JupyterLab access (port 8888)
5. **VM-03 → VM-04**: n8n API access (port 5678)

### Firewall Rules

Each VM implements firewall rules via ufw:
- **SSH**: Port 22 (restricted to network subnet)
- **PostgreSQL**: Port 5432 (VM-02, restricted to VM-01 and VM-03)
- **JupyterLab**: Port 8888 (VM-03, restricted to network subnet)
- **n8n**: Port 5678 (VM-04, restricted to network subnet)

## Data Flow Architecture

### Data Collection Flow

```
┌──────────────┐
│ EDR/SIEM     │
│ APIs         │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ VM-01        │
│ Collectors   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ VM-01        │
│ Parsers      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ VM-01        │
│ Normalizers  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ VM-02        │
│ PostgreSQL   │
└──────────────┘
```

### Analysis Flow

```
┌──────────────┐
│ VM-02        │
│ PostgreSQL   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ VM-03        │
│ JupyterLab   │
│ Playbooks    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ AI/ML        │
│ Analysis     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Reports      │
│ Generation   │
└──────────────┘
```

### Orchestration Flow

```
┌──────────────┐
│ VM-04        │
│ n8n          │
│ Workflows    │
└──────┬───────┘
       │
       ├───▶ VM-01: Trigger collection
       ├───▶ VM-02: Trigger backup
       ├───▶ VM-03: Execute playbook
       └───▶ All: Health checks
```

## Security Architecture

### Security Layers

1. **Network Security**
   - Private network isolation
   - Firewall rules (ufw)
   - IP-based access restrictions
   - SSH key-based authentication

2. **Application Security**
   - Token-based authentication (JupyterLab)
   - Basic authentication (n8n)
   - Encrypted database connections
   - Secure credential storage (.env files)

3. **Data Security**
   - Deterministic anonymization
   - PII hashing
   - Encryption at rest (optional)
   - Secure data transmission

4. **System Security**
   - Hardened SSH configuration
   - Fail2ban protection
   - Automatic security updates
   - Audit logging (optional)

### Anonymization Architecture

- **Deterministic Anonymization**: Same input produces same anonymized output
- **Reversible**: Authorized users can deanonymize data
- **PII Detection**: Automatic detection of personally identifiable information
- **Hash-based Mapping**: Secure hash-based mapping for reversible anonymization

See [ANONYMIZATION.md](ANONYMIZATION.md) for detailed anonymization policy.

## Deployment Architecture

### Deployment Model

- **Lab Environment**: Isolated lab environment (current)
- **Production Ready**: Architecture supports production deployment
- **Scalability**: Horizontal scaling possible for each component

### Repository Structure

```
th_timmy/
├── hosts/                    # VM-specific setup scripts
│   ├── vm01-ingest/
│   ├── vm02-database/
│   ├── vm03-analysis/
│   ├── vm04-orchestrator/
│   └── shared/               # Shared scripts and utilities
├── automation-scripts/       # Core automation modules
│   ├── collectors/
│   ├── parsers/
│   ├── normalizers/
│   ├── orchestrators/
│   └── utils/
├── configs/                  # Configuration files
├── docs/                     # Documentation
└── results/                  # Analysis results (gitignored)
```

### Synchronization Model

- **Central Repository**: Git repository on VM-04
- **Synchronization**: Automated sync to other VMs via n8n workflows
- **Configuration Management**: Centralized configuration in `configs/config.yml`

## Technology Stack

### Core Technologies

- **Operating System**: Ubuntu Server 22.04 LTS
- **Programming Language**: Python 3.10+
- **Database**: PostgreSQL 14+
- **Orchestration**: n8n (Docker)
- **Containerization**: Docker Engine
- **Version Control**: Git

### Python Libraries

- **Data Processing**: pandas, numpy, pyarrow
- **Database**: psycopg2-binary, sqlalchemy
- **Configuration**: pyyaml, python-dotenv
- **Analysis**: scikit-learn, matplotlib, seaborn
- **AI Integration**: openai
- **Utilities**: requests, loguru, python-dateutil

### Infrastructure

- **Web Server**: JupyterLab (VM-03)
- **Workflow Engine**: n8n (VM-04)
- **Database Server**: PostgreSQL (VM-02)
- **Backup Tools**: rsync, cron

## Integration Points

### External Integrations

1. **EDR Systems**
   - API-based data collection
   - Configurable endpoints and authentication
   - Real-time and batch collection modes

2. **SIEM Systems**
   - Log aggregation
   - Query-based data extraction
   - Event correlation

3. **AI Services**
   - OpenAI ChatGPT-5+ integration
   - Analysis assistance
   - Report generation

### Internal Integrations

1. **VM-01 ↔ VM-02**: Database writes
2. **VM-03 ↔ VM-02**: Database reads
3. **VM-04 ↔ All VMs**: Remote execution and monitoring
4. **VM-04 ↔ VM-03**: JupyterLab integration
5. **VM-03 ↔ VM-04**: n8n API integration

## Scalability and Performance

### Current Capacity

- **Data Volume**: Designed for lab-scale data volumes
- **Concurrent Users**: Single analyst (JupyterLab)
- **Workflow Complexity**: Moderate complexity workflows

### Scalability Options

1. **Horizontal Scaling**
   - Multiple VM-01 instances for increased collection
   - Read replicas for VM-02 (PostgreSQL)
   - Multiple VM-03 instances for parallel analysis

2. **Performance Optimization**
   - Database indexing
   - Query optimization
   - Caching strategies
   - Resource limits

### Performance Considerations

- **Data Retention**: 90-day retention keeps database size manageable
- **Backup Strategy**: Daily backups with 30-day retention
- **Network Latency**: Private network minimizes latency
- **Resource Allocation**: VM resource allocation based on workload

## Maintenance and Operations

### Health Monitoring

- Automated health checks via n8n workflows
- Service status monitoring
- Database health checks
- Network connectivity tests

### Backup and Recovery

- Daily automated backups
- 30-day backup retention
- Backup verification
- Recovery procedures documented

### Update Procedures

- System updates via automatic security updates
- Application updates via package managers
- n8n updates via Docker image updates
- Database migrations via versioned scripts

## Compliance and Security

### Data Retention

- **90-day retention**: Production-ready default
- **Configurable**: Per-table retention policies
- **Automated cleanup**: Daily cleanup operations
- **Audit logging**: Cleanup operations logged

### Access Control

- **SSH**: Key-based authentication, root login disabled
- **Database**: IP-based access control, user-based permissions
- **JupyterLab**: Token-based authentication
- **n8n**: Basic authentication

### Audit and Logging

- **System logs**: Centralized logging (optional)
- **Database logs**: PostgreSQL audit logs
- **Application logs**: Structured logging with loguru
- **Access logs**: SSH and service access logs

## Future Enhancements

### Planned Features

1. **Enhanced AI Integration**
   - Advanced ML models
   - Automated threat detection
   - Predictive analytics

2. **Extended Integrations**
   - Additional EDR/SIEM platforms
   - Threat intelligence feeds
   - External API integrations

3. **Advanced Analytics**
   - Real-time streaming analysis
   - Complex event processing
   - Advanced visualization

4. **Production Features**
   - High availability setup
   - Load balancing
   - Advanced monitoring and alerting

## References

- [Configuration Guide](CONFIGURATION.md)
- [Hardening Guide](HARDENING.md)
- [Testing Guide](TESTING.md)
- [Data Flow Documentation](DATA_FLOW.md)
- [Anonymization Policy](ANONYMIZATION.md)
- [User Guide for Hunters](USER_GUIDE_HUNTER.md)
