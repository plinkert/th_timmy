# Threat Hunting Lab - User Guide for Hunters

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Accessing the System](#accessing-the-system)
4. [Working with Playbooks](#working-with-playbooks)
5. [Data Analysis](#data-analysis)
6. [AI-Assisted Analysis](#ai-assisted-analysis)
7. [Report Generation](#report-generation)
8. [Anonymization and Deanonymization](#anonymization-and-deanonymization)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## Overview

This guide is designed for threat hunters using the Threat Hunting Lab system. It provides step-by-step instructions for performing threat hunting operations, executing playbooks, analyzing data, and generating reports.

### System Components

- **VM-03 (JupyterLab)**: Interactive analysis environment
- **VM-02 (PostgreSQL)**: Data storage and queries
- **VM-04 (n8n)**: Workflow automation (optional for advanced users)
- **VM-01**: Data collection (background process)

### Key Features

- MITRE ATT&CK-based playbooks
- Interactive JupyterLab notebooks
- AI-assisted analysis (ChatGPT-5+)
- Automated report generation
- Deterministic anonymization
- Deanonymization for authorized users

## Getting Started

### Prerequisites

- Access credentials to VM-03 (JupyterLab)
- Network access to the lab environment
- Basic knowledge of threat hunting concepts
- Familiarity with Python and SQL (helpful but not required)

### Initial Setup

1. **Obtain Access**:
   - Contact system administrator for JupyterLab access
   - Receive access token or password
   - Verify network connectivity

2. **Access JupyterLab**:
   - Open browser: `http://VM03_IP:8888`
   - Enter token or password
   - Verify access to notebooks

3. **Familiarize with Interface**:
   - Explore notebook structure
   - Review available playbooks
   - Check data access

## Accessing the System

### JupyterLab Access

**URL**: `http://VM03_IP:8888`

**Authentication**:
- Token-based (recommended)
- Password-based (optional)

**Finding Your Token**:
- Provided by administrator
- Or check JupyterLab logs
- Or generate new token: `jupyter lab --generate-config`

### Database Access

**Connection Details**:
- Host: VM-02 IP address
- Port: 5432
- Database: `threat_hunting`
- User: `threat_hunter`
- Password: (provided by administrator)

**Connection from JupyterLab**:
```python
import psycopg2
from sqlalchemy import create_engine

# Using psycopg2
conn = psycopg2.connect(
    host="VM02_IP",
    port=5432,
    database="threat_hunting",
    user="threat_hunter",
    password="your_password"
)

# Using SQLAlchemy
engine = create_engine(
    f"postgresql://threat_hunter:password@VM02_IP:5432/threat_hunting"
)
```

### n8n Access (Optional)

**URL**: `http://VM04_IP:5678`

**Authentication**:
- Username: (provided by administrator)
- Password: (provided by administrator)

**Use Cases**:
- Automated workflow execution
- Scheduled playbook runs
- Data collection automation

## Working with Playbooks

### Playbook Structure

Playbooks are organized by MITRE ATT&CK tactics and techniques:

```
playbooks/
├── initial-access/
├── execution/
├── persistence/
├── privilege-escalation/
├── defense-evasion/
├── credential-access/
├── discovery/
├── lateral-movement/
├── collection/
├── exfiltration/
└── command-and-control/
```

### Executing a Playbook

1. **Select Playbook**:
   - Navigate to playbook directory
   - Open playbook notebook (`.ipynb`)

2. **Review Playbook**:
   - Read hypothesis
   - Understand data sources
   - Review queries

3. **Configure Playbook**:
   - Set date ranges
   - Configure filters
   - Adjust parameters

4. **Execute Playbook**:
   - Run cells sequentially
   - Review intermediate results
   - Analyze findings

5. **Generate Report**:
   - Execute report generation cell
   - Review report
   - Export if needed

### Playbook Types

#### Hypothesis-Based Hunts

**Purpose**: Test specific threat hypotheses

**Structure**:
- Hypothesis statement
- Data source identification
- Query construction
- Result analysis
- Conclusion

**Example**:
```python
# Hypothesis: Adversaries are using PowerShell for execution
hypothesis = "Adversaries are using PowerShell for execution and evasion"

# Query for PowerShell execution
query = """
SELECT * FROM events
WHERE process_name LIKE '%powershell%'
AND timestamp >= '2024-01-01'
ORDER BY timestamp DESC
"""
```

#### Baseline Hunts

**Purpose**: Establish baseline of normal behavior

**Structure**:
- Baseline definition
- Data collection
- Statistical analysis
- Anomaly detection
- Reporting

#### Model-Assisted Hunts

**Purpose**: Use ML models for anomaly detection

**Structure**:
- Model selection
- Feature engineering
- Model execution
- Anomaly identification
- Investigation

### Creating Custom Playbooks

1. **Create Notebook**:
   - New notebook in appropriate directory
   - Use playbook template

2. **Define Hypothesis**:
   - Clear hypothesis statement
   - Scope definition
   - Success criteria

3. **Write Queries**:
   - SQL queries for data extraction
   - Filter and aggregation
   - Time range selection

4. **Analyze Results**:
   - Data visualization
   - Statistical analysis
   - Pattern identification

5. **Document Findings**:
   - Document results
   - Create visualizations
   - Generate report

## Data Analysis

### Querying the Database

**Basic Query**:
```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql://user:pass@host:5432/db")

query = """
SELECT 
    timestamp,
    event_type,
    source_ip,
    process_name,
    command_line
FROM events
WHERE timestamp >= '2024-01-01'
AND timestamp < '2024-01-02'
ORDER BY timestamp DESC
LIMIT 1000
"""

df = pd.read_sql(query, engine)
```

### Common Analysis Patterns

#### Time-Based Analysis

```python
# Events per hour
df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
hourly_counts = df.groupby('hour').size()

# Events over time
df['date'] = pd.to_datetime(df['timestamp']).dt.date
daily_counts = df.groupby('date').size()
```

#### Source Analysis

```python
# Top source IPs
top_sources = df['source_ip'].value_counts().head(10)

# Top processes
top_processes = df['process_name'].value_counts().head(10)
```

#### Correlation Analysis

```python
# Correlate events by user
user_events = df.groupby('user_id').agg({
    'event_type': 'count',
    'source_ip': 'nunique'
})
```

### Data Visualization

**Using matplotlib**:
```python
import matplotlib.pyplot as plt

# Time series plot
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp').resample('H').size().plot()
plt.title('Events Over Time')
plt.xlabel('Time')
plt.ylabel('Event Count')
plt.show()
```

**Using seaborn**:
```python
import seaborn as sns

# Distribution plot
sns.distplot(df['hour'])
plt.title('Event Distribution by Hour')
plt.show()
```

## AI-Assisted Analysis

### ChatGPT-5+ Integration

**Purpose**: Get AI assistance for analysis and interpretation

**Usage**:
```python
from openai import OpenAI

client = OpenAI(api_key="your_api_key")

# Analyze findings
response = client.chat.completions.create(
    model="gpt-5",
    messages=[
        {"role": "system", "content": "You are a threat hunting expert."},
        {"role": "user", "content": f"Analyze these findings: {findings}"}
    ]
)

print(response.choices[0].message.content)
```

### AI Use Cases

1. **Query Generation**:
   - Generate SQL queries from natural language
   - Optimize existing queries
   - Suggest query improvements

2. **Result Interpretation**:
   - Interpret analysis results
   - Identify patterns
   - Suggest next steps

3. **Report Writing**:
   - Generate report summaries
   - Create executive summaries
   - Format findings

4. **Threat Intelligence**:
   - Correlate with threat intelligence
   - Identify IOCs
   - Suggest mitigation strategies

## Report Generation

### Automated Report Generation

**Using Report Template**:
```python
from report_generator import generate_report

report = generate_report(
    title="Threat Hunt: PowerShell Execution",
    hypothesis="Adversaries using PowerShell for execution",
    findings=findings_df,
    conclusions=["Found 15 suspicious PowerShell executions"],
    recommendations=["Investigate source IPs", "Review command lines"]
)

# Save report
report.save("powershell_hunt_report.html")
```

### Report Components

1. **Executive Summary**:
   - Hunt overview
   - Key findings
   - Risk assessment

2. **Methodology**:
   - Hypothesis
   - Data sources
   - Analysis approach

3. **Findings**:
   - Detailed findings
   - Visualizations
   - Supporting data

4. **Conclusions**:
   - Summary of findings
   - Threat assessment
   - Recommendations

### Export Formats

- **HTML**: Interactive web report
- **PDF**: Printable report
- **JSON**: Machine-readable format
- **CSV**: Tabular data export

## Anonymization and Deanonymization

### Understanding Anonymization

**Anonymized Fields**:
- IP addresses
- User identifiers
- Email addresses
- File paths (with usernames)

**Anonymized Format**:
- Hash-based values (e.g., `a1b2c3d4e5f6...`)
- Deterministic (same input → same output)
- Enables correlation across datasets

### Working with Anonymized Data

**Normal Operations**:
- Analysis works with anonymized data
- Correlation still possible
- Patterns still identifiable

**Example**:
```python
# Anonymized IPs can still be correlated
df.groupby('source_ip').size()  # Works with anonymized IPs
```

### Requesting Deanonymization

**Authorization Required**:
- Request through system interface
- Approval from authorized personnel
- Time-limited access

**Process**:
1. Identify need for deanonymization
2. Submit request with justification
3. Wait for approval
4. Access deanonymized data
5. Access expires after time limit

**Example Request**:
```python
from deanonymization import request_deanonymization

# Request deanonymization
result = request_deanonymization(
    anonymized_value="a1b2c3d4e5f6...",
    field_type="ip_address",
    reason="Investigation of suspicious activity",
    user="hunter_username"
)

if result.approved:
    original_value = result.original_value
    print(f"Original IP: {original_value}")
```

## Best Practices

### Threat Hunting Best Practices

1. **Start with Hypothesis**:
   - Clear hypothesis statement
   - Defined scope
   - Success criteria

2. **Use Playbooks**:
   - Leverage existing playbooks
   - Customize as needed
   - Document modifications

3. **Iterative Analysis**:
   - Start broad, narrow down
   - Refine queries based on results
   - Document findings

4. **Collaboration**:
   - Share findings with team
   - Review playbooks
   - Learn from others

### Data Analysis Best Practices

1. **Query Optimization**:
   - Use appropriate date ranges
   - Limit result sets
   - Use indexes effectively

2. **Data Validation**:
   - Verify data completeness
   - Check for anomalies
   - Validate results

3. **Documentation**:
   - Document queries
   - Explain analysis steps
   - Record findings

### Security Best Practices

1. **Access Control**:
   - Use strong passwords/tokens
   - Don't share credentials
   - Report suspicious activity

2. **Data Handling**:
   - Respect anonymization
   - Request deanonymization only when needed
   - Follow data retention policies

3. **Reporting**:
   - Include necessary context
   - Protect sensitive information
   - Follow reporting procedures

## Troubleshooting

### Common Issues

#### Cannot Connect to JupyterLab

**Symptoms**: Cannot access JupyterLab interface

**Solutions**:
- Verify network connectivity
- Check firewall rules
- Verify token/password
- Contact administrator

#### Database Connection Errors

**Symptoms**: Cannot connect to PostgreSQL

**Solutions**:
- Verify database credentials
- Check network connectivity
- Verify firewall rules
- Check database service status

#### Query Performance Issues

**Symptoms**: Queries run slowly or timeout

**Solutions**:
- Reduce date range
- Add appropriate filters
- Limit result set size
- Check database indexes
- Optimize query structure

#### Anonymization Issues

**Symptoms**: Cannot correlate anonymized data

**Solutions**:
- Verify deterministic anonymization
- Check salt consistency
- Review anonymization configuration
- Contact administrator

### Getting Help

1. **Documentation**:
   - Review this guide
   - Check architecture documentation
   - Review playbook examples

2. **Support**:
   - Contact system administrator
   - Review system logs
   - Check known issues

3. **Community**:
   - Share with team
   - Review playbooks
   - Learn from others

## References

- [Architecture Documentation](ARCHITECTURE_ENHANCED.md)
- [Data Flow Documentation](DATA_FLOW.md)
- [Anonymization Policy](ANONYMIZATION.md)
- [Configuration Guide](CONFIGURATION.md)

## Appendix

### Quick Reference

**Common Queries**:
```sql
-- Recent events
SELECT * FROM events 
WHERE timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Top processes
SELECT process_name, COUNT(*) as count
FROM events
GROUP BY process_name
ORDER BY count DESC
LIMIT 10;

-- Events by user
SELECT user_id, COUNT(*) as count
FROM events
GROUP BY user_id
ORDER BY count DESC;
```

**Useful Python Snippets**:
```python
# Load data
df = pd.read_sql(query, engine)

# Basic statistics
df.describe()

# Filter data
filtered = df[df['event_type'] == 'process_execution']

# Group by
grouped = df.groupby('source_ip').size()
```
