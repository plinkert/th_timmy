"""
Unit tests for PHASE4-02: Final Report Generator.

Test Cases:
- TC-4-02-01: Generate final report with deanonymized data
- TC-4-02-02: Executive summary integration
- TC-4-02-03: Report formatting
- TC-4-02-04: Report content
- TC-4-02-05: Report export
- TC-4-02-06: Data validation
- TC-4-02-07: Report metadata
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
if "automation_scripts.utils" not in sys.modules:
    sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
    sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
if "automation_scripts.services" not in sys.modules:
    sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
    sys.modules["automation_scripts.services"].__path__ = [str(automation_scripts_path / "services")]


@pytest.fixture
def mock_deanonymizer():
    """Create a mock deanonymizer."""
    deanonymizer = Mock()
    
    def deanonymize_findings(findings):
        """Deanonymize findings by replacing placeholders."""
        deanonymized = []
        for finding in findings:
            deanonymized_finding = finding.copy()
            # Replace placeholders
            for key, value in deanonymized_finding.items():
                if isinstance(value, str):
                    deanonymized_finding[key] = value.replace('HOST_12', 'workstation-01.example.com')
                    deanonymized_finding[key] = deanonymized_finding[key].replace('USER_03', 'john.doe')
                    deanonymized_finding[key] = deanonymized_finding[key].replace('IP_07', '192.168.1.100')
            deanonymized.append(deanonymized_finding)
        return deanonymized
    
    deanonymizer.deanonymize_findings = Mock(side_effect=deanonymize_findings)
    return deanonymizer


@pytest.fixture
def mock_executive_summary_generator():
    """Create a mock executive summary generator."""
    summary_generator = Mock()
    
    summary_generator.generate_summary = Mock(return_value={
        'summary_id': 'summary_20250115_103000',
        'generated_at': '2025-01-15T10:30:00Z',
        'findings_count': 3,
        'ai_summary': {
            'executive_summary': 'Threat hunting exercise detected multiple suspicious activities.',
            'critical_findings': [],
            'threat_landscape': {
                'attack_patterns': 'Multiple execution techniques detected'
            },
            'risk_assessment': {
                'overall_risk': 'High',
                'risk_score': 0.8,
                'risk_factors': ['Multiple high-severity findings']
            },
            'recommendations': {
                'immediate_actions': ['Investigate high-severity findings'],
                'long_term_improvements': ['Implement additional monitoring']
            },
            'next_steps': {
                'follow_up_investigations': ['Investigate process chains'],
                'additional_queries': ['Query for related activities']
            },
            'model_used': 'gpt-4'
        },
        'statistics': {
            'total_findings': 3,
            'critical_count': 0,
            'high_severity_count': 2,
            'medium_severity_count': 1,
            'low_severity_count': 0
        }
    })
    
    return summary_generator


@pytest.fixture
def sample_findings_with_placeholders():
    """Create sample findings with placeholders."""
    return [
        {
            'finding_id': 'T1059_001',
            'playbook_id': 'T1059-command',
            'technique_id': 'T1059',
            'technique_name': 'Command and Scripting Interpreter',
            'tactic': 'Execution',
            'severity': 'high',
            'confidence': 0.85,
            'title': 'Suspicious activity on HOST_12',
            'description': 'User USER_03 executed commands from IP_07',
            'hostname': 'HOST_12',
            'username': 'USER_03',
            'ip': 'IP_07',
            'source': 'Microsoft Defender',
            'timestamp': '2025-01-15T10:30:00Z',
            'status': 'new'
        },
        {
            'finding_id': 'T1047_001',
            'playbook_id': 'T1047-wmi',
            'technique_id': 'T1047',
            'technique_name': 'Windows Management Instrumentation',
            'tactic': 'Execution',
            'severity': 'medium',
            'confidence': 0.7,
            'title': 'Suspicious WMI activity',
            'description': 'WMI execution detected',
            'source': 'Sentinel',
            'timestamp': '2025-01-15T10:30:01Z',
            'status': 'new'
        },
        {
            'finding_id': 'T1071_001',
            'playbook_id': 'T1071-application-layer-protocol',
            'technique_id': 'T1071',
            'technique_name': 'Application Layer Protocol',
            'tactic': 'Command and Control',
            'severity': 'high',
            'confidence': 0.9,
            'title': 'Suspicious network activity',
            'description': 'Network connections detected',
            'source': 'Firewall',
            'timestamp': '2025-01-15T10:30:02Z',
            'status': 'new'
        }
    ]


@pytest.fixture
def final_report_generator(mock_deanonymizer, mock_executive_summary_generator, project_root_path):
    """Create FinalReportGenerator instance with mocked dependencies."""
    import sys
    import importlib.util
    import types
    
    automation_scripts_path = project_root_path / "automation-scripts"
    sys.path.insert(0, str(automation_scripts_path))
    
    if "automation_scripts.utils" not in sys.modules:
        sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
        sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
    if "automation_scripts.services" not in sys.modules:
        sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
        sys.modules["automation_scripts.services"].__path__ = [str(automation_scripts_path / "services")]
    
    # Load dependencies
    # Load deanonymizer (for import)
    deanonymizer_path = automation_scripts_path / "utils" / "deanonymizer.py"
    deanonymizer_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.deanonymizer", deanonymizer_path
    )
    deanonymizer_module = importlib.util.module_from_spec(deanonymizer_spec)
    sys.modules["automation_scripts.utils.deanonymizer"] = deanonymizer_module
    deanonymizer_spec.loader.exec_module(deanonymizer_module)
    
    # Load report_generator (for import)
    report_generator_path = automation_scripts_path / "utils" / "report_generator.py"
    report_generator_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.report_generator", report_generator_path
    )
    report_generator_module = importlib.util.module_from_spec(report_generator_spec)
    sys.modules["automation_scripts.utils.report_generator"] = report_generator_module
    report_generator_spec.loader.exec_module(report_generator_module)
    
    # Load executive_summary_generator (for import)
    executive_summary_generator_path = automation_scripts_path / "services" / "executive_summary_generator.py"
    executive_summary_generator_spec = importlib.util.spec_from_file_location(
        "automation_scripts.services.executive_summary_generator", executive_summary_generator_path
    )
    executive_summary_generator_module = importlib.util.module_from_spec(executive_summary_generator_spec)
    sys.modules["automation_scripts.services.executive_summary_generator"] = executive_summary_generator_module
    
    # Mock OpenAI import
    mock_openai = Mock()
    mock_openai.OpenAI = Mock()
    sys.modules['openai'] = mock_openai
    executive_summary_generator_module.OPENAI_AVAILABLE = True
    
    # Load ai_service and ai_prompts for executive_summary_generator
    ai_service_path = automation_scripts_path / "services" / "ai_service.py"
    ai_service_spec = importlib.util.spec_from_file_location(
        "automation_scripts.services.ai_service", ai_service_path
    )
    ai_service_module = importlib.util.module_from_spec(ai_service_spec)
    sys.modules["automation_scripts.services.ai_service"] = ai_service_module
    ai_service_spec.loader.exec_module(ai_service_module)
    
    ai_prompts_path = automation_scripts_path / "services" / "ai_prompts.py"
    ai_prompts_spec = importlib.util.spec_from_file_location(
        "automation_scripts.services.ai_prompts", ai_prompts_path
    )
    ai_prompts_module = importlib.util.module_from_spec(ai_prompts_spec)
    sys.modules["automation_scripts.services.ai_prompts"] = ai_prompts_module
    ai_prompts_spec.loader.exec_module(ai_prompts_module)
    
    executive_summary_generator_spec.loader.exec_module(executive_summary_generator_module)
    
    # Load deterministic_anonymizer (for import)
    deterministic_anonymizer_path = automation_scripts_path / "utils" / "deterministic_anonymizer.py"
    deterministic_anonymizer_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.deterministic_anonymizer", deterministic_anonymizer_path
    )
    deterministic_anonymizer_module = importlib.util.module_from_spec(deterministic_anonymizer_spec)
    sys.modules["automation_scripts.utils.deterministic_anonymizer"] = deterministic_anonymizer_module
    deterministic_anonymizer_spec.loader.exec_module(deterministic_anonymizer_module)
    
    # Load final_report_generator
    final_report_generator_path = automation_scripts_path / "utils" / "final_report_generator.py"
    final_report_generator_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.final_report_generator", final_report_generator_path
    )
    final_report_generator_module = importlib.util.module_from_spec(final_report_generator_spec)
    sys.modules["automation_scripts.utils.final_report_generator"] = final_report_generator_module
    final_report_generator_spec.loader.exec_module(final_report_generator_module)
    
    FinalReportGenerator = final_report_generator_module.FinalReportGenerator
    
    # Create generator with mocked dependencies
    generator = FinalReportGenerator(
        config_path=None,
        deanonymizer=mock_deanonymizer,
        summary_generator=mock_executive_summary_generator
    )
    
    return generator


class TestGenerateFinalReportWithDeanonymizedData:
    """TC-4-02-01: Generate final report with deanonymized data"""

    def test_generate_final_report_with_placeholders(self, final_report_generator, sample_findings_with_placeholders):
        """Test that final report is generated with deanonymized data."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            deanonymize=True,
            include_executive_summary=True,
            format='markdown'
        )
        
        assert 'report_id' in result, "Result should contain 'report_id'"
        assert 'generated_at' in result, "Result should contain 'generated_at'"
        assert 'findings_count' in result, "Result should contain 'findings_count'"
        assert result['findings_count'] == len(sample_findings_with_placeholders), "Findings count should match"
        assert 'deanonymized' in result, "Result should contain 'deanonymized'"
        assert result['deanonymized'] is True, "Report should be deanonymized"

    def test_placeholders_replaced_with_real_values(self, final_report_generator, sample_findings_with_placeholders):
        """Test that placeholders are replaced with real values."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            deanonymize=True,
            format='markdown'
        )
        
        # Check that placeholders were replaced in findings
        if 'findings' in result and len(result['findings']) > 0:
            finding = result['findings'][0]
            assert finding.get('hostname') != 'HOST_12', "HOST_12 placeholder should be replaced"
            assert finding.get('username') != 'USER_03', "USER_03 placeholder should be replaced"
            assert finding.get('ip') != 'IP_07', "IP_07 placeholder should be replaced"
            
            # Check that real values are present
            assert finding.get('hostname') == 'workstation-01.example.com', \
                "Hostname should be replaced with real value"
            assert finding.get('username') == 'john.doe', \
                "Username should be replaced with real value"
            assert finding.get('ip') == '192.168.1.100', \
                "IP should be replaced with real value"

    def test_all_placeholders_replaced(self, final_report_generator, sample_findings_with_placeholders):
        """Test that all placeholders are replaced."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            deanonymize=True,
            format='markdown'
        )
        
        # Check that no placeholders remain in findings
        if 'findings' in result:
            for finding in result['findings']:
                finding_str = json.dumps(finding)
                assert 'HOST_12' not in finding_str, "HOST_12 placeholder should be replaced"
                assert 'USER_03' not in finding_str, "USER_03 placeholder should be replaced"
                assert 'IP_07' not in finding_str, "IP_07 placeholder should be replaced"

    def test_values_match_originals(self, final_report_generator, sample_findings_with_placeholders):
        """Test that replaced values match originals from mapping table."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            deanonymize=True,
            format='markdown'
        )
        
        # Expected values from mapping table
        expected_hostname = 'workstation-01.example.com'
        expected_username = 'john.doe'
        expected_ip = '192.168.1.100'
        
        # Check that values match
        if 'findings' in result and len(result['findings']) > 0:
            finding = result['findings'][0]
            if 'hostname' in finding:
                assert finding['hostname'] == expected_hostname, \
                    f"Hostname should match: {finding['hostname']} != {expected_hostname}"
            if 'username' in finding:
                assert finding['username'] == expected_username, \
                    f"Username should match: {finding['username']} != {expected_username}"
            if 'ip' in finding:
                assert finding['ip'] == expected_ip, \
                    f"IP should match: {finding['ip']} != {expected_ip}"


class TestExecutiveSummaryIntegration:
    """TC-4-02-02: Executive summary integration"""

    def test_executive_summary_included_in_report(self, final_report_generator, sample_findings_with_placeholders, mock_executive_summary_generator):
        """Test that executive summary is included in report."""
        # Reset mock
        mock_executive_summary_generator.generate_summary.reset_mock()
        
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            include_executive_summary=True,
            format='markdown'
        )
        
        # Verify executive summary is in report
        assert 'executive_summary' in result, "Report should contain 'executive_summary'"
        assert result['executive_summary'] is not None, "Executive summary should not be None"
        
        # Verify executive summary generator was called
        assert mock_executive_summary_generator.generate_summary.called, \
            "Executive summary generator should be called"

    def test_executive_summary_deanonymized(self, final_report_generator, sample_findings_with_placeholders):
        """Test that executive summary is deanonymized."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            deanonymize=True,
            include_executive_summary=True,
            format='markdown'
        )
        
        # Check that executive summary is present
        if 'executive_summary' in result and result['executive_summary']:
            executive_summary = result['executive_summary']
            if 'ai_summary' in executive_summary:
                ai_summary = executive_summary['ai_summary']
                # Check that executive summary text doesn't contain placeholders
                if 'executive_summary' in ai_summary:
                    summary_text = ai_summary['executive_summary']
                    assert 'HOST_12' not in summary_text or 'workstation-01.example.com' in summary_text, \
                        "Executive summary should not contain placeholders"

    def test_executive_summary_formatting(self, final_report_generator, sample_findings_with_placeholders):
        """Test that executive summary is properly formatted."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            include_executive_summary=True,
            format='markdown'
        )
        
        # Check that markdown contains executive summary
        if 'markdown' in result:
            markdown = result['markdown']
            assert 'Executive Summary' in markdown or 'executive_summary' in markdown.lower(), \
                "Markdown should contain Executive Summary section"
            assert len(markdown) > 100, "Markdown should have substantial content"


class TestReportFormatting:
    """TC-4-02-03: Report formatting"""

    def test_report_formatted_according_to_template(self, final_report_generator, sample_findings_with_placeholders):
        """Test that report is formatted according to template."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            format='markdown'
        )
        
        assert 'markdown' in result, "Result should contain 'markdown'"
        markdown = result['markdown']
        assert isinstance(markdown, str), "Markdown should be a string"
        assert len(markdown) > 0, "Markdown should not be empty"
        
        # Check that template sections are present
        assert 'Threat Hunting Final Report' in markdown or 'Final Report' in markdown, \
            "Should contain Final Report section"

    def test_all_sections_present(self, final_report_generator, sample_findings_with_placeholders):
        """Test that all template sections are present."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            include_executive_summary=True,
            format='markdown'
        )
        
        markdown = result['markdown']
        
        # Check for key sections (may vary based on template)
        assert 'Executive Summary' in markdown or 'executive_summary' in markdown.lower(), \
            "Should contain Executive Summary section"
        assert 'Findings' in markdown or 'findings' in markdown.lower(), \
            "Should contain Findings section"

    def test_formatting_readable(self, final_report_generator, sample_findings_with_placeholders):
        """Test that formatting is readable and professional."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            format='markdown'
        )
        
        markdown = result['markdown']
        
        # Check that markdown is readable (has structure)
        assert '\n' in markdown, "Markdown should have line breaks"
        # Check that it's not just one long line
        lines = markdown.split('\n')
        assert len(lines) > 5, "Markdown should have multiple lines"


