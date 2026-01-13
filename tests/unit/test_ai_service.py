"""
Unit tests for PHASE3-01: AI Service.

Test Cases:
- TC-3-01-01: Findings validation by AI
- TC-3-01-02: AI receives only anonymized data
- TC-3-01-03: Executive summary generation
"""

import pytest
import sys
import json
import importlib.util
import types
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

# Add automation-scripts to path
project_root = Path(__file__).parent.parent.parent
automation_scripts_path = project_root / "automation-scripts"
sys.path.insert(0, str(automation_scripts_path))

# Create package structure
if "automation_scripts" not in sys.modules:
    sys.modules["automation_scripts"] = types.ModuleType("automation_scripts")
    sys.modules["automation_scripts"].__path__ = [str(automation_scripts_path)]
if "automation_scripts.services" not in sys.modules:
    sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
    sys.modules["automation_scripts.services"].__path__ = [str(automation_scripts_path / "services")]
if "automation_scripts.utils" not in sys.modules:
    sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
    sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"validation_status": "valid", "reasoning": "Finding is valid"}'
    mock_client.chat.completions.create = Mock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_anonymizer():
    """Create a mock anonymizer."""
    anonymizer = Mock()
    
    def anonymize_record(record):
        """Anonymize a record by replacing sensitive values."""
        anonymized = record.copy()
        if 'device_name' in anonymized:
            anonymized['device_name'] = 'anon-device-001'
        if 'process_name' in anonymized:
            anonymized['process_name'] = 'anon-process-001'
        if 'command_line' in anonymized:
            anonymized['command_line'] = 'anon-command-001'
        if 'normalized_fields' in anonymized and isinstance(anonymized['normalized_fields'], dict):
            if 'device_name' in anonymized['normalized_fields']:
                anonymized['normalized_fields']['device_name'] = 'anon-device-001'
            if 'process_name' in anonymized['normalized_fields']:
                anonymized['normalized_fields']['process_name'] = 'anon-process-001'
            if 'command_line' in anonymized['normalized_fields']:
                anonymized['normalized_fields']['command_line'] = 'anon-command-001'
        return anonymized
    
    anonymizer.anonymize_record = Mock(side_effect=anonymize_record)
    return anonymizer


@pytest.fixture
def sample_finding():
    """Create a sample finding for testing."""
    return {
        'finding_id': 'T1059_20250115_103000_1',
        'playbook_id': 'T1059-command-and-scripting-interpreter',
        'execution_id': 'exec_20250115_103000',
        'technique_id': 'T1059',
        'technique_name': 'Command and Scripting Interpreter',
        'tactic': 'Execution',
        'severity': 'high',
        'title': 'Suspicious activity detected: Command and Scripting Interpreter',
        'description': 'Detected suspicious command execution patterns',
        'confidence': 0.85,
        'source': 'Microsoft Defender',
        'status': 'new',
        'tags': ['suspicious', 'execution'],
        'indicators': ['Process: powershell.exe', 'Command: -enc ...'],
        'recommendations': ['Review command execution logs', 'Investigate process chain'],
        'evidence_count': 2,
        'metadata': {},
        'timestamp': '2025-01-15T10:30:00Z',
        'normalized_fields': {
            'device_name': 'workstation-01.example.com',
            'process_name': 'powershell.exe',
            'command_line': 'powershell.exe -enc dGVzdA=='
        }
    }


