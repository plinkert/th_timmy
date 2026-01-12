# Playbook Engine - Deterministic Analysis

## Overview

The Playbook Engine provides deterministic analysis execution for threat hunting playbooks. It processes data packages and executes playbook analyzers without AI dependencies, ensuring consistent and reproducible results.

## Purpose

- **Deterministic Analysis**: Consistent results without AI variability
- **Data Package Integration**: Works with standardized DataPackage structure
- **Anonymization Support**: Optional anonymization before analysis
- **Playbook Execution**: Executes playbook analyzers with normalized data
- **Findings Generation**: Generates structured findings from analysis

## Features

### 1. Deterministic Execution

- **No AI Dependencies**: Pure deterministic logic
- **Reproducible Results**: Same input always produces same output
- **Consistent Analysis**: Predictable analysis behavior

### 2. Data Package Integration

- **Standardized Input**: Uses DataPackage for consistent data structure
- **Metadata Preservation**: Maintains data provenance
- **Validation**: Validates data packages before execution

### 3. Anonymization Support

- **Optional Anonymization**: Anonymize data before analysis
- **Deterministic Anonymization**: Uses DeterministicAnonymizer
- **Deanonymization**: Deanonymize findings after analysis
- **Mapping Table**: Preserves ability to deanonymize results

### 4. Playbook Execution

- **Dynamic Loading**: Loads analyzer modules from playbooks
- **Metadata Integration**: Uses playbook metadata for context
- **Error Handling**: Robust error handling and logging
- **Sequential Execution**: Execute multiple playbooks sequentially

## Usage

### Basic Usage

```python
from automation_scripts.orchestrators import PlaybookEngine
from automation_scripts.utils import DataPackage

# Create data package
package = DataPackage(
    source_type="manual",
    source_name="user_upload",
    data=normalized_data
)

# Initialize engine
engine = PlaybookEngine()

# Execute playbook
result = engine.execute_playbook(
    playbook_id="T1566-phishing",
    data_package=package
)

print(f"Found {result['findings_count']} findings")
```

### With Anonymization

```python
from automation_scripts.orchestrators import PlaybookEngine
from automation_scripts.utils import DataPackage, DeterministicAnonymizer

# Create anonymizer
anonymizer = DeterministicAnonymizer(
    db_config={
        'host': 'vm02',
        'port': 5432,
        'database': 'threat_hunting',
        'user': 'threat_hunter',
        'password': 'password'
    }
)

# Create data package
package = DataPackage(
    source_type="api",
    source_name="Microsoft Defender",
    data=normalized_data
)

# Initialize engine with anonymizer
engine = PlaybookEngine(anonymizer=anonymizer)

# Execute with anonymization
result = engine.execute_playbook(
    playbook_id="T1566-phishing",
    data_package=package,
    anonymize_before=True,
    deanonymize_after=True
)
```

### Sequential Execution

```python
# Execute multiple playbooks
playbook_data_map = {
    "T1566-phishing": package1,
    "T1059-command": package2,
    "T1021-remote": package3
}

results = engine.execute_playbooks_sequentially(
    playbook_data_map=playbook_data_map,
    anonymize_before=True,
    deanonymize_after=True
)

# Get summary
summary = engine.get_execution_summary(results)
print(f"Total findings: {summary['total_findings']}")
print(f"Severity distribution: {summary['severity_distribution']}")
```

## Playbook Analyzer

Each playbook must have an `analyzer.py` file in `scripts/` directory with an `analyze()` function.

### Analyzer Function Signature

```python
def analyze(
    data: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    thresholds: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Analyze normalized data and generate findings.
    
    Args:
        data: List of normalized data records
        metadata: Playbook metadata from metadata.yml
        thresholds: Optional analysis thresholds
    
    Returns:
        List of findings dictionaries
    """
    findings = []
    # Implement deterministic analysis logic
    return findings
```

### Finding Structure

```python
{
    'finding_id': str,           # Unique finding identifier
    'technique_id': str,          # MITRE technique ID
    'severity': str,              # low, medium, high, critical
    'title': str,                 # Finding title
    'description': str,           # Finding description
    'evidence': List[Dict],       # Evidence records
    'timestamp': str,             # ISO timestamp
    'confidence': float,          # Confidence score (0.0-1.0)
    'indicators': List[str],      # List of indicators
    'recommendations': List[str]  # List of recommendations
}
```

## Template Analyzer

The template analyzer (`playbooks/template/scripts/analyzer.py`) provides:

- **Pattern Detection**: Example patterns for suspicious activities
- **Finding Creation**: Helper functions for creating findings
- **Indicator Extraction**: Functions to extract indicators
- **Severity Calculation**: Logic for determining severity

