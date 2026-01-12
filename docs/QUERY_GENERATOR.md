# Query Generator Documentation

## Overview

The Query Generator automatically generates ready-to-use queries for threat hunting based on:
- Selected MITRE ATT&CK techniques
- Available SIEM/EDR tools
- Playbook metadata
- User parameters (time range, severity, etc.)

## Features

- **Automatic Discovery**: Discovers all available playbooks and their queries
- **Multi-Tool Support**: Supports Microsoft Defender, Sentinel, Splunk, Elasticsearch, and generic SIEM
- **Dual Mode**: Generates queries for both manual execution and API automation
- **Parameter Replacement**: Automatically replaces placeholders ({{time_range}}, etc.) with actual values
- **Template Fallback**: Uses base templates when playbook-specific queries are not available
- **User-Friendly**: Simple API designed for non-technical users

## Usage

### Basic Usage

```python
from automation_scripts.utils.query_generator import QueryGenerator

# Initialize generator
generator = QueryGenerator()

# Generate queries for specific techniques and tools
result = generator.generate_queries(
    technique_ids=["T1566", "T1059"],
    tool_names=["Microsoft Defender for Endpoint", "Splunk"],
    mode="manual",
    parameters={
        "time_range": "30d",
        "severity": "high"
    }
)

# Access generated queries
for technique_id, technique_data in result['queries'].items():
    print(f"Technique: {technique_id}")
    for tool_name, query_data in technique_data['tools'].items():
        print(f"  Tool: {tool_name}")
        print(f"  Query:\n{query_data['query']}")
```

### Discover Available Playbooks

```python
# Get all playbooks
playbooks = generator.discover_playbooks()

# Get playbooks for specific techniques
playbooks = generator.get_playbooks_for_techniques(["T1566", "T1059"])

# Get available tools
tools = generator.get_available_tools()
```

### Get Query Summary

```python
# Get summary of all queries
summary = generator.get_query_summary()

# Get summary for specific techniques
summary = generator.get_query_summary(technique_ids=["T1566"])

# Get summary for specific tools
summary = generator.get_query_summary(tool_names=["Microsoft Defender for Endpoint"])
```

## Query Modes

### Manual Mode

Queries generated in manual mode are designed for:
- Copy-paste into tool interfaces
- Manual execution by threat hunters
- Step-by-step instructions included

Example:
```python
result = generator.generate_queries(
    technique_ids=["T1566"],
    tool_names=["Microsoft Defender for Endpoint"],
    mode="manual"
)
```

### API Mode

Queries generated in API mode are designed for:
- Automated execution via API
- Programmatic query execution
- API endpoint and authentication information included

Example:
```python
result = generator.generate_queries(
    technique_ids=["T1566"],
    tool_names=["Microsoft Defender for Endpoint"],
    mode="api",
    parameters={
        "time_range": "7d",
        "severity": "high"
    }
)
```

## Parameters

Common parameters that can be customized:

- **time_range**: Time range for analysis (e.g., "7d", "30d", "1h")
- **severity**: Minimum severity level (low, medium, high, critical)
- **index**: Log index name (for Splunk, Elasticsearch)
- **workspace**: Workspace name (for Microsoft Sentinel)

Parameters are automatically replaced in queries using placeholders like `{{time_range}}`.

## Supported Tools

- **Microsoft Defender for Endpoint**: KQL queries
- **Microsoft Sentinel**: KQL queries
- **Splunk**: SPL queries
- **Elasticsearch**: JSON queries
- **Generic SIEM**: Text-based templates

## Query Sources

Queries can come from two sources:

1. **Playbook Queries**: Queries defined in playbook `metadata.yml` files
2. **Template Queries**: Base templates from `QueryTemplates` class (used as fallback)

The generator prioritizes playbook queries and falls back to templates when needed.

## Error Handling

The generator includes comprehensive error handling:

- Missing playbooks: Returns warnings instead of errors
- Missing query files: Falls back to templates
- Unsupported tools: Returns warnings
- Invalid parameters: Raises `QueryGeneratorError`

## Integration Examples

### With Management Dashboard

```python
# In dashboard API endpoint
from automation_scripts.utils.query_generator import QueryGenerator

generator = QueryGenerator()
queries = generator.generate_queries(
    technique_ids=selected_techniques,
    tool_names=available_tools,
    mode="manual"
)
# Return queries to frontend
```

### With n8n Workflow

```python
# In n8n workflow node
from automation_scripts.utils.query_generator import QueryGenerator

generator = QueryGenerator()
result = generator.generate_queries(
    technique_ids=$json.techniques,
    tool_names=$json.tools,
    mode=$json.mode
)
# Use result in workflow
```

## Best Practices

1. **Always specify parameters**: Provide time_range and other parameters for better results
2. **Check warnings**: Review warnings in result for missing queries or tools
3. **Use appropriate mode**: Use "manual" for human execution, "api" for automation
4. **Validate queries**: Review generated queries before execution
5. **Customize as needed**: Generated queries are starting points, customize for your environment

## Troubleshooting

### No queries generated

- Check if playbooks exist for selected techniques
- Verify tool names match exactly (case-sensitive)
- Check playbook metadata.yml structure

### Template queries used

- This is normal when playbook-specific queries are not available
- Templates provide basic structure that can be customized
- Consider adding queries to playbook metadata.yml

### Parameter replacement not working

- Ensure parameters are provided in the parameters dictionary
- Check placeholder format in queries (should be {{param}} or {{{{param}}}})
- Verify parameter names match exactly

## API Reference

### QueryGenerator

#### `__init__(playbooks_dir=None, logger=None)`
Initialize query generator.

#### `discover_playbooks() -> List[Dict]`
Discover all available playbooks.

#### `get_playbooks_for_techniques(technique_ids: List[str]) -> List[Dict]`
Get playbooks for specified MITRE techniques.

#### `get_available_tools(playbooks=None) -> List[str]`
Get list of available tools from playbooks.

#### `generate_queries(technique_ids, tool_names, mode="manual", parameters=None) -> Dict`
Generate queries for specified techniques and tools.

#### `get_query_summary(technique_ids=None, tool_names=None) -> Dict`
Get summary of available queries.

### QueryTemplates

#### `get_template(tool, mode, technique_id=None, technique_name=None) -> str`
Get base query template for a tool and mode.

#### `get_tool_from_name(tool_name: str) -> Optional[QueryTool]`
Convert tool name string to QueryTool enum.

## Examples

See `playbooks/template/` for example playbook structure with queries.

See `tests/` for unit and integration test examples.

