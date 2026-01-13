# AI Service - OpenAI Integration

## Overview

The AI Service provides OpenAI API integration for threat hunting operations, including findings validation, executive summary generation, evidence analysis, and finding correlation.

## Purpose

- **Findings Validation**: AI-powered validation of threat hunting findings
- **Executive Summary**: Automated generation of executive summaries
- **Evidence Analysis**: AI analysis of evidence records
- **Finding Correlation**: Correlation of multiple findings to identify attack patterns
- **Description Enhancement**: Enhancement of finding descriptions

## Features

### 1. Findings Validation

Validates findings using AI to assess:
- Validation status (valid, needs_review, invalid)
- Confidence assessment
- Severity assessment
- Evidence quality
- False positive risk

### 2. Executive Summary Generation

Generates comprehensive executive summaries including:
- High-level overview
- Critical findings
- Threat landscape
- Risk assessment
- Recommendations
- Next steps

### 3. Evidence Analysis

Analyzes evidence records to identify:
- Evidence classification
- Threat indicators
- Behavioral patterns
- Context
- Relevance score

### 4. Finding Correlation

Correlates multiple findings to identify:
- Attack chains
- Common indicators
- Timeline analysis
- Threat actor profiles

### 5. Description Enhancement

Enhances finding descriptions with:
- More detailed information
- MITRE ATT&CK context
- Investigation guidance

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-your-api-key-here

# Optional
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=2000
```

### Config File

```yaml
ai:
  openai:
    model: "gpt-4"
    temperature: 0.3
    max_tokens: 2000
    timeout: 30
  anonymize_before_ai: true
  features:
    validate_findings: true
    generate_executive_summary: true
    analyze_evidence: true
    correlate_findings: true
    enhance_descriptions: true
```

## Usage

### Initialize AI Service

```python
from automation_scripts.services.ai_service import AIService
from automation_scripts.utils.deterministic_anonymizer import DeterministicAnonymizer

# Initialize anonymizer (optional but recommended)
anonymizer = DeterministicAnonymizer(
    db_config={
        'host': 'vm02',
        'database': 'threat_hunting',
        'user': 'threat_hunter',
        'password': 'password'
    }
)

# Initialize AI service
ai_service = AIService(
    api_key=os.getenv('OPENAI_API_KEY'),
    model='gpt-4',
    anonymizer=anonymizer
)
```

### Validate Finding

```python
finding = {
    'finding_id': 'T1566_20240115_103000_5',
    'technique_id': 'T1566',
    'technique_name': 'Phishing',
    'severity': 'high',
    'confidence': 0.85,
    'title': 'Suspicious activity detected',
    'description': 'Detected suspicious email activity',
    'evidence_count': 5
}

validation = ai_service.validate_finding(finding, anonymize=True)
print(f"Status: {validation['validation_status']}")
print(f"False Positive Risk: {validation['false_positive_risk']}")
```

### Generate Executive Summary

```python
findings = [finding1, finding2, finding3]

context = {
    'time_range': '2024-01-15 to 2024-01-16',
    'playbooks': ['T1566-phishing', 'T1059-command'],
    'total_findings': len(findings),
    'analysis_date': '2024-01-16'
}

summary = ai_service.generate_executive_summary(
    findings=findings,
    context=context,
    anonymize=True
)

print(summary['executive_summary'])
print(f"Overall Risk: {summary['risk_assessment']['overall_risk']}")
```

### Analyze Evidence

```python
evidence = {
    'evidence_id': 'evid_001',
    'evidence_type': 'log_entry',
    'source': 'Microsoft Defender',
    'timestamp': '2024-01-15T10:30:00Z',
    'normalized_fields': {
        'process_name': 'powershell.exe',
        'command_line': 'powershell -enc ...'
    }
}

analysis = ai_service.analyze_evidence(evidence, anonymize=True)
print(f"Classification: {analysis['classification']}")
print(f"Threat Indicators: {analysis['threat_indicators']}")
```

### Correlate Findings

```python
findings = [finding1, finding2, finding3, finding4]

correlation = ai_service.correlate_findings(findings, anonymize=True)

if correlation['correlated']:
    print("Findings are correlated!")
    print(f"Attack Chain: {correlation['attack_chain']}")
    print(f"Common Indicators: {correlation['common_indicators']}")
```

### Enhance Description

```python
finding = {
    'finding_id': 'T1566_001',
    'technique_id': 'T1566',
    'technique_name': 'Phishing',
    'description': 'Suspicious email detected'
}

enhancement = ai_service.enhance_finding_description(finding, anonymize=True)
print(f"Enhanced Description: {enhancement['enhanced_description']}")
```

## Anonymization

The AI Service integrates with DeterministicAnonymizer to anonymize data before sending to OpenAI:

- **Automatic Anonymization**: Data is anonymized before AI processing
- **Deanonymization**: Results can be deanonymized after processing
- **Privacy Protection**: Sensitive data (IPs, emails, usernames) is protected

```python
# Anonymization is enabled by default
validation = ai_service.validate_finding(finding, anonymize=True)

# Disable anonymization if needed (not recommended)
validation = ai_service.validate_finding(finding, anonymize=False)
```

## Error Handling

```python
from automation_scripts.services.ai_service import AIServiceError

try:
    validation = ai_service.validate_finding(finding)
except AIServiceError as e:
    print(f"AI Service error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Best Practices

1. **Always Anonymize**: Use anonymization before sending data to AI
2. **Validate API Key**: Ensure API key is set correctly
3. **Handle Errors**: Implement proper error handling
4. **Rate Limiting**: Be aware of OpenAI API rate limits
5. **Cost Management**: Monitor API usage and costs
6. **Model Selection**: Choose appropriate model (gpt-4 for accuracy, gpt-3.5-turbo for speed)

## Integration

### With Playbook Engine

```python
from automation_scripts.orchestrators.playbook_engine import PlaybookEngine
from automation_scripts.services.ai_service import AIService

# Execute playbook
engine = PlaybookEngine()
result = engine.execute_playbook(playbook_id, data_package)

# Validate findings with AI
ai_service = AIService()
for finding in result['findings']:
    validation = ai_service.validate_finding(finding)
    if validation['validation_status'] == 'invalid':
        print(f"Invalid finding: {finding['finding_id']}")
```

### With Findings Storage

```python
# Store findings with AI validation
for finding in findings:
    # Validate with AI
    validation = ai_service.validate_finding(finding)
    
    # Add validation to finding metadata
    finding['ai_validation'] = validation
    
    # Store in database
    store_finding(finding)
```

## Security Considerations

1. **API Key Protection**: Never commit API keys to version control
2. **Data Anonymization**: Always anonymize sensitive data before AI processing
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Cost Monitoring**: Monitor API usage to prevent unexpected costs
5. **Error Handling**: Handle API errors gracefully

## Future Enhancements

- Support for other AI providers (Anthropic, Google, etc.)
- Batch processing for multiple findings
- Caching of AI responses
- Custom prompt templates
- Fine-tuned models for threat hunting

