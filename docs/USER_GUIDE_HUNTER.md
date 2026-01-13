# User Guide for Threat Hunters

## Overview

This guide is designed for threat hunters who use the Threat Hunting Automation Lab to conduct systematic threat hunting operations. It provides step-by-step instructions for using all available tools and workflows to identify and analyze security threats.

## Getting Started

### Prerequisites

- Access to n8n dashboard on VM-04: `http://<VM-04_IP>:5678`
- Access to JupyterLab on VM-03: `http://<VM-03_IP>:8888` (optional, for advanced analysis)
- Access to your SIEM/EDR tools (Microsoft Defender, Sentinel, Splunk, etc.)
- Basic understanding of MITRE ATT&CK framework
- Understanding of threat hunting concepts

### First Steps

1. **Access the System**
   - Open n8n dashboard: `http://<VM-04_IP>:5678`
   - Log in with your credentials
   - Navigate to "Workflows" to see available workflows

2. **Familiarize Yourself with Tools**
   - Review available workflows in n8n
   - Check Management Dashboard for system status
   - Explore Hunt Selection Form

## Conducting a Threat Hunt

### Complete Hunt Workflow (Recommended)

The Complete Hunt Workflow provides an end-to-end solution from hunt selection to final report generation.

#### Step 1: Access Complete Hunt Dashboard

1. Open n8n: `http://<VM-04_IP>:5678`
2. Navigate to "Complete Hunt Workflow"
3. Ensure workflow is activated
4. Open webhook URL: `http://<VM-04_IP>:5678/webhook/complete-hunt`

#### Step 2: Select MITRE ATT&CK Techniques

1. **Review Available Techniques**
   - The dashboard displays all available MITRE ATT&CK techniques
   - Each technique shows:
     - Technique ID (e.g., T1566)
     - Technique Name (e.g., Phishing)
     - Tactic (e.g., Initial Access)
     - Description

2. **Select Techniques**
   - Check boxes next to techniques you want to investigate
   - You can select multiple techniques
   - Consider selecting related techniques for comprehensive coverage

   **Example Selection:**
   - ☑ T1566 - Phishing
   - ☑ T1059 - Command and Scripting Interpreter
   - ☑ T1078 - Valid Accounts

#### Step 3: Select Available Tools

1. **Review Available Tools**
   - The dashboard shows tools available in your playbooks:
     - Microsoft Defender for Endpoint
     - Microsoft Sentinel
     - Splunk
     - Elasticsearch
     - Generic SIEM

2. **Select Your Tools**
   - Check only the tools you have access to
   - System will generate queries only for selected tools

#### Step 4: Configure Workflow Options

1. **Select Ingest Mode**
   - **Manual**: You will upload data manually after executing queries
   - **API**: System will automatically retrieve data via API (requires API configuration)

2. **Configure Analysis Options**
   - **Anonymize Data**: Anonymize sensitive data before AI analysis (recommended)
   - **AI Review**: Automatically review findings with AI (recommended)
   - **Generate Report**: Generate comprehensive final report
   - **Deanonymize**: Include real data in final report (for stakeholders)

#### Step 5: Generate and Execute Queries

1. **Generate Queries**
   - Click "Generate Queries" button
   - System generates queries for all selected technique-tool combinations
   - Review generated queries

2. **Execute Queries in Your Tools**
   - Copy each query
   - Open your SIEM/EDR tool
   - Paste and execute the query
   - Export results (CSV or JSON format)
   - Note which results correspond to which technique

3. **Upload Query Results** (if Manual Mode)
   - Return to Complete Hunt Dashboard
   - Click "Upload Data" or "Execute Pipeline"
   - Upload your query result files
   - System maps results to appropriate techniques

#### Step 6: Execute Complete Hunt

1. **Start Execution**
   - Click "Execute Complete Hunt" button
   - System displays progress for each stage:
     - Query Generation
     - Data Ingestion (if API mode)
     - Data Storage
     - Playbook Execution
     - AI Review (if enabled)
     - Report Generation (if enabled)

2. **Monitor Progress**
   - Watch progress indicators for each stage
   - Check for any errors or warnings
   - Review intermediate results if available

#### Step 7: Review Results

