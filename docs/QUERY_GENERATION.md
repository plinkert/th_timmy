# Query Generation Guide for Threat Hunters

## Overview

This guide explains how to use the Query Generator to create ready-to-use queries for threat hunting. The Query Generator automatically creates queries based on your selected MITRE ATT&CK techniques and available SIEM/EDR tools.

## What is Query Generation?

Query Generation automatically creates queries that you can use in your SIEM/EDR tools to hunt for specific threats. Instead of writing queries manually, the system generates them based on:

- **MITRE ATT&CK Techniques**: Which threats you want to hunt for
- **Your Tools**: Which SIEM/EDR tools you have (Splunk, Sentinel, Defender, etc.)
- **Playbooks**: Pre-defined hunting playbooks with query templates

## Quick Start

### Using Hunt Selection Form (Recommended)

1. **Access Hunt Selection Form**
   - Open n8n: `http://<VM-04_IP>:5678`
   - Navigate to "Hunt Selection Form" workflow
   - Open webhook: `http://<VM-04_IP>:5678/webhook/hunt-selection`

2. **Select Techniques**
   - Check boxes for MITRE ATT&CK techniques you want to hunt
   - Example: T1566 (Phishing), T1059 (Command and Scripting Interpreter)

3. **Select Tools**
   - Check boxes for tools you have access to
   - Example: Microsoft Defender, Splunk, Sentinel

4. **Generate Queries**
   - Click "Generate Queries" button
   - System generates queries for all combinations
   - Review and copy queries

5. **Use Queries**
   - Copy each query
   - Paste into your SIEM/EDR tool
   - Execute and review results

## Understanding Generated Queries

### Query Structure

Each generated query includes:

- **Query Text**: The actual query ready to copy-paste
- **Tool Name**: Which tool the query is for
- **Technique ID**: MITRE ATT&CK technique (e.g., T1566)
- **Description**: What the query hunts for
- **Instructions**: How to execute the query

### Query Formats

Different tools use different query languages:

- **Microsoft Defender for Endpoint**: KQL (Kusto Query Language)
- **Microsoft Sentinel**: KQL (Kusto Query Language)
- **Splunk**: SPL (Splunk Processing Language)
- **Elasticsearch**: JSON queries
- **Generic SIEM**: Text-based queries

### Example Queries

#### Microsoft Defender for Endpoint (KQL)

```kql
DeviceProcessEvents
| where TimeGenerated > ago(7d)
| where ProcessCommandLine contains "powershell" 
    and ProcessCommandLine contains "-enc"
| project TimeGenerated, DeviceName, ProcessCommandLine, AccountName
```

#### Splunk (SPL)

```spl
index=security 
| search "powershell" AND "-enc" 
| stats count by host, user, command
| where count > 5
```

## Query Parameters

### Time Range

Queries include time range parameters that you can customize:

- **Default**: Usually 7 days (`ago(7d)` or `time_range=7d`)
- **Customize**: Change to match your needs (1h, 24h, 7d, 30d)
- **Consistency**: Use same time range across related queries

**Example:**
```kql
// Change from:
| where TimeGenerated > ago(7d)

// To:
| where TimeGenerated > ago(30d)  // Last 30 days
```

### Other Parameters

Some queries include additional parameters:

- **Severity**: Filter by severity level
- **Index**: Log index name (for Splunk/Elasticsearch)
- **Workspace**: Workspace name (for Sentinel)

## Using Generated Queries

### Step 1: Review Query

Before executing, review the query:

1. **Check Syntax**: Ensure query syntax is correct for your tool
2. **Verify Parameters**: Check time ranges and other parameters
3. **Understand Logic**: Understand what the query is looking for
4. **Customize if Needed**: Adjust for your environment

### Step 2: Execute in Your Tool

1. **Open Your SIEM/EDR Tool**
   - Microsoft Defender: Advanced Hunting
   - Sentinel: Log Analytics
   - Splunk: Search interface
   - Elasticsearch: Dev Tools

2. **Paste Query**
   - Copy the entire query
   - Paste into query interface
   - Verify query is complete

3. **Adjust Parameters**
   - Update time range if needed
   - Adjust other parameters for your environment
   - Add filters if necessary

4. **Execute Query**
   - Click "Run" or "Execute"
   - Wait for results
   - Review result count

### Step 3: Export Results

1. **Review Results**
   - Check if results are reasonable
   - Review sample records
   - Verify data quality

2. **Export Data**
   - Export as CSV or JSON
   - Include all relevant fields
   - Save with descriptive filename

3. **Document**
   - Note which technique the query was for
   - Record execution time
   - Note any modifications made

## Query Modes

### Manual Mode (Default)

**When to Use:**
- You want to execute queries manually
- You need to review queries before execution
- You want to customize queries

**Features:**
- Queries ready for copy-paste
- Step-by-step instructions included
- Human-readable format

**Example:**
```python
# Generate queries in manual mode
result = generator.generate_queries(
    technique_ids=["T1566"],
    tool_names=["Microsoft Defender for Endpoint"],
    mode="manual"
)
```

### API Mode

**When to Use:**
- You have API access to your tools
- You want automated query execution
- You're integrating with automation

**Features:**
- API endpoint information included
- Authentication details
- Programmatic execution format

**Note:** API mode requires API configuration and credentials.

## Customizing Queries

### Why Customize?

Generated queries are starting points. You may need to customize for:

- **Your Environment**: Different field names or data sources
- **Specific Requirements**: Additional filters or conditions
- **Performance**: Optimize for your data volume
- **Compliance**: Add compliance-related filters

### How to Customize

1. **Copy Generated Query**
2. **Modify in Your Tool**
   - Add additional filters
   - Adjust time ranges
   - Add field selections
