"""
Deterministic Analyzer - Template for playbook analysis logic.

This module provides a deterministic analysis function that processes
normalized data and generates findings without AI dependencies.

Each playbook should implement its own analyzer.py with deterministic
logic specific to the MITRE ATT&CK technique being hunted.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re


def analyze(
    data: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    thresholds: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Analyze normalized data and generate findings.
    
    This is a template function. Each playbook should implement its own
    deterministic analysis logic based on the MITRE ATT&CK technique.
    
    Args:
        data: List of normalized data records
        metadata: Playbook metadata from metadata.yml
        thresholds: Optional analysis thresholds from config/thresholds.yml
    
    Returns:
        List of findings dictionaries
    
    Finding Structure:
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
    """
    findings = []
    
    if not data:
        return findings
    
    # Get technique information from metadata
    technique_id = metadata.get('mitre', {}).get('technique_id', 'UNKNOWN')
    technique_name = metadata.get('mitre', {}).get('technique_name', 'Unknown Technique')
    hypothesis = metadata.get('hypothesis', '')
    
    # Default thresholds if not provided
    if thresholds is None:
        thresholds = {
            'min_confidence': 0.7,
            'severity_mapping': {
                'critical': 0.9,
                'high': 0.8,
                'medium': 0.7,
                'low': 0.5
            }
        }
    
    # Example deterministic analysis logic
    # This should be replaced with technique-specific logic
    
    # Group data by source for analysis
    by_source = {}
    for record in data:
        source = record.get('source', 'unknown')
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(record)
    
    # Analyze each source
    for source, records in by_source.items():
        # Example: Detect suspicious patterns
        suspicious_records = _detect_suspicious_patterns(records, thresholds)
        
        if suspicious_records:
            finding = _create_finding(
                technique_id=technique_id,
                technique_name=technique_name,
                source=source,
                suspicious_records=suspicious_records,
                hypothesis=hypothesis,
                thresholds=thresholds
            )
            findings.append(finding)
    
    return findings