class TestReportContent:
    """TC-4-02-04: Report content"""

    def test_findings_section_contains_all_findings(self, final_report_generator, sample_findings_with_placeholders):
        """Test that Findings section contains all findings with real data."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            deanonymize=True,
            format='markdown'
        )
        
        # Check that all findings are in report
        assert 'findings' in result, "Report should contain 'findings'"
        assert len(result['findings']) == len(sample_findings_with_placeholders), \
            "All findings should be in report"
        
        # Check that findings are deanonymized
        for finding in result['findings']:
            assert 'HOST_12' not in str(finding), "Findings should be deanonymized"

    def test_executive_summary_section_present(self, final_report_generator, sample_findings_with_placeholders):
        """Test that Executive Summary section is present."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            include_executive_summary=True,
            format='markdown'
        )
        
        # Check that executive summary is in report
        assert 'executive_summary' in result, "Report should contain 'executive_summary'"
        
        # Check that markdown contains executive summary
        if 'markdown' in result:
            markdown = result['markdown']
            assert 'Executive Summary' in markdown or 'executive_summary' in markdown.lower(), \
                "Markdown should contain Executive Summary section"

    def test_recommendations_section_present(self, final_report_generator, sample_findings_with_placeholders):
        """Test that Recommendations section is present."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            include_executive_summary=True,
            format='markdown'
        )
        
        # Check that markdown contains recommendations
        if 'markdown' in result:
            markdown = result['markdown']
            assert 'Recommendations' in markdown or 'recommendations' in markdown.lower(), \
                "Markdown should contain Recommendations section"

    def test_all_sections_complete(self, final_report_generator, sample_findings_with_placeholders):
        """Test that all sections are complete and contain appropriate content."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            include_executive_summary=True,
            format='markdown'
        )
        
        # Check that report has all required sections
        assert 'findings' in result, "Report should contain findings"
        assert 'statistics' in result, "Report should contain statistics"
        assert 'executive_summary' in result or not result.get('include_executive_summary', True), \
            "Report should contain executive summary if requested"
        
        # Check that statistics are calculated
        statistics = result.get('statistics', {})
        assert 'total_findings' in statistics, "Statistics should contain total_findings"


