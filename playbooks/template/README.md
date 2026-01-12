# Playbook Template

This is a template for creating new Threat Hunting playbooks based on MITRE ATT&CK framework.

## Structure

```
playbook-name/
├── README.md              # Playbook description (this file)
├── metadata.yml           # Playbook metadata with queries
├── playbook.ipynb         # Main playbook (Jupyter notebook) - optional
├── queries/               # SIEM/EDR queries
│   ├── microsoft_defender_manual.kql
│   ├── microsoft_defender_api.kql
│   ├── microsoft_sentinel_manual.kql
│   ├── microsoft_sentinel_api.kql
│   ├── splunk_manual.spl
│   ├── splunk_api.spl
│   ├── elasticsearch_manual.json
│   ├── elasticsearch_api.json
│   └── generic_siem_manual.txt
├── scripts/               # Python scripts
│   ├── normalizer.py      # Normalization (optional)
│   ├── transformer.py     # Transformation (optional)
│   └── analyzer.py        # Analysis (REQUIRED for Master Playbook)
├── config/                # Configuration
│   └── thresholds.yml     # Thresholds and parameters
├── tests/                 # Tests
│   └── test_playbook.py
└── examples/              # Example data
    └── sample_data.csv
```

## Creating a New Playbook

### Step 1: Copy Template

```bash
cd playbooks
cp -r template T####-technique-name
cd T####-technique-name
```

### Step 2: Edit metadata.yml

The `metadata.yml` file contains all playbook information including queries for different SIEM/EDR tools.

#### Basic Information

```yaml
playbook:
  id: "T1566-phishing-account-compromise"
  name: "Phishing Account Compromise Detection"
  version: "1.0.0"
  author: "Your Name"
  created: "2025-01-XX"
  updated: "2025-01-XX"
  description: |
    Brief description of what this playbook detects.
```

#### MITRE ATT&CK Information

```yaml
mitre:
  technique_id: "T1566"
  technique_name: "Phishing"
  tactic: "Initial Access"
  sub_techniques:
    - "T1566.001"
    - "T1566.002"
```

#### Hypothesis

```yaml
hypothesis: |
  Adversaries may send phishing messages to gain access to victim systems.
  This playbook detects suspicious account activities following potential
  phishing attempts.
```

#### Data Sources with Queries

The `data_sources` section defines which tools this playbook supports and includes queries for each tool.

Each data source can have two types of queries:
- **manual**: For manual execution in the tool's interface
- **api**: For automated execution via API

Example:

```yaml
data_sources:
  - name: "Microsoft Defender for Endpoint"
    type: "EDR"
    required: true
    queries:
      manual:
        - name: "Basic Detection Query"
          description: "Query to detect suspicious process execution"
          file: "queries/microsoft_defender_manual.kql"
          parameters:
            time_range: "7d"
          expected_fields:
            - TimeGenerated
            - DeviceName
            - ProcessName
          instructions: |
            Step-by-step instructions for manual execution...
      api:
        - name: "API Detection Query"
          description: "Query for automated execution via API"
          file: "queries/microsoft_defender_api.kql"
          api_endpoint: "https://api.security.microsoft.com/v1.0/advancedHunting/run"
          api_method: "POST"
          instructions: |
            This query is executed automatically by the system.
```

### Step 3: Customize Queries

Edit the query files in the `queries/` directory:

1. **Microsoft Defender**: Edit `.kql` files
2. **Microsoft Sentinel**: Edit `.kql` files
3. **Splunk**: Edit `.spl` files
4. **Elasticsearch**: Edit `.json` files
5. **Generic SIEM**: Edit `.txt` file

Each query file should:
- Include comments explaining what the query does
- Use placeholders like `{{time_range}}` for parameters (in API queries)
- Include instructions for manual execution (in manual queries)

### Step 4: Implement Analyzer

**scripts/analyzer.py** - REQUIRED for Master Playbook:

```python
from typing import List, Dict, Any

def analyze(normalized_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze normalized data for threats
    
    Args:
        normalized_data: List of normalized records
        
    Returns:
        List of findings
    """
    findings = []
    
    for record in normalized_data:
        # Your analysis logic
        if is_suspicious(record):
            findings.append({
                'technique': 'T1566',
                'severity': 'high',
                'description': 'Suspicious activity detected',
                'evidence': record['normalized_fields'],
                'timestamp': record['timestamp']
            })
    
    return findings
```

### Step 5: Test Playbook

```bash
# In the playbook directory
python3 -m pytest tests/test_playbook.py
```

## Using Queries

### Manual Execution

1. **Open the tool** (Microsoft Defender, Splunk, etc.)
2. **Navigate to query interface** (Advanced Hunting, Search, etc.)
3. **Copy the query** from the appropriate file in `queries/`
4. **Paste and adjust** parameters (time range, filters, etc.)
5. **Execute** the query
6. **Export results** as CSV or JSON
7. **Upload** results to the system for analysis

### Automated Execution (API)

Queries marked as `api` in `metadata.yml` are executed automatically by the system:

1. The **query_generator** service reads the query from `metadata.yml`
2. It replaces placeholders (like `{{time_range}}`) with actual values
3. It authenticates to the tool's API
4. It executes the query via API
5. It retrieves and processes the results

No manual steps required!

## Query Parameters

Common parameters used in queries:

- **time_range**: Time range for analysis (e.g., "7d", "30d", "1h")
- **severity**: Minimum severity level (low, medium, high, critical)
- **index**: Log index name (for Splunk, Elasticsearch)
- **workspace**: Workspace name (for Microsoft Sentinel)

These parameters are defined in `metadata.yml` and can be customized per query.

## Expected Fields

Each query defines `expected_fields` - the fields that should be present in the results:

```yaml
expected_fields:
  - TimeGenerated
  - DeviceName
  - ProcessName
  - ProcessCommandLine
```

These fields are used by the system to:
- Validate query results
- Map results to the normalized schema
- Ensure all required data is present

## Best Practices

1. **Clear Descriptions**: Write clear descriptions for each query explaining what it detects
2. **Step-by-Step Instructions**: Provide detailed instructions for manual execution
3. **Parameter Documentation**: Document all parameters and their possible values
4. **Example Values**: Include example values in query comments
5. **Error Handling**: Consider edge cases and error scenarios
6. **Performance**: Optimize queries for performance (limit results, use indexes)

## Integration with System

Playbooks are automatically discovered by the system if:

1. They have a valid `metadata.yml` with queries defined
2. They have `scripts/analyzer.py` with `analyze(data)` function
3. Query files referenced in `metadata.yml` exist in `queries/` directory

The system will:
- Discover available playbooks
- Generate query recommendations based on selected tools
- Map query results to appropriate playbooks
- Execute playbooks sequentially
- Aggregate findings

## Support

For questions or issues:
- Check the main project documentation: `docs/`
- Review example playbooks in `playbooks/`
- Contact the development team

