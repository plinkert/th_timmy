"""
Unit tests for PHASE3-03: Executive Summary Generator.

Test Cases:
- TC-3-03-01: Generate summary from aggregated findings
- TC-3-03-02: Format summary according to template
- TC-3-03-03: Summary content (description, recommendations, next steps)
- TC-3-03-04: AI Service integration
- TC-3-03-05: Save summary to file/report
- TC-3-03-06: Summary for different hunt types
- TC-3-03-07: Aggregate findings from multiple sources
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
import tempfile
import shutil

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
def mock_ai_service():
    """Create a mock AI Service."""
    ai_service = Mock()
    
    # Mock generate_executive_summary
    ai_service.generate_executive_summary = Mock(return_value={
        'executive_summary': 'Threat hunting exercise detected multiple suspicious activities across the environment.',
        'critical_findings': [
            {
                'finding_id': 'T1059_001',
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
        },
        'generated_at': datetime.utcnow().isoformat(),
        'model_used': 'gpt-4',
        'findings_count': 5
    })
    
    return ai_service


@pytest.fixture
def mock_anonymizer():
    """Create a mock anonymizer."""
    anonymizer = Mock()
    
    def anonymize_record(record):
        """Anonymize a record by replacing sensitive values."""
        anonymized = record.copy()
        if 'normalized_fields' in anonymized and isinstance(anonymized['normalized_fields'], dict):
            if 'device_name' in anonymized['normalized_fields']:
                anonymized['normalized_fields']['device_name'] = 'anon-device-001'
        return anonymized
    
    anonymizer.anonymize_record = Mock(side_effect=anonymize_record)
    return anonymizer


@pytest.fixture
def sample_findings():
    """Create sample findings for testing."""
    return [
        {
            'finding_id': 'T1059_20250115_103000_1',
            'playbook_id': 'T1059-command-and-scripting-interpreter',
            'technique_id': 'T1059',
            'technique_name': 'Command and Scripting Interpreter',
            'tactic': 'Execution',
            'severity': 'high',
            'confidence': 0.85,
            'title': 'Suspicious activity detected: Command and Scripting Interpreter',
            'description': 'Detected suspicious command execution patterns',
            'source': 'Microsoft Defender',
            'timestamp': '2025-01-15T10:30:00Z'
        },
        {
            'finding_id': 'T1047_20250115_103001_2',
            'playbook_id': 'T1047-wmi',
            'technique_id': 'T1047',
            'technique_name': 'Windows Management Instrumentation',
            'tactic': 'Execution',
            'severity': 'medium',
            'confidence': 0.7,
            'title': 'Suspicious WMI activity detected',
            'description': 'Detected suspicious WMI execution',
            'source': 'Sentinel',
            'timestamp': '2025-01-15T10:30:01Z'
        },
        {
            'finding_id': 'T1071_20250115_103002_3',
            'playbook_id': 'T1071-application-layer-protocol',
            'technique_id': 'T1071',
            'technique_name': 'Application Layer Protocol',
            'tactic': 'Command and Control',
            'severity': 'high',
            'confidence': 0.9,
            'title': 'Suspicious network activity detected',
            'description': 'Detected suspicious network connections',
            'source': 'Firewall',
            'timestamp': '2025-01-15T10:30:02Z'
        }
    ]


@pytest.fixture
def executive_summary_generator(mock_ai_service, mock_anonymizer, project_root_path):
    """Create ExecutiveSummaryGenerator instance with mocked dependencies."""
    import sys
    import importlib.util
    import types
    import os
    
    automation_scripts_path = project_root_path / "automation-scripts"
    sys.path.insert(0, str(automation_scripts_path))
    
    if "automation_scripts.services" not in sys.modules:
        sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
        sys.modules["automation_scripts.services"].__path__ = [str(automation_scripts_path / "services")]
    
    # Load dependencies
    # Load ai_prompts first
    ai_prompts_path = automation_scripts_path / "services" / "ai_prompts.py"
    ai_prompts_spec = importlib.util.spec_from_file_location(
        "automation_scripts.services.ai_prompts", ai_prompts_path
    )
    ai_prompts_module = importlib.util.module_from_spec(ai_prompts_spec)
    sys.modules["automation_scripts.services.ai_prompts"] = ai_prompts_module
    ai_prompts_spec.loader.exec_module(ai_prompts_module)
    
    # Load ai_service (for import)
    ai_service_path = automation_scripts_path / "services" / "ai_service.py"
    ai_service_spec = importlib.util.spec_from_file_location(
        "automation_scripts.services.ai_service", ai_service_path
    )
    ai_service_module = importlib.util.module_from_spec(ai_service_spec)
    sys.modules["automation_scripts.services.ai_service"] = ai_service_module
    
    # Mock OpenAI import
    mock_openai = Mock()
    mock_openai.OpenAI = Mock()
    sys.modules['openai'] = mock_openai
    ai_service_module.OPENAI_AVAILABLE = True
    
    ai_service_spec.loader.exec_module(ai_service_module)
    
    # Load deterministic_anonymizer (for import)
    deterministic_anonymizer_path = automation_scripts_path / "utils" / "deterministic_anonymizer.py"
    deterministic_anonymizer_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.deterministic_anonymizer", deterministic_anonymizer_path
    )
    deterministic_anonymizer_module = importlib.util.module_from_spec(deterministic_anonymizer_spec)
    sys.modules["automation_scripts.utils.deterministic_anonymizer"] = deterministic_anonymizer_module
    deterministic_anonymizer_spec.loader.exec_module(deterministic_anonymizer_module)
    
    # Load executive_summary_generator
    executive_summary_generator_path = automation_scripts_path / "services" / "executive_summary_generator.py"
    executive_summary_generator_spec = importlib.util.spec_from_file_location(
        "automation_scripts.services.executive_summary_generator", executive_summary_generator_path
    )
    executive_summary_generator_module = importlib.util.module_from_spec(executive_summary_generator_spec)
    sys.modules["automation_scripts.services.executive_summary_generator"] = executive_summary_generator_module
    executive_summary_generator_spec.loader.exec_module(executive_summary_generator_module)
    
    ExecutiveSummaryGenerator = executive_summary_generator_module.ExecutiveSummaryGenerator
    
    # Create generator with mocked dependencies
    generator = ExecutiveSummaryGenerator(
        config_path=None,
        ai_service=mock_ai_service,
        anonymizer=mock_anonymizer
    )
    
    return generator


class TestGenerateSummaryFromAggregatedFindings:
    """TC-3-03-01: Generate summary from aggregated findings"""

    def test_generate_summary_from_aggregated_findings(self, executive_summary_generator, sample_findings):
        """Test that summary is generated from aggregated findings."""
        # Generate summary from aggregated findings
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            context={
                'time_range': '2025-01-15 to 2025-01-16',
                'playbooks_executed': ['T1059-command', 'T1047-wmi', 'T1071-application-layer-protocol']
            },
            format='markdown'
        )
        
        assert 'summary_id' in result, "Result should contain 'summary_id'"
        assert 'generated_at' in result, "Result should contain 'generated_at'"
        assert 'findings_count' in result, "Result should contain 'findings_count'"
        assert result['findings_count'] == len(sample_findings), "Findings count should match"
        assert 'ai_summary' in result, "Result should contain 'ai_summary'"
        assert 'statistics' in result, "Result should contain 'statistics'"

    def test_summary_contains_statistics(self, executive_summary_generator, sample_findings):
        """Test that summary contains statistics of findings."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        assert 'statistics' in result, "Result should contain 'statistics'"
        statistics = result['statistics']
        assert 'total_findings' in statistics, "Statistics should contain 'total_findings'"
        assert statistics['total_findings'] == len(sample_findings), "Total findings should match"
        assert 'severity_distribution' in statistics, "Statistics should contain 'severity_distribution'"
        assert 'technique_distribution' in statistics, "Statistics should contain 'technique_distribution'"

    def test_summary_aggregates_all_findings(self, executive_summary_generator, sample_findings):
        """Test that summary aggregates all findings."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        # Check that all findings are included in statistics
        statistics = result['statistics']
        assert statistics['total_findings'] == 3, "Should aggregate all 3 findings"
        
        # Check technique distribution
        technique_distribution = statistics['technique_distribution']
        assert 'T1059' in technique_distribution, "Should include T1059"
        assert 'T1047' in technique_distribution, "Should include T1047"
        assert 'T1071' in technique_distribution, "Should include T1071"


class TestFormatSummaryAccordingToTemplate:
    """TC-3-03-02: Format summary according to template"""

    def test_summary_formatted_according_to_template(self, executive_summary_generator, sample_findings):
        """Test that summary is formatted according to template."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        assert 'markdown' in result, "Result should contain 'markdown'"
        markdown = result['markdown']
        assert isinstance(markdown, str), "Markdown should be a string"
        assert len(markdown) > 0, "Markdown should not be empty"
        
        # Check that template sections are present
        assert '# Executive Summary' in markdown or 'Executive Summary' in markdown, \
            "Should contain Executive Summary section"
        assert 'Executive Overview' in markdown or 'executive_summary' in markdown.lower(), \
            "Should contain Executive Overview section"

    def test_template_sections_present(self, executive_summary_generator, sample_findings):
        """Test that all template sections are present."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        markdown = result['markdown']
        
        # Check for key sections (may vary based on template)
        assert 'Executive' in markdown or 'Summary' in markdown, \
            "Should contain Executive Summary section"
        # Template may have different section names, so we check for general structure
        assert len(markdown) > 100, "Markdown should have substantial content"

    def test_formatting_readable(self, executive_summary_generator, sample_findings):
        """Test that formatting is readable."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        markdown = result['markdown']
        
        # Check that markdown is readable (has structure)
        assert '\n' in markdown, "Markdown should have line breaks"
        # Check that it's not just one long line
        lines = markdown.split('\n')
        assert len(lines) > 5, "Markdown should have multiple lines"