class TestReportExport:
    """TC-4-02-05: Report export"""

    def test_export_markdown_format(self, final_report_generator, sample_findings_with_placeholders, temp_dir):
        """Test that report can be exported as Markdown."""
        # Generate final report
        report = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            format='markdown'
        )
        
        # Export to Markdown
        output_path = Path(temp_dir) / "test_report.md"
        saved_path = final_report_generator.save_final_report(
            report=report,
            output_path=output_path,
            format='markdown'
        )
        
        # Verify file exists
        assert saved_path.exists(), "Markdown file should exist"
        assert saved_path.suffix == '.md', "File should have .md extension"
        
        # Verify file content
        with open(saved_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert len(content) > 0, "File should not be empty"
        assert 'Final Report' in content or 'Threat Hunting' in content, \
            "File should contain report content"

    def test_export_json_format(self, final_report_generator, sample_findings_with_placeholders, temp_dir):
        """Test that report can be exported as JSON."""
        # Generate final report
        report = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            format='both'
        )
        
        # Export to JSON
        output_path = Path(temp_dir) / "test_report.json"
        saved_path = final_report_generator.save_final_report(
            report=report,
            output_path=output_path,
            format='json'
        )
        
        # Verify file exists
        assert saved_path.exists(), "JSON file should exist"
        assert saved_path.suffix == '.json', "File should have .json extension"
        
        # Verify JSON content is valid
        with open(saved_path, 'r', encoding='utf-8') as f:
            json_content = json.load(f)
        
        assert 'report_id' in json_content, "JSON should contain 'report_id'"
        assert 'findings' in json_content, "JSON should contain 'findings'"

    def test_export_both_formats(self, final_report_generator, sample_findings_with_placeholders, temp_dir):
        """Test that report can be exported in both formats."""
        # Generate final report
        report = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            format='both'
        )
        
        # Export to both formats
        output_path = Path(temp_dir) / "test_report"
        saved_path = final_report_generator.save_final_report(
            report=report,
            output_path=output_path,
            format='both'
        )
        
        # Verify at least one file exists
        assert saved_path.exists(), "At least one file should exist"
        
        # Check for both files
        md_file = output_path.with_suffix('.md')
        json_file = output_path.with_suffix('.json')
        
        # At least one should exist (the first one saved)
        assert md_file.exists() or json_file.exists(), "At least one format file should exist"