3. **Test Modified Query**
4. **Document Changes**: Note what you changed and why

### Example Customization

**Original Query:**
```kql
DeviceProcessEvents
| where TimeGenerated > ago(7d)
| where ProcessCommandLine contains "powershell"
```

**Customized Query:**
```kql
DeviceProcessEvents
| where TimeGenerated > ago(30d)  // Changed time range
| where ProcessCommandLine contains "powershell"
| where DeviceName startswith "SERVER"  // Added filter
| where AccountName != "SYSTEM"  // Excluded system accounts
```

## Best Practices

### Query Generation

1. **Select Relevant Techniques**: Choose techniques relevant to your threat landscape
2. **Use Multiple Tools**: Generate queries for all available tools
3. **Review Before Execution**: Always review queries before running
4. **Document Modifications**: Note any changes you make

### Query Execution

1. **Start with Small Time Ranges**: Test with 1-7 days first
2. **Monitor Performance**: Watch query execution time
3. **Validate Results**: Ensure results make sense
4. **Export Properly**: Export all relevant fields

### Query Management

1. **Organize Queries**: Keep track of which queries you've executed
2. **Version Control**: Save modified queries for future use
3. **Share Knowledge**: Share effective queries with team
4. **Regular Updates**: Update queries as playbooks are updated

## Troubleshooting

### No Queries Generated

**Problem**: System doesn't generate queries for selected techniques/tools.

**Solutions:**
- Check if playbooks exist for selected techniques
- Verify tool names match exactly (case-sensitive)
- Review playbook structure in `playbooks/` directory
- Check if queries are defined in playbook metadata.yml

### Queries Use Templates

**Problem**: Generated queries look generic or use template format.

**Explanation**: This is normal when playbook-specific queries aren't available. Templates provide basic structure.

**Solutions:**
- Customize template queries for your needs
- Add specific queries to playbook metadata.yml
- Use templates as starting points

### Queries Don't Work in My Tool

**Problem**: Generated queries fail to execute in your tool.

**Solutions:**
- Check query syntax for your tool version
- Verify field names match your data schema
- Review tool-specific requirements
- Test with simpler query first
- Check tool documentation for syntax

### Parameter Replacement Not Working

**Problem**: Placeholders like `{{time_range}}` aren't replaced.

**Solutions:**
- Ensure parameters are provided in request
- Check placeholder format (should be `{{param}}`)
- Verify parameter names match exactly
- Review query template structure

## Advanced Usage

### Programmatic Query Generation

If you're using the system programmatically:

```python
from automation_scripts.utils.query_generator import QueryGenerator

# Initialize generator
generator = QueryGenerator()

# Generate queries
result = generator.generate_queries(
    technique_ids=["T1566", "T1059"],
    tool_names=["Microsoft Defender for Endpoint", "Splunk"],
    mode="manual",
    parameters={
        "time_range": "30d",
        "severity": "high"
    }
)

# Access queries
for technique_id, technique_data in result['queries'].items():
    for tool_name, query_data in technique_data['tools'].items():
        query = query_data['query']
        print(f"{technique_id} - {tool_name}: {query}")
```

### Discovering Available Queries

```python
# Get all available playbooks
playbooks = generator.discover_playbooks()

# Get playbooks for specific techniques
playbooks = generator.get_playbooks_for_techniques(["T1566"])

# Get available tools
tools = generator.get_available_tools()
```

### Query Summary

```python
# Get summary of all queries
summary = generator.get_query_summary()

# Get summary for specific techniques
summary = generator.get_query_summary(technique_ids=["T1566"])

# Get summary for specific tools
summary = generator.get_query_summary(tool_names=["Splunk"])
```

## Integration with Complete Hunt Workflow

When using Complete Hunt Workflow:

1. **Queries are Generated Automatically**: No need to generate separately
2. **Queries are Executed**: If using API mode, queries execute automatically
3. **Results are Processed**: Query results are automatically processed
4. **Findings are Generated**: System analyzes results and generates findings

## Query Sources

### Playbook Queries (Preferred)

Queries defined in playbook `metadata.yml` files:
- Technique-specific
- Tool-optimized
- Tested and validated

### Template Queries (Fallback)

Base templates used when playbook queries aren't available:
- Generic structure
- Customizable
- Starting point for development

## Examples

### Example 1: Single Technique Hunt

**Goal**: Hunt for Phishing (T1566) using Microsoft Defender

1. Select technique: T1566
2. Select tool: Microsoft Defender for Endpoint
3. Generate query
4. Execute in Defender Advanced Hunting
5. Review results

### Example 2: Multi-Technique Hunt

**Goal**: Hunt for multiple Initial Access techniques

1. Select techniques: T1566, T1078, T1133
2. Select tools: All available
3. Generate all queries
4. Execute queries in parallel
5. Correlate results

### Example 3: Tool-Specific Hunt

**Goal**: Use only Splunk for all hunts

1. Select all relevant techniques
2. Select only Splunk
3. Generate Splunk queries
4. Execute in Splunk
5. Analyze aggregated results

## Summary

Query Generation automates the creation of threat hunting queries, saving time and ensuring consistency. Key points:

- **Automatic Generation**: System generates queries based on techniques and tools
- **Multiple Formats**: Supports various SIEM/EDR tools
- **Customizable**: Queries can be modified for your environment
- **Integrated**: Works seamlessly with Complete Hunt Workflow
- **Best Practices**: Review, customize, and document queries

**Next Steps:**
- Practice generating queries for different techniques
- Execute queries in your tools
- Customize queries for your environment
- Use Complete Hunt Workflow for end-to-end automation