class TestSummaryContent:
    """TC-3-03-03: Summary content (description, recommendations, next steps)"""

    def test_summary_contains_overview(self, executive_summary_generator, sample_findings):
        """Test that summary contains Overview section with description."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        # Check AI summary contains overview
        ai_summary = result['ai_summary']
        assert 'executive_summary' in ai_summary, "AI summary should contain 'executive_summary'"
        assert len(ai_summary['executive_summary']) > 0, "Executive summary should not be empty"
        
        # Check markdown contains overview
        markdown = result['markdown']
        assert 'Executive Overview' in markdown or 'executive_summary' in markdown.lower(), \
            "Markdown should contain Overview section"

    def test_summary_contains_key_findings(self, executive_summary_generator, sample_findings):
        """Test that summary contains Key Findings section."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        # Check AI summary contains critical findings
        ai_summary = result['ai_summary']
        assert 'critical_findings' in ai_summary, "AI summary should contain 'critical_findings'"
        
        # Check markdown contains findings
        markdown = result['markdown']
        assert 'Critical Findings' in markdown or 'Findings' in markdown, \
            "Markdown should contain Findings section"

    def test_summary_contains_recommendations(self, executive_summary_generator, sample_findings):
        """Test that summary contains Recommendations section."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        # Check AI summary contains recommendations
        ai_summary = result['ai_summary']
        assert 'recommendations' in ai_summary, "AI summary should contain 'recommendations'"
        recommendations = ai_summary['recommendations']
        assert 'immediate_actions' in recommendations, "Should have immediate_actions"
        assert 'long_term_improvements' in recommendations, "Should have long_term_improvements"
        
        # Check markdown contains recommendations
        markdown = result['markdown']
        assert 'Recommendations' in markdown or 'recommendations' in markdown.lower(), \
            "Markdown should contain Recommendations section"

    def test_summary_contains_next_steps(self, executive_summary_generator, sample_findings):
        """Test that summary contains Next Steps section."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        # Check AI summary contains next steps
        ai_summary = result['ai_summary']
        assert 'next_steps' in ai_summary, "AI summary should contain 'next_steps'"
        next_steps = ai_summary['next_steps']
        assert 'follow_up_investigations' in next_steps, "Should have follow_up_investigations"
        assert 'additional_queries' in next_steps, "Should have additional_queries"
        
        # Check markdown contains next steps
        markdown = result['markdown']
        assert 'Next Steps' in markdown or 'next steps' in markdown.lower(), \
            "Markdown should contain Next Steps section"

    def test_all_sections_filled(self, executive_summary_generator, sample_findings):
        """Test that all sections are filled (not empty)."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        ai_summary = result['ai_summary']
        
        # Check that sections are not empty
        assert len(ai_summary.get('executive_summary', '')) > 0, "Executive summary should not be empty"
        assert len(ai_summary.get('recommendations', {}).get('immediate_actions', [])) > 0, \
            "Immediate actions should not be empty"
        assert len(ai_summary.get('next_steps', {}).get('follow_up_investigations', [])) > 0, \
            "Follow-up investigations should not be empty"


class TestAIServiceIntegration:
    """TC-3-03-04: AI Service integration"""

    def test_ai_service_called(self, executive_summary_generator, sample_findings, mock_ai_service):
        """Test that AI Service is called."""
        # Reset mock call count
        mock_ai_service.generate_executive_summary.reset_mock()
        
        # Generate summary
        executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        # Verify AI Service was called
        assert mock_ai_service.generate_executive_summary.called, "AI Service should be called"
        assert mock_ai_service.generate_executive_summary.call_count == 1, \
            "AI Service should be called once"

    def test_prompt_formatted_correctly(self, executive_summary_generator, sample_findings, mock_ai_service):
        """Test that prompt is correctly formatted."""
        # Generate summary
        executive_summary_generator.generate_summary(
            findings=sample_findings,
            context={'time_range': '2025-01-15 to 2025-01-16'},
            format='markdown'
        )
        
        # Verify AI Service was called with correct arguments
        assert mock_ai_service.generate_executive_summary.called, "AI Service should be called"
        call_args = mock_ai_service.generate_executive_summary.call_args
        assert call_args is not None, "AI Service should be called with arguments"
        
        # Check that findings were passed
        assert 'findings' in call_args.kwargs or len(call_args[0]) > 0, \
            "Findings should be passed to AI Service"

    def test_ai_response_processed(self, executive_summary_generator, sample_findings):
        """Test that AI response is processed."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        # Check that AI summary is in result
        assert 'ai_summary' in result, "Result should contain 'ai_summary'"
        ai_summary = result['ai_summary']
        assert 'executive_summary' in ai_summary, "AI summary should contain 'executive_summary'"
        
        # Check that markdown contains AI-generated content
        markdown = result['markdown']
        assert len(markdown) > 0, "Markdown should contain AI-generated content"

    def test_summary_contains_ai_content(self, executive_summary_generator, sample_findings):
        """Test that summary contains content generated by AI."""
        result = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        # Check that AI summary is included
        assert 'ai_summary' in result, "Result should contain 'ai_summary'"
        ai_summary = result['ai_summary']
        
        # Check that AI-generated content is present
        assert 'executive_summary' in ai_summary, "Should have executive_summary from AI"
        assert 'recommendations' in ai_summary, "Should have recommendations from AI"
        assert 'next_steps' in ai_summary, "Should have next_steps from AI"


