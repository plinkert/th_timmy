# AI Integration Guide for Threat Hunters

## Overview

This guide explains how AI is integrated into the Threat Hunting Automation Lab system and how threat hunters can leverage AI capabilities to enhance their threat hunting operations.

## What is AI Integration?

The system integrates with OpenAI to provide AI-powered analysis and validation of threat hunting findings. AI helps:

- **Validate Findings**: Determine if findings are valid threats or false positives
- **Generate Summaries**: Create executive summaries of hunt results
- **Analyze Evidence**: Analyze evidence records for threat indicators
- **Correlate Findings**: Identify relationships between multiple findings
- **Enhance Descriptions**: Improve finding descriptions with context

## How AI Works in the System

### Data Flow with AI

```
Findings Generated
    ↓
Anonymization (if enabled)
    ↓
AI Service (OpenAI)
    ↓
Validation Results
    ↓
Status Updates
    ↓
Enhanced Findings
```

### Privacy Protection

**Important**: Before sending data to AI, sensitive information is automatically anonymized:

- IP addresses → Anonymized IPs
- Email addresses → Anonymized emails
- Usernames → Anonymized usernames
- Other PII → Anonymized values

This protects sensitive data while allowing AI analysis.

## Using AI Features

### AI Review Workflow

The easiest way to use AI is through the AI Review Workflow in n8n.

#### Access AI Review Dashboard

1. **Open n8n**: `http://<VM-04_IP>:5678`
2. **Navigate to**: "AI Review Workflow"
3. **Open Dashboard**: `http://<VM-04_IP>:5678/webhook/ai-review`

#### Review Single Finding

1. **Enter Finding JSON**
   - Paste finding JSON in textarea
   - Or select finding from list

2. **Set Options**
   - Check "Update finding status based on review"
   - Select review options

3. **Click "Review Finding"**
   - System sends finding to AI (anonymized)
   - AI analyzes and validates
   - Results displayed

4. **Review Results**
   - Validation status (valid/invalid/needs_review)
   - False positive risk (low/medium/high)
   - Confidence assessment
   - Recommended status update

#### Review Multiple Findings (Batch)

1. **Enter Findings JSON**
   - Paste array of findings JSON
   - Or select multiple findings

2. **Set Batch Size**
   - Number of findings to process in parallel (default: 10)
   - Adjust based on API limits

3. **Click "Review Findings Batch"**
   - System processes all findings
   - Shows progress
   - Displays summary statistics

4. **Review Results**
   - Summary of all reviews
   - Individual review results
   - Statistics (valid/invalid/needs_review counts)

### AI Review in Complete Hunt Workflow

When using Complete Hunt Workflow, AI review can be enabled automatically:

1. **Enable AI Review Option**
   - Check "AI Review" in workflow options
   - System automatically reviews all findings

2. **Review Process**
   - Findings are anonymized
   - Sent to AI for validation
   - Status updated based on AI results
   - Results included in final report

3. **Review Results**
   - Check AI validation in findings
   - Review AI recommendations
   - Use AI insights for triage

## Understanding AI Results

### Validation Status

AI returns one of three validation statuses:

- **valid**: Finding appears to be a valid threat
- **needs_review**: Finding requires manual review
- **invalid**: Finding appears to be false positive

### False Positive Risk

AI assesses false positive risk:

- **low**: Low risk of false positive
- **medium**: Medium risk, review recommended
- **high**: High risk of false positive

### Confidence Assessment

AI provides confidence levels:

- **Current Confidence**: Your original confidence level
- **Recommended Confidence**: AI's recommended confidence
- **Reasoning**: Why confidence should be adjusted

### Severity Assessment

AI may recommend severity adjustments:

- **Current Severity**: Your original severity
- **Recommended Severity**: AI's recommended severity
- **Reasoning**: Why severity should be adjusted

### Evidence Quality

AI assesses evidence quality:

- **Quality Score**: How strong the evidence is
- **Gaps**: What evidence might be missing
- **Recommendations**: How to improve evidence

## AI-Generated Executive Summaries

### What is an Executive Summary?

An AI-generated executive summary provides:

- **High-Level Overview**: Summary of all findings
- **Critical Findings**: Most important threats identified
- **Threat Landscape**: Overall threat picture
- **Risk Assessment**: Overall risk level
- **Recommendations**: Next steps and actions
- **Statistics**: Key numbers and metrics

### Generating Executive Summary

#### Through Complete Hunt Workflow

1. **Enable Report Generation**
   - Check "Generate Report" in workflow options
   - Check "Include Executive Summary"

2. **Review Summary**
   - Summary included in final report
   - Review for accuracy
   - Customize if needed

#### Through API

```python
from automation_scripts.services.ai_service import AIService

ai_service = AIService()

summary = ai_service.generate_executive_summary(
    findings=findings,
    context={
        'time_range': '2025-01-01 to 2025-01-12',
        'playbooks': ['T1566-phishing', 'T1059-command']
    },
    anonymize=True
)

print(summary['executive_summary'])
```

## Best Practices

### When to Use AI Review

**Use AI Review For:**
- Initial triage of findings
- Validating suspicious findings
- Identifying false positives
- Getting second opinion on findings
- Batch processing large numbers of findings

**Don't Rely Solely On:**
- AI validation should complement, not replace, human analysis
- Always verify critical findings manually
- Use AI as a tool, not a decision-maker

### Data Anonymization