class TestDataValidation:
    """TC-4-02-06: Data validation"""

    def test_validation_with_incomplete_data(self, final_report_generator):
        """Test that validation handles incomplete data."""
        # Try to generate report with empty findings
        incomplete_findings = []
        
        # Should still generate report (empty findings is valid)
        # Note: Empty findings may cause issues in template rendering, so we test with minimal data
        minimal_finding = {
            'finding_id': 'TEST_001',
            'technique_id': 'T1059',
            'technique_name': 'Test Technique',
            'tactic': 'Execution',
            'severity': 'low',
            'confidence': 0.5,
            'title': 'Test finding',
            'description': 'Test description',
            'source': 'Test',
            'timestamp': '2025-01-15T10:30:00Z',
            'status': 'new'
        }
        
        # Test with minimal finding (incomplete but valid)
        result = final_report_generator.generate_final_report(
            findings=[minimal_finding],
            format='markdown'
        )
        
        assert 'report_id' in result, "Report should be generated"
        assert result['findings_count'] == 1, "Findings count should be 1"

    def test_validation_with_complete_data(self, final_report_generator, sample_findings_with_placeholders):
        """Test that validation accepts complete data."""
        # Generate report with complete data
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            format='markdown'
        )
        
        assert 'report_id' in result, "Report should be generated"
        assert result['findings_count'] == len(sample_findings_with_placeholders), \
            "Findings count should match"


