# Deanonymization and Reporting

## Overview

The Deanonymization and Reporting system provides services for reversing anonymization and generating final reports with original (deanonymized) data. This is essential for creating reports for stakeholders who need to see actual IP addresses, usernames, and other sensitive information.

## Purpose

- **Deanonymization Before Reporting**: Reverse anonymization using mapping table
- **Report Generation**: Generate professional reports with deanonymized data
- **Integration**: Seamless integration with Executive Summary Generator
- **Multiple Formats**: Support for markdown and JSON output formats
- **Security**: Controlled deanonymization only for reporting purposes

## Components

### 1. Deanonymizer Service

The `Deanonymizer` service provides deterministic deanonymization using the mapping table stored in PostgreSQL.

#### Features

- **Finding Deanonymization**: Deanonymize individual findings
- **Batch Deanonymization**: Deanonymize multiple findings at once
- **Evidence Deanonymization**: Deanonymize evidence records
- **Report Deanonymization**: Deanonymize complete reports
- **Text Deanonymization**: Deanonymize text fields containing anonymized values

#### Usage

```python
from automation_scripts.utils.deanonymizer import Deanonymizer

# Initialize deanonymizer
deanonymizer = Deanonymizer(config_path='configs/config.yml')

# Deanonymize a finding
finding = {
    'finding_id': 'T1566_001',
    'ip': '10.123.45.67',  # Anonymized IP
    'username': 'user_abc123456789',  # Anonymized username
    'description': 'Activity from 10.123.45.67 by user_abc123456789'
}

deanonymized_finding = deanonymizer.deanonymize_finding(finding)
# Returns finding with original values restored
```

#### Deanonymize Multiple Findings

```python
findings = [finding1, finding2, finding3]

deanonymized_findings = deanonymizer.deanonymize_findings(findings)
```

#### Deanonymize Evidence

```python
evidence = {
    'evidence_id': 'evid_001',
    'raw_data': {
        'ip': '10.123.45.67',
        'user': 'user_abc123456789'
    }
}

deanonymized_evidence = deanonymizer.deanonymize_evidence(evidence)
```

#### Deanonymize Report

```python
report = {
    'findings': [finding1, finding2],
    'executive_summary': 'Summary with 10.123.45.67...',
    'recommendations': {
        'immediate_actions': ['Check 10.123.45.67...']
    }
}

deanonymized_report = deanonymizer.deanonymize_report(report)
```

### 2. Report Generator

The `ReportGenerator` service generates complete reports with deanonymized data.

#### Features

- **Automatic Deanonymization**: Automatically deanonymizes data before reporting
- **Executive Summary Integration**: Includes AI-generated executive summary
- **Multiple Formats**: Support for markdown and JSON
- **Professional Formatting**: Well-structured reports for stakeholders

#### Usage

```python
from automation_scripts.utils.report_generator import ReportGenerator

# Initialize report generator
report_generator = ReportGenerator(config_path='configs/config.yml')

# Generate report
findings = [finding1, finding2, finding3]

context = {
    'time_range': '2024-01-15 to 2024-01-20',
    'playbooks_executed': ['T1566-phishing', 'T1059-command']
}

report = report_generator.generate_report(
    findings=findings,
    context=context,
    deanonymize=True,  # Deanonymize before reporting
    include_executive_summary=True,  # Include AI summary
    format='both'  # Both markdown and JSON
)

# Save report
report_generator.save_report(report, format='markdown')
```

#### Generate Report from Playbook Execution

```python
from automation_scripts.orchestrators.playbook_engine import PlaybookEngine

# Execute playbook
engine = PlaybookEngine()
result = engine.execute_playbook(playbook_id, data_package)

# Generate report
report = report_generator.generate_report_from_execution(
    execution_result=result,
    deanonymize=True,
    include_executive_summary=True
)
```

## Workflow

### Typical Workflow

1. **Data Anonymization** (Before AI):
   - Data is anonymized using `DeterministicAnonymizer`
   - Mapping stored in PostgreSQL database

2. **AI Analysis** (With Anonymized Data):
   - AI processes anonymized data
   - Findings generated with anonymized values

3. **Deanonymization** (Before Reporting):
   - `Deanonymizer` reverses anonymization
   - Original values restored using mapping table

4. **Report Generation**:
   - `ReportGenerator` creates final report
   - Report includes deanonymized data
   - Executive summary included

### Example Workflow

