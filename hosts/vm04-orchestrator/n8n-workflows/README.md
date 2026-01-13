# Management Dashboard - n8n Workflow

## Description

Management Dashboard is the primary n8n workflow for managing the Threat Hunting Lab system. The dashboard provides a central interface for monitoring and managing all system components.

## Features

### 1. System Overview
- **Status of all 4 VMs** - Displays health status of each VM as color-coded cards:
  - 🟢 Green - VM healthy
  - 🟡 Yellow - VM in degraded state
  - 🔴 Red - VM unhealthy
- **System metrics** - Displays metrics for each VM:
  - CPU usage (%)
  - Memory usage (%)
  - Disk usage (%)
- **Automatic refresh** - Status is automatically refreshed every 5 minutes

### 2. Health Monitoring
- **Automatic health checks** - Scheduled trigger runs health checks every 5 minutes
- **Health Monitor Service integration** - Uses `HealthMonitor` (PHASE0-04) to check VM health
- **Alerts** - Automatic alerts in case of VM health problems

### 3. Repository Sync
- **Sync button** - Manual repository synchronization trigger
- **Sync to all VMs** - Uses `RepoSyncService` (PHASE0-02)
- **Sync status** - Displays synchronization operation results

### 4. Configuration Management
- **Configuration display** - Ability to view central configuration
- **Configuration editing** - Ability to update configuration through dashboard
- **Validation** - Automatic validation before saving changes
- **Backup** - Automatic backup creation before changes

### 5. Quick Actions
- **Health Checks** - Manual health check trigger for selected VM
- **Connection tests** - Testing connectivity between VMs
- **Service status** - Checking status of services (PostgreSQL, JupyterLab, n8n, Docker)

## Installation

### 1. Import workflow to n8n