def _detect_suspicious_patterns(
    records: List[Dict[str, Any]],
    thresholds: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Detect suspicious patterns in records.
    
    This is a template function. Each playbook should implement
    technique-specific pattern detection logic.
    
    Args:
        records: List of data records
        thresholds: Analysis thresholds
    
    Returns:
        List of suspicious records
    """
    suspicious = []
    
    for record in records:
        # Example pattern detection logic
        # This should be replaced with technique-specific patterns
        
        # Check event type
        event_type = record.get('event_type', '').lower()
        normalized_fields = record.get('normalized_fields', {})
        
        # Example: Detect suspicious process names
        process_name = normalized_fields.get('process_name', '').lower()
        if process_name and _is_suspicious_process(process_name):
            suspicious.append(record)
            continue
        
        # Example: Detect suspicious command lines
        command_line = normalized_fields.get('command_line', '').lower()
        if command_line and _is_suspicious_command(command_line):
            suspicious.append(record)
            continue
        
        # Example: Detect suspicious file paths
        file_path = normalized_fields.get('file_path', '').lower()
        if file_path and _is_suspicious_path(file_path):
            suspicious.append(record)
            continue
    
    return suspicious


def _is_suspicious_process(process_name: str) -> bool:
    """
    Check if process name is suspicious.
    
    This is a template function. Each playbook should implement
    technique-specific process detection logic.
    """
    # Example suspicious process patterns
    suspicious_patterns = [
        r'powershell\.exe',
        r'cmd\.exe',
        r'wscript\.exe',
        r'cscript\.exe',
        r'rundll32\.exe',
        r'regsvr32\.exe'
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, process_name, re.IGNORECASE):
            return True
    
    return False


def _is_suspicious_command(command_line: str) -> bool:
    """
    Check if command line is suspicious.
    
    This is a template function. Each playbook should implement
    technique-specific command detection logic.
    """
    # Example suspicious command patterns
    suspicious_patterns = [
        r'-enc\s+',  # Encoded PowerShell
        r'-e\s+',    # Encoded command
        r'base64',   # Base64 encoding
        r'iex\s*\(', # Invoke-Expression
        r'downloadstring', # Download string
        r'invoke-webrequest',
        r'net\s+user', # User enumeration
        r'net\s+localgroup' # Group enumeration
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, command_line, re.IGNORECASE):
            return True
    
    return False


def _is_suspicious_path(file_path: str) -> bool:
    """
    Check if file path is suspicious.
    
    This is a template function. Each playbook should implement
    technique-specific path detection logic.
    """
    # Example suspicious path patterns
    suspicious_patterns = [
        r'temp\\',      # Temp directory
        r'appdata\\',   # AppData directory
        r'\\windows\\temp\\', # Windows temp
        r'\\users\\[^\\]+\\appdata\\local\\temp\\' # User temp
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, file_path, re.IGNORECASE):
            return True
    
    return False


def _create_finding(
    technique_id: str,
    technique_name: str,
    source: str,
    suspicious_records: List[Dict[str, Any]],
    hypothesis: str,
    thresholds: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a finding from suspicious records.
    
    Args:
        technique_id: MITRE technique ID
        technique_name: MITRE technique name
        source: Data source
        suspicious_records: List of suspicious records
        hypothesis: Threat hunting hypothesis
        thresholds: Analysis thresholds
    
    Returns:
        Finding dictionary
    """
    # Calculate confidence based on number of suspicious records
    record_count = len(suspicious_records)
    confidence = min(1.0, 0.5 + (record_count * 0.1))
    
    # Determine severity based on confidence
    severity = 'low'
    severity_mapping = thresholds.get('severity_mapping', {})
    if confidence >= severity_mapping.get('critical', 0.9):
        severity = 'critical'
    elif confidence >= severity_mapping.get('high', 0.8):
        severity = 'high'
    elif confidence >= severity_mapping.get('medium', 0.7):
        severity = 'medium'
    
    # Generate finding ID
    finding_id = f"{technique_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(suspicious_records)}"
    
    # Extract indicators
    indicators = _extract_indicators(suspicious_records)
    
    # Create finding
    finding = {
        'finding_id': finding_id,
        'technique_id': technique_id,
        'technique_name': technique_name,
        'severity': severity,
        'title': f"Suspicious activity detected: {technique_name}",
        'description': f"Detected {record_count} suspicious records matching {technique_name} patterns. {hypothesis}",
        'evidence': suspicious_records[:10],  # Limit evidence to first 10 records
        'evidence_count': len(suspicious_records),
        'timestamp': datetime.utcnow().isoformat(),
        'confidence': round(confidence, 2),
        'indicators': indicators,
        'recommendations': [
            f"Review all {record_count} suspicious records",
            f"Investigate source: {source}",
            f"Check for related MITRE ATT&CK technique: {technique_id}",
            "Consider additional threat hunting queries"
        ],
        'source': source
    }
    
    return finding


def _extract_indicators(records: List[Dict[str, Any]]) -> List[str]:
    """
    Extract indicators from suspicious records.
    
    Args:
        records: List of suspicious records
    
    Returns:
        List of unique indicators
    """
    indicators = set()
    
    for record in records:
        normalized_fields = record.get('normalized_fields', {})
        
        # Extract process names
        if 'process_name' in normalized_fields:
            indicators.add(f"Process: {normalized_fields['process_name']}")
        
        # Extract command lines
        if 'command_line' in normalized_fields:
            cmd = normalized_fields['command_line']
            # Extract key parts of command
            if len(cmd) > 100:
                cmd = cmd[:100] + "..."
            indicators.add(f"Command: {cmd}")
        
        # Extract file paths
        if 'file_path' in normalized_fields:
            indicators.add(f"File: {normalized_fields['file_path']}")
        
        # Extract hostnames
        if 'hostname' in normalized_fields:
            indicators.add(f"Host: {normalized_fields['hostname']}")
        
        # Extract IP addresses
        if 'ip_address' in normalized_fields:
            indicators.add(f"IP: {normalized_fields['ip_address']}")
    
    return list(indicators)[:20]  # Limit to 20 indicators

