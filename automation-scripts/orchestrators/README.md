# Orchestrators Module

This directory contains orchestration modules that coordinate end-to-end workflows and data pipelines across the Threat Hunting Automation Lab system.

## Overview

Orchestrators provide high-level coordination of complex workflows that span multiple VMs and services, managing the complete threat hunting pipeline from query generation to results aggregation.

## Orchestrators

### `pipeline_orchestrator.py`

**PipelineOrchestrator** - End-to-end data pipeline orchestration.

Orchestrates the complete data flow:
1. **n8n (VM04)**: Hunt selection, query generation
2. **VM01**: Data ingestion/parsing (optional)
3. **VM02**: Data storage in database with anonymization
4. **VM03**: Playbook execution and analysis
5. **n8n (VM04)**: Results aggregation

**Features:**
- Complete pipeline coordination
- Error handling and rollback
- Progress tracking
- Stage-by-stage execution
- Results aggregation

**Usage:**
```python
from automation_scripts.orchestrators.pipeline_orchestrator import PipelineOrchestrator

orchestrator = PipelineOrchestrator(config_path="configs/config.yml")
result = orchestrator.execute_pipeline(
    technique_ids=["T1566", "T1059"],
    tool_names=["Microsoft Defender for Endpoint"],
    ingest_mode="manual",
    anonymize=True
)
```

**Pipeline Stages:**
1. Query Generation - Generate queries for selected techniques
2. Data Ingestion - Collect data from sources (optional)
3. Data Storage - Store data in database with anonymization
4. Playbook Execution - Execute playbooks for analysis
5. Results Aggregation - Aggregate findings and generate reports

### `playbook_engine.py`

**PlaybookEngine** - Deterministic playbook execution engine.

Executes playbooks with deterministic analysis logic (no AI dependencies). Processes data packages and generates findings based on playbook rules.

**Features:**
- Deterministic analysis (no AI)
- Playbook execution
- Findings generation
- Integration with DataPackage
- Integration with DeterministicAnonymizer

**Usage:**
```python
from automation_scripts.orchestrators.playbook_engine import PlaybookEngine
from automation_scripts.utils.data_package import DataPackage

engine = PlaybookEngine()
package = DataPackage(source_type="manual", source_name="test")
findings = engine.execute_playbook("T1566-phishing", package)
```

**Execution Flow:**
1. Load playbook metadata and structure
2. Validate playbook
3. Process data package
4. Execute playbook analyzer logic
5. Generate findings
6. Return results

## Integration

Orchestrators integrate with:
- **Services**: RemoteExecutor, HealthMonitor, etc.
- **Utils**: QueryGenerator, DataPackage, DeterministicAnonymizer, PlaybookValidator
- **API**: Dashboard API endpoints
- **n8n**: Workflow automation

## Error Handling

Orchestrators raise custom exceptions:
- `PipelineOrchestratorError` - Pipeline orchestration errors
- `PipelineExecutionError` - Pipeline execution failures
- `PlaybookEngineError` - Playbook engine errors
- `PlaybookExecutionError` - Playbook execution failures

## Dependencies

Orchestrators depend on:
- All services from `services/`
- All utilities from `utils/`
- Configuration files
- Database access (for anonymization mapping)
- SSH access to all VMs

## Usage in n8n Workflows

Orchestrators are primarily used by n8n workflows on VM-04:
- Data Ingest Pipeline workflow
- Playbook execution workflows
- End-to-end threat hunting workflows

## Best Practices

1. **Error Handling**: Always handle exceptions and provide rollback mechanisms
2. **Logging**: Comprehensive logging for debugging and audit trails
3. **Progress Tracking**: Track progress through pipeline stages
4. **Resource Management**: Proper cleanup of temporary files and connections
5. **Validation**: Validate inputs at each stage before proceeding