1. Log into n8n (default: http://VM04_IP:5678)
2. Go to **Workflows** → **Import from File**
3. Select file `management-dashboard.json`
4. Click **Import**

### 2. Configuration

After importing the workflow, configure the following elements:

#### API Endpoints

The workflow requires API services to be available. Ensure that:

1. **Remote Execution API** is running:
   ```bash
   # On VM04
   cd /home/thadmin/th_timmy
   uvicorn automation-scripts.api.remote_api:app --host 0.0.0.0 --port 8000
   ```

2. **Health Monitor Service** is available via API (endpoints can be added in the future)

3. **Repository Sync Service** is available via API (endpoints can be added in the future)

#### Webhook URL Configuration

The workflow uses n8n webhooks. After activating the workflow, n8n will generate unique URLs for each webhook. Update them in the dashboard UI if needed.

#### Authentication Configuration

If the API requires authentication (API key), configure it in HTTP Request nodes:
1. Open HTTP Request node
2. In **Authentication** section select **Header Auth**
3. Set:
   - **Name**: `Authorization`
   - **Value**: `Bearer YOUR_API_KEY`

## Usage

### Accessing Dashboard

1. Activate workflow in n8n
2. Open webhook URL for "Dashboard UI" (e.g., `http://VM04_IP:5678/webhook/dashboard`)
3. Dashboard will be displayed in browser

### Automatic Health Checks

The workflow automatically runs health checks every 5 minutes. You can change the interval in the "Schedule Health Check" node:
- Open the node
- Change `minutesInterval` value in parameters

### Manual Operations

#### Repository Synchronization

1. Click **"Sync Repository"** button in dashboard
2. Or send POST request to webhook:
   ```bash
   curl -X POST http://VM04_IP:5678/webhook/sync-repository \
     -H "Content-Type: application/json" \
     -d '{}'
   ```

#### Health Status Check

1. Click **"Refresh Status"** button in dashboard
2. Or send POST request to webhook:
   ```bash
   curl -X POST http://VM04_IP:5678/webhook/get-health-status \
     -H "Content-Type: application/json" \
     -d '{"vm_id": "vm01"}'
   ```

## Service Integration

The dashboard integrates with the following services:

### PHASE0-01: Remote Execution Service
- **Endpoint**: `POST /execute-command`
- **Usage**: Executing commands on remote VMs
- **Example**: Health checks, connection tests

### PHASE0-02: Repository Sync Service
- **Function**: `sync_repository_to_all_vms()`
- **Usage**: Git repository synchronization on all VMs
- **Status**: Currently via direct call (API endpoint can be added)

### PHASE0-03: Configuration Manager
- **Functions**: `get_config()`, `update_config()`, `validate_config()`
- **Usage**: System configuration management
- **Status**: Currently via direct call (API endpoint can be added)

### PHASE0-04: Health Monitor
- **Functions**: `check_vm_health()`, `get_health_status_all()`, `collect_metrics()`
- **Usage**: VM health monitoring and metrics collection
- **Status**: Currently via direct call (API endpoint can be added)

## Workflow Structure

The workflow consists of the following nodes:

1. **Schedule Health Check** - Trigger that runs every 5 minutes
2. **Get All VM Status** - Collecting status of all VMs
3. **Set VM Status** - Preparing status data
4. **Dashboard UI** - Webhook displaying user interface
5. **Get Health Status** - Webhook for manual status check
6. **Sync Repository** - Webhook for repository synchronization
7. **Execute Command** - Command execution via API
8. **Respond nodes** - HTTP responses for webhooks

## Extending

### Adding New Features

1. Add new webhook node for new feature
2. Add HTTP Request node for API communication
3. Add button in dashboard UI
4. Update JavaScript in dashboard to handle new feature

### Adding New Metrics

1. Extend "Get All VM Status" node with new metrics
2. Update HTML template in "Respond Dashboard" to display new metrics

## Troubleshooting

### Dashboard Not Loading

1. Check if workflow is activated in n8n
2. Check if webhook URL is correct
3. Check n8n logs for errors

### Health Checks Not Working

1. Check if API is running and available
2. Check authentication configuration in HTTP Request nodes
3. Check if VMs are accessible via SSH

### Repository Synchronization Not Working

1. Check if Git repository is configured on all VMs
2. Check SSH permissions to remote VMs
3. Check logs in n8n and services

## Security

⚠️ **WARNING**: Dashboard currently does not have full authentication. In production environment:

1. Configure n8n with Basic Auth or OAuth
2. Add API key authentication to all endpoints
3. Restrict dashboard access to authorized users only
4. Use HTTPS instead of HTTP

## Testing Management Workflow

### Installation

1. Import workflow `testing-management.json` to n8n
2. Activate workflow
3. Access dashboard: `http://VM04_IP:5678/webhook/testing-dashboard`

### Features

- **Connection Tests**: Running `test_connections.sh` remotely
- **Data Flow Tests**: Running `test_data_flow.sh` remotely
- **Health Checks**: Running `health_check.sh` on all VMs
- **Test Results**: Displaying test results in dashboard
- **Test History**: History of all tests

### Webhook Endpoints

- `POST /webhook/run-connection-tests` - Run connection tests
- `POST /webhook/run-data-flow-tests` - Run data flow tests
- `POST /webhook/run-health-checks` - Run health checks on all VMs
- `GET /webhook/test-results` - Get test results
- `GET /webhook/test-history` - Get test history
- `GET /webhook/testing-dashboard` - Testing management dashboard

## Deployment Management Workflow

### Installation

1. Import workflow `deployment-management.json` to n8n
2. Activate workflow
3. Access dashboard: `http://VM04_IP:5678/webhook/deployment-dashboard`

### Features

- **Installation Status**: Installation status on all VMs
- **Run Installation**: Running `install_vmXX.sh` remotely
- **Installation Logs**: Displaying installation logs
- **Deployment Verification**: Post-installation verification

### Webhook Endpoints

- `GET /webhook/installation-status` - Get installation status of all VMs
- `POST /webhook/run-installation` - Run installation on selected VM
- `GET /webhook/installation-logs` - Get installation logs
- `POST /webhook/verify-deployment` - Verify deployment on VM
- `GET /webhook/deployment-dashboard` - Deployment management dashboard

### Usage

#### Check Installation Status

```bash
curl http://VM04_IP:5678/webhook/installation-status
```

#### Run Installation

```bash
curl -X POST http://VM04_IP:5678/webhook/run-installation \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "vm01"}'
```

#### Verify Deployment

```bash
curl -X POST http://VM04_IP:5678/webhook/verify-deployment \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "vm01"}'
```

## Hardening Management Workflow

### Installation

1. Import workflow `hardening-management.json` to n8n
2. Activate workflow
3. Access dashboard: `http://VM04_IP:5678/webhook/hardening-dashboard`

### Features

- **Hardening Status**: Hardening status on all VMs
- **Run Hardening**: Running `harden_vmXX.sh` remotely
- **Before/After Comparison**: Before/after hardening comparison
- **Hardening Reports**: Hardening reports

### Webhook Endpoints

- `GET /webhook/hardening-status` - Get hardening status of all VMs
- `POST /webhook/run-hardening` - Run hardening on selected VM
- `GET /webhook/hardening-reports` - Get hardening reports
- `POST /webhook/compare-before-after` - Compare before/after hardening
- `GET /webhook/hardening-dashboard` - Hardening management dashboard

### Usage

#### Check Hardening Status

```bash
curl http://VM04_IP:5678/webhook/hardening-status
```

#### Run Hardening

```bash
curl -X POST http://VM04_IP:5678/webhook/run-hardening \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "vm01", "capture_before": true}'
```

#### Before/After Comparison

```bash
curl -X POST http://VM04_IP:5678/webhook/compare-before-after \
  -H "Content-Type: application/json" \
  -d '{"hardening_id": "20240115_120000", "vm_id": "vm01"}'
```

## Hunt Selection Form Workflow

### Installation

1. Import workflow `hunt-selection-form.json` to n8n
2. Activate workflow
3. Access form: `http://VM04_IP:5678/webhook/hunt-selection`

### Features

- **Hunt Selection**: Selection of MITRE ATT&CK techniques for investigation
- **Tool Selection**: Selection of available SIEM/EDR tools
- **Ingest Mode**: Selection of execution mode (manual/API)
- **Query Generation**: Automatic query generation
- **Query Display**: Displaying generated queries with copy functionality

### Webhook Endpoints

- `GET /webhook/hunt-selection` - Hunt selection form (HTML)
- `GET /webhook/available-playbooks` - Get available playbooks
- `GET /webhook/available-tools` - Get available tools
- `POST /webhook/generate-queries` - Generate queries for selected hunts and tools

### Usage

#### Access Form

1. Open in browser: `http://VM04_IP:5678/webhook/hunt-selection`
2. Form will automatically load available playbooks and tools

#### Hunt Selection and Query Generation

1. **Select MITRE ATT&CK techniques**: Check boxes for techniques you want to investigate
2. **Select tools**: Check boxes for tools you have available
3. **Select ingest mode**: 
   - **Manual**: Queries for manual copy and execution
   - **API**: Queries for automatic execution via API
4. **Set parameters**: Select time range and minimum severity
5. **Click "Generate Queries"**: System will generate queries for selected combinations

#### Displaying Results

- Generated queries are displayed in readable format
- Each query has "Copy Query" button for copying
- Execution instructions are displayed for each query
- Warnings are displayed if queries are not available

### Integration

- **PHASE1-02**: Uses Query Generator for query generation
- **PHASE0-05**: Integration with Management Dashboard
- **API Endpoints**: Uses `/query-generator/*` endpoints from dashboard_api.py

### Usage Examples

#### Get Available Playbooks

```bash
curl http://VM04_IP:5678/webhook/available-playbooks
```

#### Get Available Tools

```bash
curl http://VM04_IP:5678/webhook/available-tools
```

#### Generate Queries

```bash
curl -X POST http://VM04_IP:5678/webhook/generate-queries \
  -H "Content-Type: application/json" \
  -d '{
    "technique_ids": ["T1566", "T1059"],
    "tool_names": ["Microsoft Defender for Endpoint", "Splunk"],
    "mode": "manual",
    "parameters": {
      "time_range": "7d",
      "severity": "high"
    }
  }'
```

## Playbook Manager Workflow

### Installation

1. Import workflow `playbook-manager.json` to n8n
2. Activate workflow
3. Access dashboard: `http://VM04_IP:5678/webhook/playbook-manager`

### Features

- **Playbook List**: Displaying all available playbooks with validation status
- **Create Playbook**: Form for creating new playbook from template
- **Edit Playbook**: Updating playbook metadata
- **Validate Playbook**: Validating playbook structure and metadata
- **Test Playbook**: Testing playbook (validation, structure, query files)

### Webhook Endpoints

- `GET /webhook/playbook-manager` - Playbook management dashboard (HTML)
- `GET /webhook/list-playbooks` - Get list of all playbooks
- `GET /webhook/get-playbook` - Get playbook details
- `POST /webhook/create-playbook` - Create new playbook
- `POST /webhook/update-playbook` - Update playbook
- `POST /webhook/validate-playbook` - Validate playbook
- `POST /webhook/test-playbook` - Test playbook

### Usage

#### Access Dashboard

1. Open in browser: `http://VM04_IP:5678/webhook/playbook-manager`
2. Dashboard will automatically load playbook list

#### Create New Playbook

1. Fill "Create New Playbook" form:
   - Playbook ID (e.g., `T1566-phishing`)
   - MITRE Technique ID (e.g., `T1566`)
   - Technique Name (e.g., `Phishing`)
   - Tactic (e.g., `Initial Access`)
   - Author
   - Description
   - Hypothesis
2. Click "Create Playbook"
3. System will create playbook from template and validate it

#### Validate Playbook

1. Click "Validate" button next to playbook
2. System will display validation results (errors and warnings)

#### Test Playbook

1. Click "Test" button next to playbook
2. System will run tests (validation, structure, query files)
3. Test results will be displayed

### Integration

- **PHASE1-06**: Uses Playbook Validator for validation
- **PHASE0-05**: Integration with Management Dashboard
- **API Endpoints**: Uses `/playbooks/*` endpoints from dashboard_api.py

### Usage Examples

#### Get Playbook List

```bash
curl http://VM04_IP:5678/webhook/list-playbooks
```

#### Create Playbook

```bash
curl -X POST http://VM04_IP:5678/webhook/create-playbook \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_id": "T1566-phishing",
    "technique_id": "T1566",
    "technique_name": "Phishing",
    "tactic": "Initial Access",
    "author": "Your Name",
    "description": "Detects phishing attempts",
    "hypothesis": "Adversaries may send phishing messages"
  }'
```

#### Validate Playbook

```bash
curl -X POST http://VM04_IP:5678/webhook/validate-playbook \
  -H "Content-Type: application/json" \
  -d '{"playbook_id": "T1566-phishing"}'
```

#### Test Playbook

```bash
curl -X POST http://VM04_IP:5678/webhook/test-playbook \
  -H "Content-Type: application/json" \
  -d '{"playbook_id": "T1566-phishing"}'
```

## Data Ingest Pipeline Workflow

### Installation

1. Import workflow `data-ingest-pipeline.json` to n8n
2. Activate workflow
3. Access pipeline: `http://VM04_IP:5678/webhook/data-pipeline`

### Features

- **End-to-End Pipeline**: Automatic data flow through all VMs
- **Query Generation**: Query generation for selected hunts
- **Data Ingestion**: Data ingestion (manual or API)
- **Data Storage**: Data storage to database on VM02
- **Playbook Execution**: Playbook execution on VM03
- **Results Aggregation**: Results aggregation in n8n

### Pipeline Flow

```
n8n (VM04) → Query Generation
    ↓
VM01 → Data Ingestion (optional)
    ↓
VM02 → Data Storage (with anonymization)
    ↓
VM03 → Playbook Execution
    ↓
n8n (VM04) → Results Aggregation
```

### Webhook Endpoints

- `GET /webhook/data-pipeline` - Pipeline dashboard (HTML)
- `POST /webhook/execute-pipeline` - Execute pipeline

### Usage

#### Access Pipeline

1. Open in browser: `http://VM04_IP:5678/webhook/data-pipeline`
2. Dashboard will automatically load available playbooks and tools

#### Execute Pipeline

1. **Select MITRE ATT&CK techniques**: Check boxes for techniques
2. **Select tools**: Check boxes for tools
3. **Select ingest mode**: 
   - **Manual**: Manual DataPackage upload
   - **API**: Automatic data retrieval via API
4. **Set options**: Check "Anonymize data before analysis" if needed
5. **Click "Execute Pipeline"**: System will execute full pipeline

#### Displaying Results

- Status of each pipeline stage
- Number of findings discovered
- Severity distribution of findings
- Execution details for each stage

### Integration

- **PHASE1-04**: Uses Hunt Selection Form for hunt selection
- **PHASE1-05**: Uses DataPackage for data standardization
- **PHASE2-01**: Uses Playbook Engine for analysis
- **PHASE0-01**: Uses Remote Execution Service for VM communication
- **PHASE1-03**: Uses DeterministicAnonymizer for anonymization

### Usage Examples

#### Execute Pipeline

```bash
curl -X POST http://VM04_IP:5678/webhook/execute-pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "technique_ids": ["T1566", "T1059"],
    "tool_names": ["Microsoft Defender for Endpoint", "Splunk"],
    "ingest_mode": "manual",
    "anonymize": true
  }'
```

### Pipeline Stages

1. **Stage 1: Query Generation** (VM04)
   - Generating queries for selected techniques and tools
   - Preparing queries for execution

2. **Stage 2: Data Ingestion** (VM01 - optional)
   - Executing queries via API
   - Parsing and data normalization
   - Creating DataPackage

3. **Stage 3: Data Storage** (VM02)
   - Data anonymization (if required)
   - Storage to PostgreSQL database
   - DataPackage validation

4. **Stage 4: Playbook Execution** (VM03)
   - Playbook execution via Playbook Engine
   - Data analysis with deterministic logic
   - Findings generation

5. **Stage 5: Results Aggregation** (VM04)
   - Aggregating results from all playbooks
   - Findings summary
   - Report preparation

## Future Enhancements

- [ ] Add API endpoints for all services
- [ ] Full authentication and authorization
- [ ] More metrics and charts
- [ ] Change history and logs
- [ ] Notifications (email, Slack, etc.)
- [ ] Automatic remediation actions
- [ ] Report export
- [ ] Scheduled tests
- [ ] Test results comparison (before/after)

## Support

For issues:
1. Check n8n documentation: https://docs.n8n.io
2. Check n8n logs: `docker logs n8n`
3. Check service logs in `logs/` directory
4. Check test results in `test_results/` directory