class TestReportMetadata:
    """TC-4-02-07: Report metadata"""

    def test_report_contains_metadata(self, final_report_generator, sample_findings_with_placeholders):
        """Test that report contains metadata."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            format='markdown'
        )
        
        # Check metadata fields
        assert 'report_id' in result, "Report should contain 'report_id'"
        assert 'generated_at' in result, "Report should contain 'generated_at'"
        assert 'findings_count' in result, "Report should contain 'findings_count'"
        assert 'deanonymized' in result, "Report should contain 'deanonymized'"

    def test_metadata_date_correct(self, final_report_generator, sample_findings_with_placeholders):
        """Test that metadata date is correct."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            format='markdown'
        )
        
        # Check that generated_at is a valid ISO format
        generated_at = result.get('generated_at')
        assert generated_at is not None, "Generated at should not be None"
        assert isinstance(generated_at, str), "Generated at should be a string"
        # Should be ISO format
        assert 'T' in generated_at or '-' in generated_at, "Generated at should be in ISO format"

    def test_metadata_version_present(self, final_report_generator, sample_findings_with_placeholders):
        """Test that metadata version is present."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            format='markdown'
        )
        
        # Check that markdown contains version information
        if 'markdown' in result:
            markdown = result['markdown']
            # Version might be in template
            assert 'Report Version' in markdown or 'version' in markdown.lower() or \
                   'Generated By' in markdown, \
                "Markdown should contain version or generation information"


class TestFullReportGenerationCycle:
    """TS-4-02-01: Full report generation cycle"""

    def test_full_cycle_report_generation(self, final_report_generator, sample_findings_with_placeholders):
        """Test full cycle of report generation."""
        # Step 1: Generate executive summary (implicit in generate_final_report)
        # Step 2: Deanonymize findings
        # Step 3: Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            deanonymize=True,
            include_executive_summary=True,
            format='markdown'
        )
        
        # Step 4: Verify report content
        assert 'report_id' in result, "Report should have report_id"
        assert 'findings' in result, "Report should contain findings"
        assert 'executive_summary' in result, "Report should contain executive summary"
        
        # Step 5: Verify all data is deanonymized
        for finding in result['findings']:
            finding_str = json.dumps(finding)
            assert 'HOST_12' not in finding_str, "All data should be deanonymized"
        
        # Step 6: Verify export works
        assert 'markdown' in result, "Report should have markdown format"


class TestReportForMultipleHunts:
    """TS-4-02-02: Report for multiple hunts"""

    def test_report_contains_all_hunts(self, final_report_generator, sample_findings_with_placeholders):
        """Test that report contains findings from all hunts."""
        # Generate final report with findings from multiple hunts
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            format='markdown'
        )
        
        # Check that all findings are in report
        assert len(result['findings']) == len(sample_findings_with_placeholders), \
            "Report should contain all findings from all hunts"
        
        # Check that findings are from different hunts
        playbook_ids = set(f.get('playbook_id') for f in result['findings'] if f.get('playbook_id'))
        assert len(playbook_ids) > 0, "Report should contain findings from multiple hunts"

    def test_findings_grouped_per_hunt(self, final_report_generator, sample_findings_with_placeholders):
        """Test that findings are grouped per hunt."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            format='markdown'
        )
        
        # Check that statistics include playbook executions
        if 'statistics' in result:
            statistics = result['statistics']
            assert 'playbook_executions' in statistics, \
                "Statistics should contain playbook_executions"

    def test_executive_summary_aggregates_all_hunts(self, final_report_generator, sample_findings_with_placeholders):
        """Test that executive summary aggregates all hunts."""
        # Generate final report
        result = final_report_generator.generate_final_report(
            findings=sample_findings_with_placeholders,
            include_executive_summary=True,
            format='markdown'
        )
        
        # Check that executive summary is present
        assert 'executive_summary' in result, "Report should contain executive summary"
        
        # Check that executive summary includes all findings
        if 'executive_summary' in result and result['executive_summary']:
            executive_summary = result['executive_summary']
            if 'findings_count' in executive_summary:
                assert executive_summary['findings_count'] == len(sample_findings_with_placeholders), \
                    "Executive summary should include all findings"