```python
from automation_scripts.utils.deterministic_anonymizer import DeterministicAnonymizer
from automation_scripts.utils.deanonymizer import Deanonymizer
from automation_scripts.utils.report_generator import ReportGenerator
from automation_scripts.orchestrators.playbook_engine import PlaybookEngine

# 1. Anonymize data before AI
anonymizer = DeterministicAnonymizer(db_config=db_config)
anonymized_data = anonymizer.anonymize_record(original_data)

# 2. Execute playbook with anonymized data
engine = PlaybookEngine()
result = engine.execute_playbook(
    playbook_id='T1566-phishing',
    data_package=anonymized_data_package,
    anonymize_before=True
)

# 3. Deanonymize findings before reporting
deanonymizer = Deanonymizer(config_path='configs/config.yml')
deanonymized_findings = deanonymizer.deanonymize_findings(result['findings'])

# 4. Generate report with deanonymized data
report_generator = ReportGenerator(config_path='configs/config.yml')
report = report_generator.generate_report(
    findings=deanonymized_findings,
    deanonymize=False,  # Already deanonymized
    include_executive_summary=True
)

# 5. Save report
report_generator.save_report(report, format='markdown')
```

## Integration Points

### With Playbook Engine

```python
# Execute playbook and generate report
engine = PlaybookEngine()
result = engine.execute_playbook(playbook_id, data_package)

report_generator = ReportGenerator()
report = report_generator.generate_report_from_execution(
    execution_result=result,
    deanonymize=True
)
```

### With AI Reviewer

```python
# Review findings and generate report
from automation_scripts.orchestrators.ai_reviewer import AIReviewer

reviewer = AIReviewer()
review_result = reviewer.review_playbook_execution(execution_result)

report_generator = ReportGenerator()
report = report_generator.generate_report(
    findings=execution_result['findings'],
    context={'review_results': review_result},
    deanonymize=True
)
```

### With Pipeline Orchestrator

```python
# Generate report from pipeline results
from automation_scripts.orchestrators.pipeline_orchestrator import PipelineOrchestrator

orchestrator = PipelineOrchestrator()
pipeline_result = orchestrator.execute_pipeline(...)

# Extract findings
all_findings = []
for stage in pipeline_result['stages'].values():
    if 'findings' in stage:
        all_findings.extend(stage['findings'])

# Generate report
report_generator = ReportGenerator()
report = report_generator.generate_report(
    findings=all_findings,
    context={'pipeline_id': pipeline_result['pipeline_id']},
    deanonymize=True
)
```

## Security Considerations

### When to Deanonymize

- **Before Reporting**: Deanonymize only when generating final reports
- **For Stakeholders**: Deanonymize for reports shared with authorized personnel
- **Never for AI**: Never deanonymize data before sending to AI services

### Access Control

- **Database Access**: Limit access to mapping table
- **Report Distribution**: Control who receives deanonymized reports
- **Audit Logging**: Log all deanonymization operations

### Best Practices

1. **Anonymize Before AI**: Always anonymize before AI processing
2. **Deanonymize Only for Reports**: Deanonymize only when generating final reports
3. **Secure Storage**: Store mapping table securely
4. **Access Control**: Control access to deanonymization service
5. **Audit Logging**: Log all deanonymization operations

## Report Structure

### Markdown Report

- **Header**: Metadata (date, time range, findings count)
- **Executive Summary**: AI-generated summary
- **Findings Details**: Detailed findings with deanonymized data
- **Footer**: Report metadata

### JSON Report

- **report_id**: Unique report identifier
- **generated_at**: Generation timestamp
- **findings_count**: Number of findings
- **deanonymized**: Whether data was deanonymized
- **context**: Context information
- **findings**: List of findings (deanonymized)
- **executive_summary**: Executive summary data

## Examples

### Basic Report Generation

```python
from automation_scripts.utils.report_generator import ReportGenerator

report_generator = ReportGenerator()

findings = [finding1, finding2, finding3]
report = report_generator.generate_report(
    findings=findings,
    deanonymize=True,
    format='markdown'
)

report_generator.save_report(report)
```

### Report with Executive Summary

```python
report = report_generator.generate_report(
    findings=findings,
    context={
        'time_range': '2024-01-15 to 2024-01-20',
        'playbooks_executed': ['T1566-phishing']
    },
    deanonymize=True,
    include_executive_summary=True,
    format='both'
)
```

### Custom Deanonymization

```python
from automation_scripts.utils.deanonymizer import Deanonymizer

deanonymizer = Deanonymizer()

# Deanonymize specific fields
deanonymized = deanonymizer.deanonymize_finding(
    finding=finding,
    fields_to_deanonymize=['ip', 'username', 'email']
)
```

## Troubleshooting

### Deanonymization Not Working

- **Check Mapping Table**: Ensure mapping table exists and has data
- **Verify Value Types**: Ensure value types match
- **Check Database Connection**: Verify database connection
- **Review Logs**: Check logs for errors

### Report Generation Issues

- **Check Deanonymizer**: Ensure deanonymizer is initialized
- **Verify Findings**: Ensure findings are valid
- **Check Permissions**: Verify file write permissions
- **Review Logs**: Check logs for errors

## Future Enhancements

- PDF export support
- Email integration
- Scheduled report generation
- Custom report templates
- Multi-language support
- Report versioning
- Report comparison