1. **Always Anonymize**: Never send real data to AI
2. **Verify Anonymization**: Check that anonymization worked
3. **Review Anonymized Data**: Ensure data still makes sense after anonymization
4. **Protect Mappings**: Keep anonymization mapping table secure

### API Usage

1. **Monitor Costs**: Track API usage and costs
2. **Rate Limiting**: Be aware of API rate limits
3. **Error Handling**: Handle API errors gracefully
4. **Batch Processing**: Process multiple findings in batches

### Review Process

1. **Review AI Results**: Always review AI recommendations
2. **Verify Critical Findings**: Manually verify critical findings
3. **Use AI Insights**: Leverage AI insights for investigation
4. **Document Decisions**: Document why you accept or reject AI recommendations

## AI Review Results Interpretation

### Example AI Review Result

```json
{
  "finding_id": "T1566_001",
  "validation_status": "valid",
  "recommended_status": "confirmed",
  "false_positive_risk": "low",
  "confidence_assessment": {
    "current": 0.75,
    "recommended": 0.90,
    "reasoning": "Strong evidence with multiple indicators"
  },
  "severity_assessment": {
    "current": "high",
    "recommended": "high",
    "reasoning": "Severity appropriate for threat type"
  },
  "evidence_quality": {
    "score": 0.85,
    "gaps": ["Missing network logs"],
    "recommendations": ["Collect network logs for correlation"]
  },
  "ai_review": {
    "review_text": "Finding appears valid based on evidence...",
    "reasoning": "Multiple indicators suggest phishing attempt..."
  }
}
```

### Interpreting Results

- **validation_status: "valid"**: Proceed with investigation
- **false_positive_risk: "low"**: Low risk, likely real threat
- **confidence: 0.90**: High confidence in finding
- **evidence_quality: 0.85**: Good evidence, but could be improved

## Troubleshooting

### AI Review Not Working

**Problem**: AI review fails or doesn't return results.

**Solutions:**
- Check OpenAI API key is configured
- Verify API key has sufficient credits
- Check API rate limits
- Review error logs
- Verify anonymization is working

### Anonymization Issues

**Problem**: Data not properly anonymized before AI.

**Solutions:**
- Check anonymization is enabled
- Verify database connection for mapping table
- Review anonymization logs
- Test anonymization separately

### API Errors

**Problem**: OpenAI API returns errors.

**Solutions:**
- Check API key validity
- Verify API quota/credits
- Review API error messages
- Check network connectivity
- Try different model if available

### Slow Performance

**Problem**: AI review takes too long.

**Solutions:**
- Use batch processing for multiple findings
- Reduce batch size if hitting rate limits
- Use faster model (gpt-3.5-turbo) if acceptable
- Process findings in parallel

## Security Considerations

### API Key Protection

- **Never Commit**: Never commit API keys to version control
- **Use Environment Variables**: Store keys in environment variables
- **Rotate Regularly**: Rotate API keys periodically
- **Limit Access**: Restrict who can access API keys

### Data Privacy

- **Always Anonymize**: Never send real data to AI
- **Review Anonymization**: Verify anonymization works correctly
- **Protect Mappings**: Secure anonymization mapping table
- **Audit Access**: Log all AI service access

### Cost Management

- **Monitor Usage**: Track API usage and costs
- **Set Limits**: Configure usage limits if possible
- **Optimize Queries**: Use appropriate models for tasks
- **Batch Processing**: Process multiple items together

## Integration Examples

### With Complete Hunt Workflow

AI review is automatically integrated:

1. Findings are generated
2. Findings are anonymized
3. AI reviews findings
4. Status is updated
5. Results included in report

### With Playbook Execution

```python
from automation_scripts.orchestrators.playbook_engine import PlaybookEngine
from automation_scripts.services.ai_service import AIService

# Execute playbook
engine = PlaybookEngine()
result = engine.execute_playbook(playbook_id, data_package)

# Review findings with AI
ai_service = AIService()
for finding in result['findings']:
    validation = ai_service.validate_finding(finding, anonymize=True)
    if validation['validation_status'] == 'valid':
        print(f"Valid finding: {finding['finding_id']}")
```

## Advanced Features

### Custom Prompts

You can customize AI prompts (advanced):

```python
# Customize prompts for specific use cases
ai_service.prompts.customize_finding_validation_prompt(
    additional_context="Focus on phishing indicators"
)
```

### Batch Processing

Process multiple findings efficiently:

```python
# Process 10 findings at once
findings = [finding1, finding2, ..., finding10]
validations = ai_service.validate_findings_batch(
    findings,
    batch_size=10,
    anonymize=True
)
```

### Correlation Analysis

Identify relationships between findings:

```python
# Correlate multiple findings
correlation = ai_service.correlate_findings(
    findings=[finding1, finding2, finding3],
    anonymize=True
)

if correlation['correlated']:
    print(f"Attack chain: {correlation['attack_chain']}")
```

## Summary

AI integration enhances threat hunting by providing:

- **Automated Validation**: Quick triage of findings
- **Executive Summaries**: High-level insights for stakeholders
- **Evidence Analysis**: Deep analysis of evidence
- **Finding Correlation**: Identification of attack patterns
- **Privacy Protection**: Automatic anonymization

**Key Takeaways:**
- AI review helps with initial triage
- Always anonymize data before AI
- Review AI recommendations manually
- Use AI as a tool, not a replacement
- Monitor API usage and costs

**Next Steps:**
- Try AI Review Workflow with sample findings
- Enable AI review in Complete Hunt Workflow
- Review AI-generated executive summaries
- Practice interpreting AI results