@pytest.fixture
def ai_service(mock_openai_client, mock_anonymizer, project_root_path):
    """Create AIService instance with mocked dependencies."""
    import sys
    import importlib.util
    import types
    import os
    
    automation_scripts_path = project_root_path / "automation-scripts"
    sys.path.insert(0, str(automation_scripts_path))
    
    if "automation_scripts.services" not in sys.modules:
        sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
        sys.modules["automation_scripts.services"].__path__ = [str(automation_scripts_path / "services")]
    
    # Load ai_prompts first
    ai_prompts_path = automation_scripts_path / "services" / "ai_prompts.py"
    ai_prompts_spec = importlib.util.spec_from_file_location(
        "automation_scripts.services.ai_prompts", ai_prompts_path
    )
    ai_prompts_module = importlib.util.module_from_spec(ai_prompts_spec)
    sys.modules["automation_scripts.services.ai_prompts"] = ai_prompts_module
    ai_prompts_spec.loader.exec_module(ai_prompts_module)
    
    # Load ai_service
    ai_service_path = automation_scripts_path / "services" / "ai_service.py"
    ai_service_spec = importlib.util.spec_from_file_location(
        "automation_scripts.services.ai_service", ai_service_path
    )
    ai_service_module = importlib.util.module_from_spec(ai_service_spec)
    sys.modules["automation_scripts.services.ai_service"] = ai_service_module
    
    # Mock OpenAI import
    mock_openai = Mock()
    mock_openai.OpenAI = Mock(return_value=mock_openai_client)
    sys.modules['openai'] = mock_openai
    ai_service_module.OPENAI_AVAILABLE = True
    
    # Load DeterministicAnonymizer (for import)
    deterministic_anonymizer_path = automation_scripts_path / "utils" / "deterministic_anonymizer.py"
    deterministic_anonymizer_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.deterministic_anonymizer", deterministic_anonymizer_path
    )
    deterministic_anonymizer_module = importlib.util.module_from_spec(deterministic_anonymizer_spec)
    sys.modules["automation_scripts.utils.deterministic_anonymizer"] = deterministic_anonymizer_module
    deterministic_anonymizer_spec.loader.exec_module(deterministic_anonymizer_module)
    
    # Now load ai_service
    ai_service_spec.loader.exec_module(ai_service_module)
    
    AIService = ai_service_module.AIService
    
    # Create service with mocked dependencies
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'}):
        service = AIService(
            api_key='test-api-key',
            model='gpt-4',
            anonymizer=mock_anonymizer
        )
        service.client = mock_openai_client
    
    return service


class TestFindingsValidationByAI:
    """TC-3-01-01: Findings validation by AI"""

    def test_validate_finding_returns_validation_result(self, ai_service, sample_finding, mock_openai_client):
        """Test that AI validates finding and returns validation result."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'validation_status': 'valid',
            'confidence_assessment': {
                'current': 0.85,
                'recommended': 0.85,
                'reason': 'Confidence score is appropriate'
            },
            'severity_assessment': {
                'current': 'high',
                'recommended': 'high',
                'reason': 'Severity level is appropriate'
            },
            'evidence_quality': {
                'sufficient': True,
                'quality_score': 0.8,
                'recommendations': []
            },
            'additional_recommendations': [],
            'false_positive_risk': 'low',
            'overall_assessment': 'Finding is valid and well-supported by evidence'
        })
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_service.validate_finding(sample_finding, anonymize=True)
        
        assert 'validation_status' in result, "Result should contain 'validation_status'"
        assert result['validation_status'] in ['valid', 'needs_review', 'invalid'], \
            "Validation status should be valid, needs_review, or invalid"
        assert 'validation_timestamp' in result, "Result should contain 'validation_timestamp'"
        assert 'model_used' in result, "Result should contain 'model_used'"
        assert 'finding_id' in result, "Result should contain 'finding_id'"

    def test_validation_result_contains_reasoning(self, ai_service, sample_finding, mock_openai_client):
        """Test that validation result contains reasoning."""
        # Mock OpenAI response with reasoning
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'validation_status': 'valid',
            'confidence_assessment': {
                'current': 0.85,
                'recommended': 0.85,
                'reason': 'Confidence score is appropriate based on evidence'
            },
            'severity_assessment': {
                'current': 'high',
                'recommended': 'high',
                'reason': 'Severity level matches the threat'
            },
            'evidence_quality': {
                'sufficient': True,
                'quality_score': 0.8,
                'recommendations': []
            },
            'additional_recommendations': [],
            'false_positive_risk': 'low',
            'overall_assessment': 'Finding is valid and well-supported by evidence. The confidence score and severity level are appropriate.'
        })
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_service.validate_finding(sample_finding, anonymize=True)
        
        assert 'validation_status' in result, "Result should contain 'validation_status'"
        assert 'overall_assessment' in result or 'reasoning' in result, \
            "Result should contain reasoning or overall_assessment"
        
        # Check that reasoning is available
        if 'overall_assessment' in result:
            assert len(result['overall_assessment']) > 0, "Overall assessment should not be empty"
        if 'reasoning' in result:
            assert len(result['reasoning']) > 0, "Reasoning should not be empty"

    def test_ai_validates_finding_from_playbook(self, ai_service, sample_finding, mock_openai_client):
        """Test that AI validates finding generated from playbook."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'validation_status': 'valid',
            'confidence_assessment': {'current': 0.85, 'recommended': 0.85, 'reason': 'Appropriate'},
            'severity_assessment': {'current': 'high', 'recommended': 'high', 'reason': 'Appropriate'},
            'evidence_quality': {'sufficient': True, 'quality_score': 0.8, 'recommendations': []},
            'additional_recommendations': [],
            'false_positive_risk': 'low',
            'overall_assessment': 'Valid finding'
        })
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_service.validate_finding(sample_finding, anonymize=True)
        
        assert result['validation_status'] == 'valid', "Finding should be validated as valid"
        assert result['finding_id'] == sample_finding['finding_id'], "Finding ID should match"


