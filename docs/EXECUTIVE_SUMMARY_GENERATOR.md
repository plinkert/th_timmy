# Executive Summary Generator

## Overview

The Executive Summary Generator provides AI-powered generation of professional executive summaries for threat hunting exercises. It uses AI to analyze findings and generate comprehensive, actionable summaries formatted as markdown reports.

## Purpose

- **Professional Reporting**: Generate executive-level summaries for management
- **AI-Powered Analysis**: Use AI to analyze findings and provide insights
- **Template-Based Formatting**: Use markdown templates for consistent formatting
- **Multiple Formats**: Support for markdown and JSON output formats
- **Integration**: Seamless integration with Playbook Engine and AI Reviewer

## Features

### 1. AI-Powered Summary Generation

- Analyzes findings using OpenAI
- Generates comprehensive summaries
- Provides actionable recommendations
- Identifies critical findings

### 2. Template-Based Formatting

- Markdown template for professional formatting
- Customizable template structure
- Consistent report format
- Professional presentation

### 3. Multiple Output Formats

- **Markdown**: Professional markdown report
- **JSON**: Structured JSON data
- **Both**: Both formats simultaneously

### 4. Statistics and Analysis

- Automatic statistics calculation
- Severity distribution
- Technique distribution
- Risk assessment

## Usage

### Initialize Generator

```python
from automation_scripts.services.executive_summary_generator import ExecutiveSummaryGenerator

# Initialize generator
generator = ExecutiveSummaryGenerator(
    config_path='configs/config.yml'
)
```

### Generate Summary from Findings

```python
findings = [
    {
        'finding_id': 'T1566_001',
        'technique_id': 'T1566',
        'technique_name': 'Phishing',
        'severity': 'high',
        'confidence': 0.85,
        'title': 'Suspicious email activity detected'
    },
    # ... more findings
]

context = {
    'time_range': '2024-01-15 to 2024-01-16',
    'playbooks_executed': ['T1566-phishing', 'T1059-command']
}

summary = generator.generate_summary(
    findings=findings,
    context=context,
    format='both',  # 'markdown', 'json', or 'both'
    anonymize=True
)

# Access markdown
print(summary['markdown'])

# Access JSON
print(summary['json'])
```

### Generate Summary from Playbook Execution

```python
from automation_scripts.orchestrators.playbook_engine import PlaybookEngine

# Execute playbook
engine = PlaybookEngine()
result = engine.execute_playbook(playbook_id, data_package)

# Generate summary
summary = generator.generate_summary_from_execution(
    execution_result=result,
    format='markdown',
    anonymize=True
)
```

### Save Summary to File

```python
# Save summary
output_path = generator.save_summary(
    summary=summary,
    format='both'  # Saves both .md and .json files
)

print(f"Summary saved to: {output_path}")
```

## Template Structure

The markdown template includes:

1. **Header**: Metadata (generated date, time range, findings count)
2. **Executive Overview**: High-level summary
3. **Critical Findings**: Top findings with details
4. **Threat Landscape**: MITRE ATT&CK techniques and tactics
5. **Risk Assessment**: Overall risk and risk factors
6. **Recommendations**: Immediate actions and long-term improvements
7. **Next Steps**: Follow-up investigations and queries
8. **Statistics**: Summary statistics

## Template Variables

- `{{generated_at}}`: Generation timestamp
- `{{time_range}}`: Time range of exercise
- `{{total_findings}}`: Total number of findings
- `{{executive_summary}}`: AI-generated summary text
- `{{critical_findings}}`: List of critical findings
- `{{techniques_detected}}`: MITRE techniques detected
- `{{tactics_observed}}`: MITRE tactics observed
- `{{overall_risk}}`: Overall risk level
- `{{risk_score}}`: Risk score (0-10)
- `{{immediate_actions}}`: Immediate action items
- `{{long_term_improvements}}`: Long-term improvements
- `{{follow_up_investigations}}`: Follow-up investigations
- `{{additional_queries}}`: Additional queries

## Customization

### Custom Template

```python
# Use custom template
generator = ExecutiveSummaryGenerator(
    template_path=Path('custom_template.md')
)
```

### Template Syntax

The template uses simple `{{variable}}` syntax:

- `{{variable}}`: Simple variable replacement
- `{{#list}}...{{/list}}`: List rendering (for arrays)

## Integration

### With Playbook Engine

```python
# Execute playbook and generate summary
engine = PlaybookEngine()
result = engine.execute_playbook(playbook_id, data_package)

generator = ExecutiveSummaryGenerator()
summary = generator.generate_summary_from_execution(result)
```

### With AI Reviewer

```python
# Review findings and generate summary
reviewer = AIReviewer()
review_result = reviewer.review_playbook_execution(execution_result)

generator = ExecutiveSummaryGenerator()
summary = generator.generate_summary(
    findings=execution_result['findings'],
    context={'review_results': review_result}
)
```

### With Pipeline Orchestrator

```python
# Generate summary from pipeline results
orchestrator = PipelineOrchestrator()
pipeline_result = orchestrator.execute_pipeline(...)

# Extract findings from pipeline
all_findings = []
for stage in pipeline_result['stages'].values():
    if 'findings' in stage:
        all_findings.extend(stage['findings'])

generator = ExecutiveSummaryGenerator()
summary = generator.generate_summary(
    findings=all_findings,
    context={'pipeline_id': pipeline_result['pipeline_id']}
)
```

## Output Formats

### Markdown Format

Professional markdown report suitable for:
- Documentation
- Email reports
- Presentation slides
- PDF conversion

### JSON Format

Structured JSON data suitable for:
- API responses
- Data processing
- Integration with other systems
- Programmatic access

## Best Practices

1. **Always Anonymize**: Use anonymization before AI processing
2. **Provide Context**: Include time range, playbooks, etc.
3. **Review Before Sharing**: Review AI-generated content before sharing
4. **Customize Template**: Adjust template for your organization
5. **Save Reports**: Save summaries for historical reference

## Examples

### Basic Usage

```python
from automation_scripts.services.executive_summary_generator import ExecutiveSummaryGenerator

generator = ExecutiveSummaryGenerator()

findings = [finding1, finding2, finding3]
summary = generator.generate_summary(findings, format='markdown')

# Save to file
generator.save_summary(summary, format='markdown')
```

### With Custom Context

```python
context = {
    'time_range': '2024-01-15 to 2024-01-20',
    'playbooks_executed': ['T1566-phishing', 'T1059-command', 'T1021-remote'],
    'analyst': 'John Doe',
    'exercise_name': 'Q1 2024 Threat Hunt'
}

summary = generator.generate_summary(
    findings=findings,
    context=context,
    format='both'
)
```

### Integration with Workflow

```python
# In n8n workflow or API endpoint
def generate_executive_summary_endpoint(findings, context):
    generator = ExecutiveSummaryGenerator()
    summary = generator.generate_summary(
        findings=findings,
        context=context,
        format='markdown'
    )
    return summary['markdown']
```

## Future Enhancements

- PDF export support
- Email integration
- Scheduled summary generation
- Custom template variables
- Multi-language support
- Report versioning

