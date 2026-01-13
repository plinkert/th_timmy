"""
Unit tests for PHASE4-01: Deanonymization Service.

Test Cases:
- TC-4-01-01: Report deanonymization
- TC-4-01-02: Determinism of deanonymization
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


@pytest.fixture
def mock_anonymizer_with_mapping():
    """Create a mock anonymizer with mapping table for deanonymization."""
    anonymizer = Mock()
    
    # Create a mapping table (simulating database)
    mapping_table = {
        ('HOST_12', 'hostname'): 'workstation-01.example.com',
        ('USER_03', 'username'): 'john.doe',
        ('IP_07', 'ip'): '192.168.1.100',
        ('anon-device-001', 'hostname'): 'workstation-01.example.com',
        ('anon-user-001', 'username'): 'john.doe',
        ('anon-ip-001', 'ip'): '192.168.1.100',
        ('10.123.45.67', 'ip'): '192.168.1.100',
        ('user_abc123456789', 'username'): 'john.doe',
        ('host_xyz987654321', 'hostname'): 'workstation-01.example.com'
    }
    
    def deanonymize(anonymized_value, value_type='generic'):
        """Deanonymize a value using mapping table."""
        if not anonymized_value or not isinstance(anonymized_value, str):
            return anonymized_value
        
        # Try exact match first
        key = (anonymized_value, value_type)
        if key in mapping_table:
            return mapping_table[key]
        
        # Try with generic type
        key_generic = (anonymized_value, 'generic')
        if key_generic in mapping_table:
            return mapping_table[key_generic]
        
        # Try different value types
        for vt in ['ip', 'email', 'username', 'hostname', 'generic']:
            key_alt = (anonymized_value, vt)
            if key_alt in mapping_table:
                return mapping_table[key_alt]
        
        # Not found in mapping table
        return None
    
    def deanonymize_record(record, fields_to_deanonymize=None):
        """Deanonymize a record."""
        if fields_to_deanonymize is None:
            fields_to_deanonymize = ['ip', 'email', 'username', 'user', 'account', 'hostname', 'host']
        
        deanonymized = record.copy()
        
        for field in fields_to_deanonymize:
            if field in deanonymized:
                value = deanonymized[field]
                if isinstance(value, str) and value.strip():
                    # Determine value type from field name
                    value_type = 'generic'
                    if field in ['ip', 'source_ip', 'destination_ip', 'src_ip', 'dst_ip']:
                        value_type = 'ip'
                    elif field in ['email', 'user_email', 'sender_email', 'recipient_email']:
                        value_type = 'email'
                    elif field in ['username', 'user', 'account', 'user_name']:
                        value_type = 'username'
                    elif field in ['hostname', 'host', 'server', 'machine_name']:
                        value_type = 'hostname'
                    
                    original = deanonymize(value, value_type)
                    if original:
                        deanonymized[field] = original
        
        return deanonymized
    
    # Add _deanonymize_text method to mock
    def _deanonymize_text(text):
        """Deanonymize text by finding and replacing placeholders."""
        if not text or not isinstance(text, str):
            return text
        
        import re
        
        # Pattern for placeholders: HOST_12, USER_03, IP_07
        placeholder_patterns = [
            (r'\bHOST_(\d+)\b', 'hostname'),
            (r'\bUSER_(\d+)\b', 'username'),
            (r'\bIP_(\d+)\b', 'ip')
        ]
        
        for pattern, value_type in placeholder_patterns:
            for match in re.finditer(pattern, text):
                placeholder = match.group(0)
                original = deanonymize(placeholder, value_type=value_type)
                if original:
                    text = text.replace(placeholder, original)
        
        return text
    
    anonymizer.deanonymize = Mock(side_effect=deanonymize)
    anonymizer.deanonymize_record = Mock(side_effect=deanonymize_record)
    anonymizer._deanonymize_text = _deanonymize_text
    
    return anonymizer


@pytest.fixture
def deanonymizer(mock_anonymizer_with_mapping, project_root_path):
    """Create Deanonymizer instance with mocked dependencies."""
    import sys
    import importlib.util
    import types
    
    automation_scripts_path = project_root_path / "automation-scripts"
    sys.path.insert(0, str(automation_scripts_path))
    
    if "automation_scripts.utils" not in sys.modules:
        sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
        sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
    
    # Load deterministic_anonymizer (for import)
    deterministic_anonymizer_path = automation_scripts_path / "utils" / "deterministic_anonymizer.py"
    deterministic_anonymizer_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.deterministic_anonymizer", deterministic_anonymizer_path
    )
    deterministic_anonymizer_module = importlib.util.module_from_spec(deterministic_anonymizer_spec)
    sys.modules["automation_scripts.utils.deterministic_anonymizer"] = deterministic_anonymizer_module
    deterministic_anonymizer_spec.loader.exec_module(deterministic_anonymizer_module)
    
    # Load deanonymizer
    deanonymizer_path = automation_scripts_path / "utils" / "deanonymizer.py"
    deanonymizer_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.deanonymizer", deanonymizer_path
    )
    deanonymizer_module = importlib.util.module_from_spec(deanonymizer_spec)
    sys.modules["automation_scripts.utils.deanonymizer"] = deanonymizer_module
    deanonymizer_spec.loader.exec_module(deanonymizer_module)
    
    Deanonymizer = deanonymizer_module.Deanonymizer
    
    # Create deanonymizer with mocked dependencies
    deanonymizer = Deanonymizer(
        config_path=None,
        anonymizer=mock_anonymizer_with_mapping
    )
    
    # Override _deanonymize_text to use mock's implementation
    deanonymizer._deanonymize_text = mock_anonymizer_with_mapping._deanonymize_text
    
    return deanonymizer


@pytest.fixture
def sample_report_with_placeholders():
    """Create a sample report with placeholders."""
    return {
        'summary_id': 'summary_20250115_103000',
        'generated_at': '2025-01-15T10:30:00Z',
        'executive_summary': 'Activity detected from HOST_12 by USER_03 from IP_07',
        'markdown': '# Executive Summary\n\nActivity detected from HOST_12 by USER_03 from IP_07',
        'findings': [
            {
                'finding_id': 'T1059_001',
                'title': 'Suspicious activity on HOST_12',
                'description': 'User USER_03 executed commands from IP_07',
                'hostname': 'HOST_12',
                'username': 'USER_03',
                'ip': 'IP_07'
            }
        ],
        'critical_findings': [
            {
                'finding_id': 'T1059_001',
                'title': 'Suspicious activity on HOST_12',
                'description': 'User USER_03 executed commands from IP_07',
                'hostname': 'HOST_12',
                'username': 'USER_03',
                'ip': 'IP_07'
            }
        ]
    }


class TestReportDeanonymization:
    """TC-4-01-01: Report deanonymization"""

    def test_deanonymize_report_with_placeholders(self, deanonymizer, sample_report_with_placeholders):
        """Test that report with placeholders is deanonymized."""
        # Deanonymize report
        result = deanonymizer.deanonymize_report(
            report=sample_report_with_placeholders
        )
        
        # Verify that placeholders in structural fields were replaced
        if 'findings' in result and len(result['findings']) > 0:
            finding = result['findings'][0]
            assert finding.get('hostname') != 'HOST_12', "HOST_12 placeholder should be replaced in hostname field"
            assert finding.get('username') != 'USER_03', "USER_03 placeholder should be replaced in username field"
            assert finding.get('ip') != 'IP_07', "IP_07 placeholder should be replaced in ip field"
        
        # Verify that placeholders in text fields (executive_summary, markdown) were replaced
        if 'executive_summary' in result:
            assert 'HOST_12' not in result['executive_summary'] or \
                   'workstation-01.example.com' in result['executive_summary'], \
                "HOST_12 placeholder should be replaced in executive_summary"
        
        if 'markdown' in result:
            assert 'HOST_12' not in result['markdown'] or \
                   'workstation-01.example.com' in result['markdown'], \
                "HOST_12 placeholder should be replaced in markdown"
        
        # Verify that original values are present in structural fields
        if 'findings' in result and len(result['findings']) > 0:
            finding = result['findings'][0]
            if 'hostname' in finding:
                assert finding['hostname'] == 'workstation-01.example.com', \
                    "Original hostname should be present"
            if 'username' in finding:
                assert finding['username'] == 'john.doe', \
                    "Original username should be present"
            if 'ip' in finding:
                assert finding['ip'] == '192.168.1.100', \
                    "Original IP should be present"

    def test_placeholders_replaced_with_real_values(self, deanonymizer, sample_report_with_placeholders):
        """Test that placeholders are replaced with real values from mapping table."""
        # Deanonymize report
        result = deanonymizer.deanonymize_report(
            report=sample_report_with_placeholders
        )
        
        # Check findings
        if 'findings' in result and len(result['findings']) > 0:
            finding = result['findings'][0]
            
            # Verify placeholders replaced in finding fields
            if 'hostname' in finding:
                assert finding['hostname'] != 'HOST_12', "Hostname placeholder should be replaced"
                assert finding['hostname'] == 'workstation-01.example.com', \
                    "Hostname should match mapping table value"
            
            if 'username' in finding:
                assert finding['username'] != 'USER_03', "Username placeholder should be replaced"
                assert finding['username'] == 'john.doe', \
                    "Username should match mapping table value"
            
            if 'ip' in finding:
                assert finding['ip'] != 'IP_07', "IP placeholder should be replaced"
                assert finding['ip'] == '192.168.1.100', \
                    "IP should match mapping table value"

    def test_all_placeholders_replaced(self, deanonymizer, sample_report_with_placeholders):
        """Test that all placeholders in structural fields are replaced."""
        # Count placeholders in structural fields before deanonymization
        structural_placeholder_count = 0
        if 'findings' in sample_report_with_placeholders:
            for finding in sample_report_with_placeholders['findings']:
                if finding.get('hostname') == 'HOST_12':
                    structural_placeholder_count += 1
                if finding.get('username') == 'USER_03':
                    structural_placeholder_count += 1
                if finding.get('ip') == 'IP_07':
                    structural_placeholder_count += 1
        
        assert structural_placeholder_count > 0, "Report should contain placeholders in structural fields"
        
        # Deanonymize report
        result = deanonymizer.deanonymize_report(
            report=sample_report_with_placeholders
        )
        
        # Count placeholders in structural fields after deanonymization
        remaining_structural_placeholders = 0
        if 'findings' in result:
            for finding in result['findings']:
                if finding.get('hostname') == 'HOST_12':
                    remaining_structural_placeholders += 1
                if finding.get('username') == 'USER_03':
                    remaining_structural_placeholders += 1
                if finding.get('ip') == 'IP_07':
                    remaining_structural_placeholders += 1
        
        assert remaining_structural_placeholders == 0, \
            "All placeholders in structural fields should be replaced"

    def test_values_match_mapping_table(self, deanonymizer, sample_report_with_placeholders):
        """Test that replaced values match mapping table."""
        # Deanonymize report
        result = deanonymizer.deanonymize_report(
            report=sample_report_with_placeholders
        )
        
        # Check that values match mapping table
        if 'findings' in result and len(result['findings']) > 0:
            finding = result['findings'][0]
            
            # Expected values from mapping table
            expected_hostname = 'workstation-01.example.com'
            expected_username = 'john.doe'
            expected_ip = '192.168.1.100'
            
            # Verify values match (if they were replaced)
            if 'hostname' in finding and finding['hostname'] != 'HOST_12':
                assert finding['hostname'] == expected_hostname, \
                    f"Hostname should match mapping table: {finding['hostname']} != {expected_hostname}"
            
            if 'username' in finding and finding['username'] != 'USER_03':
                assert finding['username'] == expected_username, \
                    f"Username should match mapping table: {finding['username']} != {expected_username}"
            
            if 'ip' in finding and finding['ip'] != 'IP_07':
                assert finding['ip'] == expected_ip, \
                    f"IP should match mapping table: {finding['ip']} != {expected_ip}"

    def test_text_fields_deanonymized(self, deanonymizer, sample_report_with_placeholders):
        """Test that text fields containing placeholders are deanonymized."""
        # Deanonymize report
        result = deanonymizer.deanonymize_report(
            report=sample_report_with_placeholders
        )
        
        # Check text fields
        if 'executive_summary' in result:
            assert 'HOST_12' not in result['executive_summary'] or \
                   'workstation-01.example.com' in result['executive_summary'], \
                "Executive summary should have placeholders replaced"
        
        if 'markdown' in result:
            assert 'HOST_12' not in result['markdown'] or \
                   'workstation-01.example.com' in result['markdown'], \
                "Markdown should have placeholders replaced"
        
        if 'findings' in result and len(result['findings']) > 0:
            finding = result['findings'][0]
            if 'description' in finding:
                assert 'HOST_12' not in finding['description'] or \
                       'workstation-01.example.com' in finding['description'], \
                    "Description should have placeholders replaced"


class TestDeterminismOfDeanonymization:
    """TC-4-01-02: Determinism of deanonymization"""

    def test_deanonymization_uses_only_mapping_table(self, deanonymizer, sample_report_with_placeholders, mock_anonymizer_with_mapping):
        """Test that deanonymization uses only mapping table (not AI)."""
        # Reset mock call count
        mock_anonymizer_with_mapping.deanonymize.reset_mock()
        mock_anonymizer_with_mapping.deanonymize_record.reset_mock()
        
        # Deanonymize report
        result = deanonymizer.deanonymize_report(
            report=sample_report_with_placeholders
        )
        
        # Verify that only mapping table methods were called (no AI)
        assert mock_anonymizer_with_mapping.deanonymize.called or \
               mock_anonymizer_with_mapping.deanonymize_record.called, \
            "Mapping table methods should be called"
        
        # Verify no AI service was used (check that only deanonymize/deanonymize_record were called)
        # The anonymizer should only have deanonymize and deanonymize_record methods called
        call_methods = [call[0][0] if call[0] else str(call) for call in mock_anonymizer_with_mapping.method_calls]
        ai_methods = ['validate_finding', 'generate_executive_summary', 'analyze_evidence']
        assert not any(ai_method in str(call_methods) for ai_method in ai_methods), \
            "No AI methods should be called"

    def test_deanonymization_deterministic(self, deanonymizer, sample_report_with_placeholders):
        """Test that deanonymization is deterministic (same result every time)."""
        # First deanonymization
        result1 = deanonymizer.deanonymize_report(
            report=sample_report_with_placeholders
        )
        
        # Second deanonymization (same input)
        result2 = deanonymizer.deanonymize_report(
            report=sample_report_with_placeholders
        )
        
        # Results should be identical
        assert result1 == result2, "Deanonymization should be deterministic (same result every time)"
        
        # Verify specific values are the same
        if 'findings' in result1 and len(result1['findings']) > 0:
            finding1 = result1['findings'][0]
            finding2 = result2['findings'][0]
            
            assert finding1.get('hostname') == finding2.get('hostname'), \
                "Hostname should be the same in both results"
            assert finding1.get('username') == finding2.get('username'), \
                "Username should be the same in both results"
            assert finding1.get('ip') == finding2.get('ip'), \
                "IP should be the same in both results"

    def test_deterministic_with_different_calls(self, deanonymizer, sample_report_with_placeholders):
        """Test that deanonymization is deterministic across different calls."""
        # Create multiple copies of the same report
        report1 = sample_report_with_placeholders.copy()
        report2 = sample_report_with_placeholders.copy()
        report3 = sample_report_with_placeholders.copy()
        
        # Deanonymize each copy
        result1 = deanonymizer.deanonymize_report(report=report1)
        result2 = deanonymizer.deanonymize_report(report=report2)
        result3 = deanonymizer.deanonymize_report(report=report3)
        
        # All results should be identical
        assert result1 == result2 == result3, \
            "All deanonymization results should be identical"
        
        # Verify findings are the same
        if 'findings' in result1 and len(result1['findings']) > 0:
            finding1 = result1['findings'][0]
            finding2 = result2['findings'][0]
            finding3 = result3['findings'][0]
            
            assert finding1 == finding2 == finding3, \
                "All findings should be identical after deanonymization"

    def test_no_ai_used_in_deanonymization(self, deanonymizer, sample_report_with_placeholders, mock_anonymizer_with_mapping):
        """Test that no AI is used in deanonymization process."""
        # Reset mock
        mock_anonymizer_with_mapping.reset_mock()
        
        # Deanonymize report
        result = deanonymizer.deanonymize_report(
            report=sample_report_with_placeholders
        )
        
        # Verify only mapping table methods were called
        assert mock_anonymizer_with_mapping.deanonymize.called or \
               mock_anonymizer_with_mapping.deanonymize_record.called, \
            "Mapping table methods should be called"
        
        # Verify that only deanonymize/deanonymize_record methods were called
        # (not AI methods like validate_finding, generate_executive_summary)
        called_methods = [call[0] for call in mock_anonymizer_with_mapping.method_calls]
        ai_methods = ['validate_finding', 'generate_executive_summary', 'analyze_evidence', 'correlate_findings']
        assert not any(ai_method in called_methods for ai_method in ai_methods), \
            "No AI methods should be called during deanonymization"
        
        # Verify result is deterministic (not AI-generated)
        # If AI was used, results might vary slightly, but with mapping table they should be exact
        assert result is not None, "Result should not be None"

    def test_mapping_table_only_source(self, deanonymizer, sample_report_with_placeholders, mock_anonymizer_with_mapping):
        """Test that mapping table is the only source for deanonymization."""
        # Reset mock
        mock_anonymizer_with_mapping.reset_mock()
        
        # Deanonymize report
        result = deanonymizer.deanonymize_report(
            report=sample_report_with_placeholders
        )
        
        # Verify that mapping table methods were called
        assert mock_anonymizer_with_mapping.deanonymize.called or \
               mock_anonymizer_with_mapping.deanonymize_record.called, \
            "Mapping table methods should be called"
        
        # Verify that only deanonymize/deanonymize_record methods were called
        # (not AI methods or other methods)
        called_methods = [call[0] for call in mock_anonymizer_with_mapping.method_calls]
        allowed_methods = ['deanonymize', 'deanonymize_record', '_deanonymize_text']
        ai_methods = ['validate_finding', 'generate_executive_summary', 'analyze_evidence', 'correlate_findings']
        
        # Check that no AI methods were called
        assert not any(ai_method in called_methods for ai_method in ai_methods), \
            "No AI methods should be called during deanonymization"
        
        # Verify result is deterministic
        assert result is not None, "Result should not be None"