### Customizing Analyzer

Each playbook should customize the analyzer for its specific technique:

1. **Copy template analyzer**:
   ```bash
   cp playbooks/template/scripts/analyzer.py playbooks/T1566-phishing/scripts/analyzer.py
   ```

2. **Implement technique-specific logic**:
   - Replace pattern detection with technique-specific patterns
   - Customize finding creation for technique context
   - Add technique-specific indicators

3. **Test analyzer**:
   ```python
   from playbooks.T1566_phishing.scripts.analyzer import analyze
   
   findings = analyze(test_data, metadata)
   ```

## Integration

### With DataPackage

```python
# Create package
package = DataPackage(
    source_type="api",
    source_name="Microsoft Defender",
    data=normalized_data,
    query_info={
        "technique_id": "T1566",
        "tool": "Microsoft Defender"
    }
)

# Execute playbook
result = engine.execute_playbook("T1566-phishing", package)
```

### With DeterministicAnonymizer

```python
# Initialize anonymizer
anonymizer = DeterministicAnonymizer(db_config=db_config)

# Initialize engine
engine = PlaybookEngine(anonymizer=anonymizer)

# Execute with anonymization
result = engine.execute_playbook(
    playbook_id="T1566-phishing",
    data_package=package,
    anonymize_before=True,
    deanonymize_after=True
)
```

### With Playbook Validator

The engine automatically validates playbooks before execution:

```python
# Engine validates playbook structure
result = engine.execute_playbook("T1566-phishing", package)

# Validation status in result
validation_status = result['validation_status']
if not validation_status['is_valid']:
    print(f"Warnings: {validation_status['warnings']}")
```

## Execution Flow

1. **Load Playbook**: Load playbook metadata and structure
2. **Validate Playbook**: Validate playbook structure and metadata
3. **Prepare Data**: Extract data from DataPackage
4. **Anonymize (Optional)**: Anonymize data if requested
5. **Load Analyzer**: Load analyzer module from playbook
6. **Execute Analysis**: Run analyzer.analyze() function
7. **Deanonymize (Optional)**: Deanonymize findings if requested
8. **Return Results**: Return findings and execution metadata

## Error Handling

```python
from automation_scripts.orchestrators import PlaybookEngineError, PlaybookExecutionError

try:
    result = engine.execute_playbook("T1566-phishing", package)
except PlaybookExecutionError as e:
    print(f"Execution failed: {e}")
except PlaybookEngineError as e:
    print(f"Engine error: {e}")
```

## Best Practices

1. **Deterministic Logic**: Use deterministic patterns and rules
2. **Error Handling**: Handle errors gracefully
3. **Logging**: Log important operations
4. **Testing**: Test analyzers with sample data
5. **Documentation**: Document analysis logic

## Examples

### Example 1: Basic Execution

```python
from automation_scripts.orchestrators import PlaybookEngine
from automation_scripts.utils import DataPackage

# Prepare data
normalized_data = [
    {
        'timestamp': '2024-01-15T10:30:00Z',
        'source': 'Microsoft Defender',
        'event_type': 'ProcessCreated',
        'raw_data': {...},
        'normalized_fields': {
            'process_name': 'powershell.exe',
            'command_line': 'powershell -enc ...'
        }
    }
]

# Create package
package = DataPackage(
    source_type="manual",
    source_name="test_data",
    data=normalized_data
)

# Execute
engine = PlaybookEngine()
result = engine.execute_playbook("T1059-command", package)

# Review findings
for finding in result['findings']:
    print(f"{finding['severity']}: {finding['title']}")
```

### Example 2: With Anonymization

```python
from automation_scripts.orchestrators import PlaybookEngine
from automation_scripts.utils import DataPackage, DeterministicAnonymizer

# Setup anonymizer
anonymizer = DeterministicAnonymizer(
    db_config={
        'host': 'vm02',
        'database': 'threat_hunting',
        'user': 'threat_hunter',
        'password': 'password'
    }
)

# Create package
package = DataPackage(
    source_type="api",
    source_name="Microsoft Defender",
    data=sensitive_data
)

# Execute with anonymization
engine = PlaybookEngine(anonymizer=anonymizer)
result = engine.execute_playbook(
    playbook_id="T1566-phishing",
    data_package=package,
    anonymize_before=True,
    deanonymize_after=True
)

# Findings are deanonymized
for finding in result['findings']:
    print(finding['indicators'])  # Original values restored
```

## Future Enhancements

- Parallel execution support
- Caching for performance
- Advanced pattern matching
- Machine learning integration (optional)
- Real-time execution monitoring