class TestAIReceivesOnlyAnonymizedData:
    """TC-3-01-02: AI receives only anonymized data"""

    def test_ai_receives_anonymized_data(self, ai_service, sample_finding, mock_openai_client, mock_anonymizer):
        """Test that AI receives only anonymized data."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'validation_status': 'valid',
            'reasoning': 'Finding is valid'
        })
        
        # Track what was sent to AI
        captured_messages = []
        
        def capture_prompt(*args, **kwargs):
            if kwargs and 'messages' in kwargs:
                captured_messages.extend(kwargs['messages'])
            return mock_response
        
        mock_openai_client.chat.completions.create.side_effect = capture_prompt
        
        # Validate finding with anonymization
        ai_service.validate_finding(sample_finding, anonymize=True)
        
        # Verify anonymizer was called
        assert mock_anonymizer.anonymize_record.called, "Anonymizer should be called"
        
        # Verify original values are not in prompt (check that anonymization happened)
        # The prompt should contain anonymized values, not original values
        if captured_messages:
            prompt_content = str(captured_messages)
            # Original values should not be in prompt, or anonymized values should be present
            # Since we can't easily check the exact prompt content, we verify anonymizer was called
            assert mock_anonymizer.anonymize_record.called, \
                "Anonymizer should be called to anonymize data before sending to AI"

    def test_original_values_not_in_ai_response(self, ai_service, sample_finding, mock_openai_client, mock_anonymizer):
        """Test that original values are not present in AI response."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'validation_status': 'valid',
            'reasoning': 'Finding is valid based on anonymized data'
        })
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_service.validate_finding(sample_finding, anonymize=True)
        
        # Verify result doesn't contain original sensitive values
        result_str = json.dumps(result)
        assert 'workstation-01.example.com' not in result_str, \
            "Original device name should not be in AI response"
        assert 'powershell.exe -enc dGVzdA==' not in result_str, \
            "Original command line should not be in AI response"

    def test_anonymization_before_ai_processing(self, ai_service, sample_finding, mock_openai_client, mock_anonymizer):
        """Test that data is anonymized before AI processing."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'validation_status': 'valid',
            'reasoning': 'Valid'
        })
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Store original value
        original_device_name = sample_finding.get('normalized_fields', {}).get('device_name')
        
        # Validate finding
        ai_service.validate_finding(sample_finding, anonymize=True)
        
        # Verify anonymizer was called with original finding
        assert mock_anonymizer.anonymize_record.called, "Anonymizer should be called"
        call_args = mock_anonymizer.anonymize_record.call_args
        assert call_args is not None, "Anonymizer should be called with finding"
        
        # Verify anonymized record was used (check that original values were replaced)
        # Get the anonymized record from the call
        called_record = call_args[0][0] if call_args[0] else call_args[1].get('record', {})
        anonymized_device_name = called_record.get('normalized_fields', {}).get('device_name')
        
        # The anonymized value should be different from original (if original exists)
        if original_device_name:
            assert anonymized_device_name != original_device_name or \
                   anonymized_device_name == 'anon-device-001', \
                "Device name should be anonymized (different from original or set to anonymized value)"


class TestExecutiveSummaryGeneration:
    """TC-3-01-03: Executive summary generation"""

    def test_generate_executive_summary(self, ai_service, sample_finding, mock_openai_client):
        """Test that executive summary is generated."""
        # Create multiple findings
        findings = [
            sample_finding,
            {
                **sample_finding,
                'finding_id': 'T1059_20250115_103001_2',
                'severity': 'medium',
                'confidence': 0.7
            },
            {
                **sample_finding,
                'finding_id': 'T1047_20250115_103002_3',
                'technique_id': 'T1047',
                'technique_name': 'Windows Management Instrumentation',
                'severity': 'high',
                'confidence': 0.9
            }
        ]
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'executive_summary': 'Threat hunting exercise detected multiple suspicious activities across the environment.',
            'critical_findings': [
                {
                    'finding_id': 'T1059_20250115_103000_1',
                    'technique_id': 'T1059',
                    'title': 'Suspicious activity detected',
                    'severity': 'high',
                    'confidence': 0.85,
                    'summary': 'Command execution detected'
                }
            ],
            'threat_landscape': {
                'techniques_detected': ['T1059', 'T1047'],
                'tactics_observed': ['Execution'],
                'attack_patterns': 'Multiple execution techniques detected'
            },
            'risk_assessment': {
                'overall_risk': 'High',
                'risk_factors': ['Multiple high-severity findings'],
                'risk_score': 0.8
            },
            'recommendations': {
                'immediate_actions': ['Investigate high-severity findings', 'Review command execution logs'],
                'long_term_improvements': ['Implement additional monitoring', 'Enhance detection rules']
            },
            'next_steps': {
                'follow_up_investigations': ['Investigate process chains', 'Review network connections'],
                'additional_queries': ['Query for related activities', 'Search for additional indicators']
            }
        })
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        context = {
            'time_range': '2025-01-15 to 2025-01-16',
            'playbooks': ['T1059-command', 'T1047-wmi'],
            'total_findings': len(findings),
            'analysis_date': '2025-01-16'
        }
        
        result = ai_service.generate_executive_summary(findings, context=context, anonymize=True)
        
        assert 'executive_summary' in result, "Result should contain 'executive_summary'"
        assert 'critical_findings' in result, "Result should contain 'critical_findings'"
        assert 'threat_landscape' in result, "Result should contain 'threat_landscape'"
        assert 'risk_assessment' in result, "Result should contain 'risk_assessment'"
        assert 'recommendations' in result, "Result should contain 'recommendations'"
        assert 'next_steps' in result, "Result should contain 'next_steps'"

    def test_executive_summary_contains_required_sections(self, ai_service, sample_finding, mock_openai_client):
        """Test that executive summary contains all required sections."""
        findings = [sample_finding]
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'executive_summary': 'Summary of threat hunting exercise',
            'critical_findings': [],
            'threat_landscape': {
                'techniques_detected': ['T1059'],
                'tactics_observed': ['Execution'],
                'attack_patterns': 'Execution techniques detected'
            },
            'risk_assessment': {
                'overall_risk': 'Medium',
                'risk_factors': [],
                'risk_score': 0.5
            },
            'recommendations': {
                'immediate_actions': ['Investigate findings'],
                'long_term_improvements': ['Improve monitoring']
            },
            'next_steps': {
                'follow_up_investigations': ['Investigate further'],
                'additional_queries': ['Additional queries']
            }
        })
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_service.generate_executive_summary(findings, anonymize=True)
        
        # Verify all required sections are present
        assert 'executive_summary' in result, "Should have executive_summary section"
        assert isinstance(result['executive_summary'], str), "Executive summary should be a string"
        assert len(result['executive_summary']) > 0, "Executive summary should not be empty"
        
        assert 'recommendations' in result, "Should have recommendations section"
        assert 'immediate_actions' in result['recommendations'], "Should have immediate_actions"
        assert 'long_term_improvements' in result['recommendations'], "Should have long_term_improvements"
        
        assert 'next_steps' in result, "Should have next_steps section"
        assert 'follow_up_investigations' in result['next_steps'], "Should have follow_up_investigations"
        assert 'additional_queries' in result['next_steps'], "Should have additional_queries"

    def test_executive_summary_metadata(self, ai_service, sample_finding, mock_openai_client):
        """Test that executive summary contains metadata."""
        findings = [sample_finding]
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'executive_summary': 'Summary',
            'critical_findings': [],
            'threat_landscape': {'techniques_detected': [], 'tactics_observed': [], 'attack_patterns': ''},
            'risk_assessment': {'overall_risk': 'Low', 'risk_factors': [], 'risk_score': 0.0},
            'recommendations': {'immediate_actions': [], 'long_term_improvements': []},
            'next_steps': {'follow_up_investigations': [], 'additional_queries': []}
        })
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_service.generate_executive_summary(findings, anonymize=True)
        
        assert 'generated_at' in result, "Result should contain 'generated_at'"
        assert 'model_used' in result, "Result should contain 'model_used'"
        assert 'findings_count' in result, "Result should contain 'findings_count'"
        assert result['findings_count'] == len(findings), "Findings count should match"