1. **View Findings**
   - System displays all findings discovered
   - Each finding shows:
     - Finding ID
     - Technique ID
     - Severity
     - Confidence
     - Status (new, confirmed, false_positive, etc.)
     - Description

2. **Review AI Validation** (if enabled)
   - AI review results for each finding
   - Validation status (valid, needs_review, invalid)
   - Recommended status updates
   - False positive risk assessment

3. **Download Final Report** (if enabled)
   - Click "Download Report"
   - Report includes:
     - Executive Summary (AI-generated)
     - All findings with evidence
     - Statistics and analysis
     - Recommendations

### Alternative: Hunt Selection Form Workflow

For simpler hunts without full pipeline execution:

1. **Access Hunt Selection Form**
   - Navigate to "Hunt Selection Form" workflow in n8n
   - Open webhook: `http://<VM-04_IP>:5678/webhook/hunt-selection`

2. **Select Techniques and Tools**
   - Follow same steps as Complete Hunt Workflow

3. **Generate Queries Only**
   - System generates queries
   - Copy queries for manual execution
   - Execute in your tools
   - Analyze results manually

## Using JupyterLab for Advanced Analysis

### Access JupyterLab

1. **Open JupyterLab**
   - URL: `http://<VM-03_IP>:8888`
   - Enter token from configuration

2. **Navigate to Playbooks**
   - Open `playbooks/` directory
   - Select playbook for your technique
   - Open playbook notebook

### Interactive Analysis

1. **Load Data**
   - Execute cells to load data from database
   - Filter data as needed
   - Explore data structure

2. **Run Analysis**
   - Execute playbook analysis cells
   - Review findings
   - Customize analysis logic if needed

3. **Generate Custom Reports**
   - Create custom visualizations
   - Export findings
   - Generate custom reports

## Understanding Findings

### Finding Structure

Each finding contains:

- **Finding ID**: Unique identifier
- **Technique ID**: MITRE ATT&CK technique
- **Severity**: high, medium, low, critical
- **Confidence**: 0.0 to 1.0 (0.0 = low, 1.0 = high)
- **Status**: new, confirmed, investigating, false_positive, resolved
- **Description**: Human-readable description
- **Evidence**: Supporting evidence records
- **Timestamp**: When finding was created

### Finding Statuses

- **new**: Newly discovered, not yet reviewed
- **confirmed**: Validated and confirmed as threat
- **investigating**: Under investigation
- **false_positive**: Determined to be false positive
- **resolved**: Threat has been addressed

### Interpreting Severity

- **critical**: Immediate action required
- **high**: High priority, investigate soon
- **medium**: Moderate priority
- **low**: Low priority, informational

## Best Practices

### Hunt Planning

1. **Define Objectives**: Clearly define what you're hunting for
2. **Select Appropriate Techniques**: Choose techniques relevant to your threat landscape
3. **Use Multiple Tools**: Cross-reference findings from multiple tools
4. **Set Time Ranges**: Use appropriate time ranges (7-30 days typical)

### Query Execution

1. **Review Queries**: Always review generated queries before execution
2. **Customize as Needed**: Adjust queries for your environment
3. **Document Changes**: Note any modifications made to queries
4. **Validate Results**: Ensure query results are reasonable

### Data Management

1. **Anonymize Before AI**: Always anonymize sensitive data before AI analysis
2. **Verify Anonymization**: Check that anonymization worked correctly
3. **Secure Data**: Protect query results and findings
4. **Retention**: Follow data retention policies

### Analysis

1. **Review All Findings**: Don't skip low-severity findings
2. **Correlate Evidence**: Look for patterns across findings
3. **Use AI Review**: Leverage AI validation for initial triage
4. **Verify Critical Findings**: Manually verify critical findings

### Reporting

1. **Include Context**: Provide context for findings
2. **Use Executive Summary**: Leverage AI-generated summaries
3. **Deanonymize for Reports**: Use real data in final reports for stakeholders
4. **Document Methodology**: Include how findings were discovered

## Common Workflows

### Quick Hunt (Single Technique)

1. Select one technique
2. Select one tool
3. Generate query
4. Execute query
5. Review results manually

### Comprehensive Hunt (Multiple Techniques)