class TestSaveSummaryToFile:
    """TC-3-03-05: Save summary to file/report"""

    def test_summary_saved_to_file(self, executive_summary_generator, sample_findings, temp_dir):
        """Test that summary is saved to file."""
        # Generate summary
        summary = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        # Save to file
        output_path = Path(temp_dir) / "test_summary.md"
        saved_path = executive_summary_generator.save_summary(
            summary=summary,
            output_path=output_path,
            format='markdown'
        )
        
        # Verify file exists
        assert saved_path.exists(), "Summary file should exist"
        assert saved_path.suffix == '.md', "File should have .md extension"

    def test_file_format_correct(self, executive_summary_generator, sample_findings, temp_dir):
        """Test that file format is correct."""
        # Generate summary
        summary = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        # Save to file
        output_path = Path(temp_dir) / "test_summary.md"
        executive_summary_generator.save_summary(
            summary=summary,
            output_path=output_path,
            format='markdown'
        )
        
        # Verify file content
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert len(content) > 0, "File should not be empty"
        assert 'Executive Summary' in content or 'Executive' in content, \
            "File should contain Executive Summary content"

    def test_file_content_matches_summary(self, executive_summary_generator, sample_findings, temp_dir):
        """Test that file content matches generated summary."""
        # Generate summary
        summary = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='markdown'
        )
        
        # Save to file
        output_path = Path(temp_dir) / "test_summary.md"
        executive_summary_generator.save_summary(
            summary=summary,
            output_path=output_path,
            format='markdown'
        )
        
        # Verify file content matches summary markdown
        with open(output_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        assert file_content == summary['markdown'], "File content should match summary markdown"

    def test_save_json_format(self, executive_summary_generator, sample_findings, temp_dir):
        """Test that summary can be saved in JSON format."""
        # Generate summary
        summary = executive_summary_generator.generate_summary(
            findings=sample_findings,
            format='both'
        )
        
        # Save to JSON file
        output_path = Path(temp_dir) / "test_summary.json"
        saved_path = executive_summary_generator.save_summary(
            summary=summary,
            output_path=output_path,
            format='json'
        )
        
        # Verify JSON file exists
        assert saved_path.exists(), "JSON file should exist"
        assert saved_path.suffix == '.json', "File should have .json extension"
        
        # Verify JSON content is valid
        with open(saved_path, 'r', encoding='utf-8') as f:
            json_content = json.load(f)
        
        assert 'summary_id' in json_content, "JSON should contain 'summary_id'"
        assert 'ai_summary' in json_content, "JSON should contain 'ai_summary'"


class TestSummaryForDifferentHuntTypes:
    """TC-3-03-06: Summary for different hunt types"""

    def test_summary_for_high_confidence_hunt(self, executive_summary_generator):
        """Test summary generation for hunt with high confidence."""
        findings = [
            {
                'finding_id': 'T1059_001',
                'technique_id': 'T1059',
                'technique_name': 'Command and Scripting Interpreter',
                'severity': 'high',
                'confidence': 0.95,
                'title': 'High confidence finding',
                'description': 'High confidence threat detected'
            }
        ]
        
        result = executive_summary_generator.generate_summary(
            findings=findings,
            format='markdown'
        )
        
        assert 'summary_id' in result, "Result should contain 'summary_id'"
        assert result['findings_count'] == 1, "Should have 1 finding"
        assert 'ai_summary' in result, "Result should contain 'ai_summary'"

    def test_summary_for_low_confidence_hunt(self, executive_summary_generator):
        """Test summary generation for hunt with low confidence (false positives)."""
        findings = [
            {
                'finding_id': 'T1059_002',
                'technique_id': 'T1059',
                'technique_name': 'Command and Scripting Interpreter',
                'severity': 'low',
                'confidence': 0.3,
                'title': 'Low confidence finding',
                'description': 'Possible false positive'
            }
        ]
        
        result = executive_summary_generator.generate_summary(
            findings=findings,
            format='markdown'
        )
        
        assert 'summary_id' in result, "Result should contain 'summary_id'"
        assert result['findings_count'] == 1, "Should have 1 finding"
        assert 'ai_summary' in result, "Result should contain 'ai_summary'"
        
        # Check that statistics reflect low confidence
        statistics = result['statistics']
        assert statistics['low_severity_count'] == 1, "Should have 1 low severity finding"

    def test_summary_for_no_findings(self, executive_summary_generator):
        """Test summary generation for hunt with no findings."""
        findings = []
        
        result = executive_summary_generator.generate_summary(
            findings=findings,
            format='markdown'
        )
        
        assert 'summary_id' in result, "Result should contain 'summary_id'"
        assert result['findings_count'] == 0, "Should have 0 findings"
        assert 'ai_summary' in result, "Result should contain 'ai_summary'"
        assert 'statistics' in result, "Result should contain 'statistics'"
        
        # Check statistics for no findings
        statistics = result['statistics']
        assert statistics['total_findings'] == 0, "Should have 0 total findings"

    def test_different_hunt_types_generate_appropriate_summary(self, executive_summary_generator):
        """Test that different hunt types generate appropriate summaries."""
        # High confidence hunt
        high_confidence_findings = [
            {
                'finding_id': 'T1059_001',
                'technique_id': 'T1059',
                'technique_name': 'Command and Scripting Interpreter',
                'severity': 'high',
                'confidence': 0.95,
                'title': 'High confidence finding',
                'description': 'High confidence threat'
            }
        ]
        
        high_result = executive_summary_generator.generate_summary(
            findings=high_confidence_findings,
            format='markdown'
        )
        
        # Low confidence hunt
        low_confidence_findings = [
            {
                'finding_id': 'T1059_002',
                'technique_id': 'T1059',
                'technique_name': 'Command and Scripting Interpreter',
                'severity': 'low',
                'confidence': 0.3,
                'title': 'Low confidence finding',
                'description': 'Possible false positive'
            }
        ]
        
        low_result = executive_summary_generator.generate_summary(
            findings=low_confidence_findings,
            format='markdown'
        )
        
        # Both should generate summaries
        assert 'ai_summary' in high_result, "High confidence should generate summary"
        assert 'ai_summary' in low_result, "Low confidence should generate summary"
        
        # Statistics should differ
        assert high_result['statistics']['high_severity_count'] > low_result['statistics']['high_severity_count'], \
            "High confidence hunt should have more high severity findings"


class TestAggregateFindingsFromMultipleSources:
    """TC-3-03-07: Aggregate findings from multiple sources"""

    def test_aggregate_findings_from_different_hunts(self, executive_summary_generator):
        """Test aggregation of findings from different hunts."""
        findings = [
            {
                'finding_id': 'T1059_001',
                'playbook_id': 'T1059-command',
                'technique_id': 'T1059',
                'technique_name': 'Command and Scripting Interpreter',
                'severity': 'high',
                'confidence': 0.85,
                'title': 'Finding from T1059 hunt',
                'source': 'Microsoft Defender'
            },
            {
                'finding_id': 'T1047_001',
                'playbook_id': 'T1047-wmi',
                'technique_id': 'T1047',
                'technique_name': 'Windows Management Instrumentation',
                'severity': 'medium',
                'confidence': 0.7,
                'title': 'Finding from T1047 hunt',
                'source': 'Sentinel'
            },
            {
                'finding_id': 'T1071_001',
                'playbook_id': 'T1071-application-layer-protocol',
                'technique_id': 'T1071',
                'technique_name': 'Application Layer Protocol',
                'severity': 'high',
                'confidence': 0.9,
                'title': 'Finding from T1071 hunt',
                'source': 'Firewall'
            }
        ]
        
        result = executive_summary_generator.generate_summary(
            findings=findings,
            format='markdown'
        )
        
        # Check that all findings are aggregated
        assert result['findings_count'] == 3, "Should aggregate all 3 findings"
        statistics = result['statistics']
        assert statistics['total_findings'] == 3, "Should have 3 total findings"
        
        # Check technique distribution includes all hunts
        technique_distribution = statistics['technique_distribution']
        assert 'T1059' in technique_distribution, "Should include T1059"
        assert 'T1047' in technique_distribution, "Should include T1047"
        assert 'T1071' in technique_distribution, "Should include T1071"

    def test_aggregate_findings_from_different_tools(self, executive_summary_generator):
        """Test aggregation of findings from different tools."""
        findings = [
            {
                'finding_id': 'MDE_001',
                'technique_id': 'T1059',
                'technique_name': 'Command and Scripting Interpreter',
                'severity': 'high',
                'confidence': 0.85,
                'title': 'Finding from MDE',
                'source': 'Microsoft Defender'
            },
            {
                'finding_id': 'Sentinel_001',
                'technique_id': 'T1059',
                'technique_name': 'Command and Scripting Interpreter',
                'severity': 'high',
                'confidence': 0.8,
                'title': 'Finding from Sentinel',
                'source': 'Sentinel'
            }
        ]
        
        result = executive_summary_generator.generate_summary(
            findings=findings,
            format='markdown'
        )
        
        # Check that findings from both tools are aggregated
        assert result['findings_count'] == 2, "Should aggregate findings from both tools"
        statistics = result['statistics']
        assert statistics['total_findings'] == 2, "Should have 2 total findings"

    def test_summary_shows_differences_between_sources(self, executive_summary_generator):
        """Test that summary shows differences between sources."""
        findings = [
            {
                'finding_id': 'MDE_001',
                'technique_id': 'T1059',
                'technique_name': 'Command and Scripting Interpreter',
                'severity': 'high',
                'confidence': 0.85,
                'title': 'Finding from MDE',
                'source': 'Microsoft Defender'
            },
            {
                'finding_id': 'Sentinel_001',
                'technique_id': 'T1047',
                'technique_name': 'Windows Management Instrumentation',
                'severity': 'medium',
                'confidence': 0.7,
                'title': 'Finding from Sentinel',
                'source': 'Sentinel'
            }
        ]
        
        result = executive_summary_generator.generate_summary(
            findings=findings,
            format='markdown'
        )
        
        # Check that statistics show differences
        statistics = result['statistics']
        technique_distribution = statistics['technique_distribution']
        assert len(technique_distribution) == 2, "Should show 2 different techniques"
        assert 'T1059' in technique_distribution, "Should include T1059"
        assert 'T1047' in technique_distribution, "Should include T1047"
        
        # Check severity distribution shows differences
        severity_distribution = statistics['severity_distribution']
        assert 'high' in severity_distribution, "Should include high severity"
        assert 'medium' in severity_distribution, "Should include medium severity"


class TestGenerateSummaryForComplexHunt:
    """TS-3-03-01: Generate summary for complex hunt"""

    def test_complex_hunt_summary(self, executive_summary_generator):
        """Test summary generation for complex hunt with multiple findings."""
        # Create findings from multiple hunts
        findings = []
        for i, technique_id in enumerate(['T1059', 'T1047', 'T1071']):
            findings.append({
                'finding_id': f'{technique_id}_{i+1}',
                'playbook_id': f'{technique_id}-hunt',
                'technique_id': technique_id,
                'technique_name': f'Technique {technique_id}',
                'severity': 'high' if i % 2 == 0 else 'medium',
                'confidence': 0.7 + (i * 0.1),
                'title': f'Finding from {technique_id}',
                'description': f'Description for {technique_id}',
                'source': 'Microsoft Defender' if i % 2 == 0 else 'Sentinel'
            })
        
        result = executive_summary_generator.generate_summary(
            findings=findings,
            context={
                'time_range': '2025-01-15 to 2025-01-16',
                'playbooks_executed': ['T1059-hunt', 'T1047-hunt', 'T1071-hunt']
            },
            format='markdown'
        )
        
        # Check that summary contains all hunts
        assert result['findings_count'] == 3, "Should contain all 3 hunts"
        statistics = result['statistics']
        assert statistics['total_findings'] == 3, "Should have 3 total findings"
        
        # Check that recommendations are consistent
        ai_summary = result['ai_summary']
        assert 'recommendations' in ai_summary, "Should have recommendations"
        
        # Check that next steps are logical
        assert 'next_steps' in ai_summary, "Should have next steps"


class TestUpdateSummaryAfterNewFindings:
    """TS-3-03-02: Update summary after new findings"""

    def test_initial_summary_generated(self, executive_summary_generator):
        """Test that initial summary is generated."""
        initial_findings = [
            {
                'finding_id': 'T1059_001',
                'technique_id': 'T1059',
                'technique_name': 'Command and Scripting Interpreter',
                'severity': 'high',
                'confidence': 0.85,
                'title': 'Initial finding',
                'description': 'Initial finding description'
            }
        ]
        
        initial_result = executive_summary_generator.generate_summary(
            findings=initial_findings,
            format='markdown'
        )
        
        assert 'summary_id' in initial_result, "Initial summary should have summary_id"
        assert initial_result['findings_count'] == 1, "Initial summary should have 1 finding"

    def test_updated_summary_includes_new_findings(self, executive_summary_generator):
        """Test that updated summary includes new findings."""
        # Initial findings
        initial_findings = [
            {
                'finding_id': 'T1059_001',
                'technique_id': 'T1059',
                'technique_name': 'Command and Scripting Interpreter',
                'severity': 'high',
                'confidence': 0.85,
                'title': 'Initial finding',
                'description': 'Initial finding description'
            }
        ]
        
        # Generate initial summary
        initial_result = executive_summary_generator.generate_summary(
            findings=initial_findings,
            format='markdown'
        )
        
        # Add new findings
        new_findings = initial_findings + [
            {
                'finding_id': 'T1047_001',
                'technique_id': 'T1047',
                'technique_name': 'Windows Management Instrumentation',
                'severity': 'medium',
                'confidence': 0.7,
                'title': 'New finding',
                'description': 'New finding description'
            }
        ]
        
        # Generate updated summary
        updated_result = executive_summary_generator.generate_summary(
            findings=new_findings,
            format='markdown'
        )
        
        # Check that new findings are included
        assert updated_result['findings_count'] == 2, "Updated summary should have 2 findings"
        assert updated_result['findings_count'] > initial_result['findings_count'], \
            "Updated summary should have more findings than initial"
        
        # Check that statistics are updated
        updated_statistics = updated_result['statistics']
        assert updated_statistics['total_findings'] == 2, "Should have 2 total findings"

    def test_recommendations_updated(self, executive_summary_generator):
        """Test that recommendations are updated after new findings."""
        # Initial findings
        initial_findings = [
            {
                'finding_id': 'T1059_001',
                'technique_id': 'T1059',
                'technique_name': 'Command and Scripting Interpreter',
                'severity': 'high',
                'confidence': 0.85,
                'title': 'Initial finding',
                'description': 'Initial finding description'
            }
        ]
        
        # Generate initial summary
        initial_result = executive_summary_generator.generate_summary(
            findings=initial_findings,
            format='markdown'
        )
        
        # Add new findings
        new_findings = initial_findings + [
            {
                'finding_id': 'T1047_001',
                'technique_id': 'T1047',
                'technique_name': 'Windows Management Instrumentation',
                'severity': 'medium',
                'confidence': 0.7,
                'title': 'New finding',
                'description': 'New finding description'
            }
        ]
        
        # Generate updated summary
        updated_result = executive_summary_generator.generate_summary(
            findings=new_findings,
            format='markdown'
        )
        
        # Check that recommendations are present in both
        assert 'recommendations' in initial_result['ai_summary'], "Initial should have recommendations"
        assert 'recommendations' in updated_result['ai_summary'], "Updated should have recommendations"
        
        # Both should have recommendations (may differ based on findings)
        initial_recommendations = initial_result['ai_summary']['recommendations']
        updated_recommendations = updated_result['ai_summary']['recommendations']
        assert 'immediate_actions' in initial_recommendations, "Initial should have immediate_actions"
        assert 'immediate_actions' in updated_recommendations, "Updated should have immediate_actions"