1. Select multiple related techniques
2. Select all available tools
3. Generate all queries
4. Execute queries
5. Use Complete Hunt Workflow
6. Review aggregated findings

### Targeted Hunt (Specific Threat)

1. Identify specific threat or campaign
2. Select relevant techniques
3. Generate queries
4. Execute with specific time range
5. Analyze results
6. Generate detailed report

## Troubleshooting

### Queries Not Generated

- **Check Playbook Availability**: Ensure playbooks exist for selected techniques
- **Verify Tool Names**: Tool names must match exactly (case-sensitive)
- **Review Playbook Structure**: Check playbook metadata.yml structure

### No Findings Generated

- **Check Data Quality**: Ensure query results contain relevant data
- **Review Playbook Logic**: Check playbook analyzer logic
- **Verify Time Range**: Ensure time range covers relevant period
- **Check Data Format**: Verify data format matches expected structure

### AI Review Not Working

- **Check API Key**: Verify OpenAI API key is configured
- **Review Anonymization**: Ensure data is properly anonymized
- **Check API Limits**: Verify API rate limits not exceeded
- **Review Logs**: Check logs for error messages

### Report Generation Issues

- **Check Deanonymization**: Ensure mapping table has required mappings
- **Verify Findings**: Ensure findings exist for report
- **Review Permissions**: Check file system permissions
- **Check Disk Space**: Ensure sufficient disk space

## Advanced Features

### Custom Playbook Creation

1. **Use Playbook Manager**
   - Access via n8n: `http://<VM-04_IP>:5678/webhook/playbook-manager`
   - Click "Create New Playbook"
   - Fill in playbook details
   - System creates playbook from template

2. **Customize Playbook**
   - Edit metadata.yml
   - Add custom queries
   - Modify analyzer logic
   - Validate playbook

### Batch Processing

1. **Multiple Hunts**
   - Execute multiple hunts in sequence
   - Aggregate results
   - Compare findings across hunts

2. **Scheduled Hunts**
   - Set up scheduled hunts (if supported)
   - Automate regular threat hunting
   - Review periodic reports

## Integration with External Tools

### SIEM/EDR Integration

- **API Mode**: Configure API connections for automatic data retrieval
- **Manual Mode**: Export data from tools and upload manually
- **Query Templates**: Use generated queries in your tools

### Reporting Integration

- **Export Findings**: Export findings to external systems
- **API Access**: Use API endpoints for programmatic access
- **Custom Reports**: Generate custom reports for different stakeholders

## Security Considerations

### Data Protection

- **Anonymization**: Always anonymize before AI analysis
- **Access Control**: Limit access to sensitive findings
- **Audit Logging**: All operations are logged
- **Data Retention**: Follow retention policies

### Best Practices

- **Secure Credentials**: Never expose API keys or passwords
- **Review Permissions**: Regularly review access permissions
- **Monitor Access**: Monitor who accesses the system
- **Update Regularly**: Keep system updated with latest playbooks

## Getting Help

### Documentation

- **Tools Guide**: `docs/TOOLS_GUIDE.md` - Detailed tool documentation
- **Deployment Guide**: `docs/DEPLOYMENT_GUIDE.md` - System setup
- **Architecture**: `docs/ARCHITECTURE_ENHANCED.md` - System architecture
- **Data Flow**: `docs/DATA_FLOW.md` - Data flow documentation

### Support

- **Check Logs**: Review system logs for errors
- **Management Dashboard**: Check system health
- **Test Connectivity**: Use Testing Management Interface
- **Contact Administrator**: For system-level issues

## Summary

This guide provides comprehensive instructions for conducting threat hunts using the Threat Hunting Automation Lab. The system automates the entire workflow from query generation through analysis to reporting, while providing flexibility for manual intervention and customization.

**Key Takeaways:**
- Use Complete Hunt Workflow for end-to-end automation
- Always review generated queries before execution
- Leverage AI review for initial triage
- Anonymize data before AI analysis
- Generate comprehensive reports for stakeholders
- Follow best practices for data security

**Next Steps:**
- Review [Query Generation Guide](QUERY_GENERATION.md) for detailed query usage
- Read [AI Integration Guide](AI_INTEGRATION.md) to understand AI features
- Check [Remote Management Guide](REMOTE_MANAGEMENT.md) for system management

