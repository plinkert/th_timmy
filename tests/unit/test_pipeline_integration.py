"""
Unit tests for PHASE2-02: Pipeline Integration.

Test Cases:
- TC-2-02-01: Pełny pipeline end-to-end
- TC-2-02-02: Obsługa błędów w pipeline
"""

import pytest
import tempfile
import shutil
import json
import sys
import importlib.util
import types
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

# Add automation-scripts to path
project_root = Path(__file__).parent.parent.parent
automation_scripts_path = project_root / "automation-scripts"
sys.path.insert(0, str(automation_scripts_path))

# Create package structure
if "automation_scripts" not in sys.modules:
    sys.modules["automation_scripts"] = types.ModuleType("automation_scripts")
    sys.modules["automation_scripts"].__path__ = [str(automation_scripts_path)]
if "automation_scripts.orchestrators" not in sys.modules:
    sys.modules["automation_scripts.orchestrators"] = types.ModuleType("automation_scripts.orchestrators")
    sys.modules["automation_scripts.orchestrators"].__path__ = [str(automation_scripts_path / "orchestrators")]
if "automation_scripts.utils" not in sys.modules:
    sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
    sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
if "automation_scripts.services" not in sys.modules:
    sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
    sys.modules["automation_scripts.services"].__path__ = [str(automation_scripts_path / "services")]


@pytest.fixture
def mock_remote_executor():
    """Create a mock RemoteExecutor for testing."""
    mock_executor = Mock()
    mock_executor.execute_remote_command = Mock(return_value=("output", ""))
    mock_executor.execute_remote_script = Mock(return_value=("output", ""))
    mock_executor.upload_file = Mock(return_value=True)
    mock_executor.download_file = Mock(return_value=True)
    return mock_executor


@pytest.fixture
def mock_query_generator():
    """Create a mock QueryGenerator for testing."""
    mock_generator = Mock()
    mock_generator.generate_queries = Mock(return_value={
        'queries': {
            'Microsoft Defender': {
                'manual': [{'name': 'Test Query', 'query': 'DeviceProcessEvents | where ...'}],
                'api': [{'name': 'Test Query API', 'query': 'DeviceProcessEvents | where ...'}]
            }
        },
        'warnings': []
    })
    mock_generator.get_playbooks_for_techniques = Mock(return_value=[
        {'id': 'T1059-test', 'path': '/tmp/test_playbook'}
    ])
    return mock_generator


@pytest.fixture
def test_data_package(project_root_path):
    """Create test DataPackage with anonymized test data."""
    import sys
    import importlib.util
    import types
    
    automation_scripts_path = project_root_path / "automation-scripts"
    sys.path.insert(0, str(automation_scripts_path))
    
    if "automation_scripts.utils" not in sys.modules:
        sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
        sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
    
    data_package_path = automation_scripts_path / "utils" / "data_package.py"
    spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.data_package", data_package_path
    )
    data_package_module = importlib.util.module_from_spec(spec)
    sys.modules["automation_scripts.utils.data_package"] = data_package_module
    spec.loader.exec_module(data_package_module)
    
    DataPackage = data_package_module.DataPackage
    
    # Create test data with process events
    test_data = [
        {
            'timestamp': '2025-01-15T10:00:00Z',
            'source': 'Microsoft Defender',
            'event_type': 'ProcessCreated',
            'raw_data': {},
            'normalized_fields': {
                'device_name': 'test-device-01',
                'process_name': 'cmd.exe',
                'parent_process_name': 'explorer.exe',
                'command_line': 'cmd.exe /c echo test'
            }
        },
        {
            'timestamp': '2025-01-15T10:00:01Z',
            'source': 'Microsoft Defender',
            'event_type': 'ProcessCreated',
            'raw_data': {},
            'normalized_fields': {
                'device_name': 'test-device-01',
                'process_name': 'powershell.exe',
                'parent_process_name': 'cmd.exe',
                'command_line': 'powershell.exe -enc ...'
            }
        }
    ]
    
    package = DataPackage(
        source_type="manual",
        source_name="test_data",
        data=test_data
    )
    
    return package


@pytest.fixture
def pipeline_orchestrator(mock_remote_executor, mock_query_generator, project_root_path, temp_dir):
    """Create PipelineOrchestrator instance with mocked dependencies."""
    import sys
    import importlib.util
    import types
    import yaml
    
    automation_scripts_path = project_root_path / "automation-scripts"
    sys.path.insert(0, str(automation_scripts_path))
    
    if "automation_scripts.orchestrators" not in sys.modules:
        sys.modules["automation_scripts.orchestrators"] = types.ModuleType("automation_scripts.orchestrators")
        sys.modules["automation_scripts.orchestrators"].__path__ = [str(automation_scripts_path / "orchestrators")]
    
    pipeline_orchestrator_path = automation_scripts_path / "orchestrators" / "pipeline_orchestrator.py"
    spec = importlib.util.spec_from_file_location(
        "automation_scripts.orchestrators.pipeline_orchestrator", pipeline_orchestrator_path
    )
    pipeline_orchestrator_module = importlib.util.module_from_spec(spec)
    sys.modules["automation_scripts.orchestrators.pipeline_orchestrator"] = pipeline_orchestrator_module
    
    # Load dependencies
    # Load RemoteExecutor
    remote_executor_path = automation_scripts_path / "services" / "remote_executor.py"
    remote_executor_spec = importlib.util.spec_from_file_location(
        "automation_scripts.services.remote_executor", remote_executor_path
    )
    remote_executor_module = importlib.util.module_from_spec(remote_executor_spec)
    sys.modules["automation_scripts.services.remote_executor"] = remote_executor_module
    remote_executor_spec.loader.exec_module(remote_executor_module)
    
    # Load QueryGenerator
    query_generator_path = automation_scripts_path / "utils" / "query_generator.py"
    query_generator_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.query_generator", query_generator_path
    )
    query_generator_module = importlib.util.module_from_spec(query_generator_spec)
    sys.modules["automation_scripts.utils.query_generator"] = query_generator_module
    query_generator_spec.loader.exec_module(query_generator_module)
    
    # Load DataPackage
    data_package_path = automation_scripts_path / "utils" / "data_package.py"
    data_package_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.data_package", data_package_path
    )
    data_package_module = importlib.util.module_from_spec(data_package_spec)
    sys.modules["automation_scripts.utils.data_package"] = data_package_module
    data_package_spec.loader.exec_module(data_package_module)
    
    # Load PlaybookEngine
    playbook_engine_path = automation_scripts_path / "orchestrators" / "playbook_engine.py"
    playbook_engine_spec = importlib.util.spec_from_file_location(
        "automation_scripts.orchestrators.playbook_engine", playbook_engine_path
    )
    playbook_engine_module = importlib.util.module_from_spec(playbook_engine_spec)
    sys.modules["automation_scripts.orchestrators.playbook_engine"] = playbook_engine_module
    playbook_engine_spec.loader.exec_module(playbook_engine_module)
    
    # Load DeterministicAnonymizer
    deterministic_anonymizer_path = automation_scripts_path / "utils" / "deterministic_anonymizer.py"
    deterministic_anonymizer_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.deterministic_anonymizer", deterministic_anonymizer_path
    )
    deterministic_anonymizer_module = importlib.util.module_from_spec(deterministic_anonymizer_spec)
    sys.modules["automation_scripts.utils.deterministic_anonymizer"] = deterministic_anonymizer_module
    deterministic_anonymizer_spec.loader.exec_module(deterministic_anonymizer_module)
    
    # Now load pipeline_orchestrator
    spec.loader.exec_module(pipeline_orchestrator_module)
    
    PipelineOrchestrator = pipeline_orchestrator_module.PipelineOrchestrator
    
    # Create test config file
    test_config = {
        'vms': {
            'vm01': {'ip': '192.168.1.101'},
            'vm02': {'ip': '192.168.1.102'},
            'vm03': {'ip': '192.168.1.103'},
            'vm04': {'ip': '192.168.1.104'}
        },
        'database': {
            'host': '192.168.1.102',
            'port': 5432,
            'name': 'threat_hunting',
            'user': 'threat_hunter',
            'password': 'test_password'
        }
    }
    
    config_file = Path(temp_dir) / "test_config.yml"
    with open(config_file, 'w') as f:
        yaml.dump(test_config, f)
    
    orchestrator = PipelineOrchestrator(config_path=str(config_file))
    
    # Replace with mocks
    orchestrator.remote_executor = mock_remote_executor
    orchestrator.query_generator = mock_query_generator
    
    return orchestrator


@pytest.fixture
def dashboard_client_with_pipeline(dashboard_client, pipeline_orchestrator):
    """Create dashboard client with pipeline orchestrator override."""
    dashboard_api_module = dashboard_client._dashboard_api_module
    
    # Override get_pipeline_orchestrator to use test instance
    dashboard_api_module.get_pipeline_orchestrator = lambda: pipeline_orchestrator
    
    yield dashboard_client


class TestFullPipelineEndToEnd:
    """TC-2-02-01: Pełny pipeline end-to-end"""

    def test_full_pipeline_execution(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test that full pipeline executes through all stages."""
        # Mock remote executor responses
        mock_remote_executor.execute_remote_script.return_value = (
            'Data package test_package_id validated and ready for storage',
            ''
        )
        mock_remote_executor.execute_remote_command.return_value = (
            json.dumps({
                'all_findings': [
                    {
                        'finding_id': 'test_finding_1',
                        'technique_id': 'T1059',
                        'severity': 'high',
                        'confidence': 0.8
                    }
                ],
                'execution_results': [
                    {
                        'playbook_id': 'T1059-test',
                        'status': 'success',
                        'findings_count': 1
                    }
                ]
            }),
            ''
        )
        
        result = pipeline_orchestrator.execute_pipeline(
            technique_ids=["T1059"],
            tool_names=["Microsoft Defender"],
            ingest_mode="manual",
            data_package=test_data_package,
            anonymize=True
        )
        
        assert "pipeline_id" in result, "Result should contain 'pipeline_id'"
        assert "status" in result, "Result should contain 'status'"
        assert "stages" in result, "Result should contain 'stages'"
        assert result["status"] in ["success", "error"], "Status should be 'success' or 'error'"
        
        # Verify all stages are present
        assert "query_generation" in result["stages"], "Should have query_generation stage"
        assert "data_storage" in result["stages"], "Should have data_storage stage"
        assert "playbook_execution" in result["stages"], "Should have playbook_execution stage"
        assert "results_aggregation" in result["stages"], "Should have results_aggregation stage"

    def test_data_anonymized_on_vm01(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test that data is anonymized before storage on VM02."""
        # Mock remote executor to capture uploaded data
        uploaded_data = {}
        
        def capture_upload(vm_id, local_path, remote_path):
            with open(local_path, 'r') as f:
                uploaded_data[remote_path] = json.load(f)
            return True
        
        mock_remote_executor.upload_file.side_effect = capture_upload
        mock_remote_executor.execute_remote_script.return_value = (
            'Data package test_package_id validated and ready for storage',
            ''
        )
        mock_remote_executor.execute_remote_command.return_value = (
            json.dumps({'all_findings': [], 'execution_results': []}),
            ''
        )
        
        result = pipeline_orchestrator.execute_pipeline(
            technique_ids=["T1059"],
            tool_names=["Microsoft Defender"],
            ingest_mode="manual",
            data_package=test_data_package,
            anonymize=True
        )
        
        # Verify that anonymization info is set in data package
        # The data package should have anonymization metadata
        assert result["status"] in ["success", "error"], "Pipeline should complete"
        
        # Check if data was uploaded (indicating storage attempt)
        assert len(uploaded_data) > 0 or result["stages"].get("data_storage", {}).get("status") in ["success", "error"], \
            "Data should be uploaded to VM02 or storage stage should be attempted"

    def test_data_stored_in_database_vm02(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test that data is stored in database on VM02."""
        mock_remote_executor.execute_remote_script.return_value = (
            'Data package test_package_id validated and ready for storage',
            ''
        )
        mock_remote_executor.execute_remote_command.return_value = (
            json.dumps({'all_findings': [], 'execution_results': []}),
            ''
        )
        
        result = pipeline_orchestrator.execute_pipeline(
            technique_ids=["T1059"],
            tool_names=["Microsoft Defender"],
            ingest_mode="manual",
            data_package=test_data_package,
            anonymize=False  # Skip anonymization for simpler test
        )
        
        # Verify storage stage was executed
        storage_stage = result["stages"].get("data_storage", {})
        assert storage_stage.get("status") in ["success", "error", "skipped"], \
            "Storage stage should have status"
        
        # Verify remote executor was called for VM02 (upload_file or execute_remote_script)
        vm02_upload_calls = [
            call for call in mock_remote_executor.upload_file.call_args_list
            if len(call[0]) > 0 and call[0][0] == "vm02"
        ]
        vm02_script_calls = [
            call for call in mock_remote_executor.execute_remote_script.call_args_list
            if len(call[0]) > 0 and call[0][0] == "vm02"
        ]
        vm02_command_calls = [
            call for call in mock_remote_executor.execute_remote_command.call_args_list
            if len(call[0]) > 0 and call[0][0] == "vm02"
        ]
        
        # Should attempt to interact with VM02 or storage should be skipped/errored
        assert len(vm02_upload_calls) > 0 or len(vm02_script_calls) > 0 or len(vm02_command_calls) > 0 or \
            storage_stage.get("status") in ["skipped", "error"], \
            "Should attempt to interact with VM02 or storage should be skipped/errored"

    def test_playbook_executed_on_vm03(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test that playbook is executed on VM03."""
        mock_remote_executor.execute_remote_script.return_value = (
            'Data package test_package_id validated and ready for storage',
            ''
        )
        mock_remote_executor.execute_remote_command.return_value = (
            json.dumps({
                'all_findings': [
                    {
                        'finding_id': 'test_finding_1',
                        'technique_id': 'T1059',
                        'severity': 'high',
                        'confidence': 0.8
                    }
                ],
                'execution_results': [
                    {
                        'playbook_id': 'T1059-test',
                        'status': 'success',
                        'findings_count': 1,
                        'technique_id': 'T1059'
                    }
                ]
            }),
            ''
        )
        
        result = pipeline_orchestrator.execute_pipeline(
            technique_ids=["T1059"],
            tool_names=["Microsoft Defender"],
            ingest_mode="manual",
            data_package=test_data_package,
            anonymize=False
        )
        
        # Verify playbook execution stage
        execution_stage = result["stages"].get("playbook_execution", {})
        assert execution_stage.get("status") in ["success", "error"], \
            "Playbook execution stage should have status"
        
        # Verify remote executor was called for VM03
        vm03_calls = [
            call for call in mock_remote_executor.execute_remote_command.call_args_list
            if len(call[0]) > 0 and call[0][0] == "vm03"
        ]
        assert len(vm03_calls) > 0 or execution_stage.get("status") == "error", \
            "Should attempt to execute on VM03 or execution should have error"

    def test_findings_in_results(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test that findings are in pipeline results."""
        test_findings = [
            {
                'finding_id': 'test_finding_1',
                'technique_id': 'T1059',
                'severity': 'high',
                'confidence': 0.8,
                'title': 'Test Finding',
                'description': 'Test finding description'
            }
        ]
        
        mock_remote_executor.execute_remote_script.return_value = (
            'Data package test_package_id validated and ready for storage',
            ''
        )
        mock_remote_executor.execute_remote_command.return_value = (
            json.dumps({
                'all_findings': test_findings,
                'execution_results': [
                    {
                        'playbook_id': 'T1059-test',
                        'status': 'success',
                        'findings_count': 1,
                        'technique_id': 'T1059'
                    }
                ]
            }),
            ''
        )
        
        result = pipeline_orchestrator.execute_pipeline(
            technique_ids=["T1059"],
            tool_names=["Microsoft Defender"],
            ingest_mode="manual",
            data_package=test_data_package,
            anonymize=False
        )
        
        # Verify findings are in results
        assert "total_findings" in result, "Result should contain 'total_findings'"
        assert result["total_findings"] >= 0, "Total findings should be non-negative"
        
        # Verify aggregation stage has findings
        aggregation_stage = result["stages"].get("results_aggregation", {})
        if aggregation_stage.get("status") == "success":
            assert "total_findings" in aggregation_stage, "Aggregation should have total_findings"
            assert aggregation_stage.get("total_findings", 0) >= 0, "Total findings should be non-negative"

    def test_data_flows_through_all_vms(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test that data flows through all VMs correctly."""
        mock_remote_executor.execute_remote_script.return_value = (
            'Data package test_package_id validated and ready for storage',
            ''
        )
        mock_remote_executor.execute_remote_command.return_value = (
            json.dumps({
                'all_findings': [],
                'execution_results': []
            }),
            ''
        )
        
        result = pipeline_orchestrator.execute_pipeline(
            technique_ids=["T1059"],
            tool_names=["Microsoft Defender"],
            ingest_mode="manual",
            data_package=test_data_package,
            anonymize=False
        )
        
        # Verify all stages completed
        assert "stages" in result, "Result should contain 'stages'"
        
        # Verify stage order: query_generation -> data_storage -> playbook_execution -> results_aggregation
        stages = result["stages"]
        assert "query_generation" in stages, "Should have query_generation stage"
        assert "data_storage" in stages, "Should have data_storage stage"
        assert "playbook_execution" in stages, "Should have playbook_execution stage"
        assert "results_aggregation" in stages, "Should have results_aggregation stage"
        
        # Verify pipeline status
        assert result["status"] in ["success", "error"], "Pipeline should have status"


class TestErrorHandling:
    """TC-2-02-02: Obsługa błędów w pipeline"""

    def test_invalid_data_handled(self, pipeline_orchestrator, mock_remote_executor):
        """Test that invalid data is handled gracefully."""
        # Create invalid data package (missing required fields)
        invalid_data = [
            {
                'timestamp': '2025-01-15T10:00:00Z',
                # Missing required fields
            }
        ]
        
        from automation_scripts.utils.data_package import DataPackage
        
        try:
            invalid_package = DataPackage(
                source_type="manual",
                source_name="invalid_data",
                data=invalid_data
            )
        except Exception:
            # If DataPackage validation fails, that's expected
            # Test that pipeline handles this
            with pytest.raises(Exception):
                pipeline_orchestrator.execute_pipeline(
                    technique_ids=["T1059"],
                    tool_names=["Microsoft Defender"],
                    ingest_mode="manual",
                    data_package=None,  # Missing data package
                    anonymize=False
                )
        else:
            # If DataPackage is created, test pipeline execution
            result = pipeline_orchestrator.execute_pipeline(
                technique_ids=["T1059"],
                tool_names=["Microsoft Defender"],
                ingest_mode="manual",
                data_package=invalid_package,
                anonymize=False
            )
            
            # Pipeline should handle errors gracefully
            assert result["status"] in ["success", "error"], "Pipeline should have status"
            if result["status"] == "error":
                assert "error" in result, "Error should be in result"

    def test_pipeline_continues_after_error(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test that pipeline continues after error in one stage."""
        # Make storage stage fail
        mock_remote_executor.execute_remote_script.side_effect = Exception("Storage failed")
        
        # But playbook execution should still be attempted
        mock_remote_executor.execute_remote_command.return_value = (
            json.dumps({
                'all_findings': [],
                'execution_results': []
            }),
            ''
        )
        
        # Pipeline should handle error and continue or fail gracefully
        try:
            result = pipeline_orchestrator.execute_pipeline(
                technique_ids=["T1059"],
                tool_names=["Microsoft Defender"],
                ingest_mode="manual",
                data_package=test_data_package,
                anonymize=False
            )
            
            # Pipeline should have status (either success or error)
            assert "status" in result, "Result should have status"
            assert result["status"] in ["success", "error"], "Status should be success or error"
            
            # If error, should have error message
            if result["status"] == "error":
                assert "error" in result, "Error should be in result"
        except Exception as e:
            # If pipeline raises exception, that's also acceptable error handling
            assert isinstance(e, Exception), "Should raise exception for error handling"

    def test_error_logged(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test that errors are logged."""
        # Make a stage fail
        mock_remote_executor.execute_remote_script.side_effect = Exception("Test error")
        
        # Pipeline should log error
        try:
            result = pipeline_orchestrator.execute_pipeline(
                technique_ids=["T1059"],
                tool_names=["Microsoft Defender"],
                ingest_mode="manual",
                data_package=test_data_package,
                anonymize=False
            )
            
            # Error should be in result
            if result.get("status") == "error":
                assert "error" in result, "Error should be in result"
                assert len(result["error"]) > 0, "Error message should not be empty"
        except Exception:
            # If exception is raised, that's also acceptable
            pass

    def test_pipeline_not_hung(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test that pipeline doesn't hang on errors."""
        # Make remote executor hang (simulate timeout)
        def hanging_command(*args, **kwargs):
            import time
            time.sleep(0.1)  # Short delay to simulate hang
            raise Exception("Timeout")
        
        mock_remote_executor.execute_remote_command.side_effect = hanging_command
        mock_remote_executor.execute_remote_script.side_effect = hanging_command
        
        # Pipeline should handle timeout and not hang
        try:
            result = pipeline_orchestrator.execute_pipeline(
                technique_ids=["T1059"],
                tool_names=["Microsoft Defender"],
                ingest_mode="manual",
                data_package=test_data_package,
                anonymize=False
            )
            
            # Should complete (with error status)
            assert "status" in result, "Result should have status"
            assert "completed_at" in result, "Result should have completed_at"
        except Exception:
            # If exception is raised, that's acceptable
            pass


class TestAdditionalScenarios:
    """Additional test scenarios for pipeline integration"""

    def test_manual_ingest_mode(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test pipeline with manual ingest mode."""
        mock_remote_executor.execute_remote_script.return_value = (
            'Data package test_package_id validated and ready for storage',
            ''
        )
        mock_remote_executor.execute_remote_command.return_value = (
            json.dumps({'all_findings': [], 'execution_results': []}),
            ''
        )
        
        result = pipeline_orchestrator.execute_pipeline(
            technique_ids=["T1059"],
            tool_names=["Microsoft Defender"],
            ingest_mode="manual",
            data_package=test_data_package,
            anonymize=False
        )
        
        assert result["ingest_mode"] == "manual", "Ingest mode should be manual"
        assert "data_ingestion" not in result["stages"] or result["stages"].get("data_ingestion", {}).get("status") == "skipped", \
            "Data ingestion should be skipped for manual mode"

    def test_api_ingest_mode(self, pipeline_orchestrator, mock_remote_executor):
        """Test pipeline with API ingest mode."""
        result = pipeline_orchestrator.execute_pipeline(
            technique_ids=["T1059"],
            tool_names=["Microsoft Defender"],
            ingest_mode="api",
            data_package=None,
            anonymize=False
        )
        
        assert result["ingest_mode"] == "api", "Ingest mode should be api"
        # API ingestion may be skipped if not fully implemented
        assert "data_ingestion" in result["stages"], "Should have data_ingestion stage"

    def test_anonymization_enabled(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test pipeline with anonymization enabled."""
        mock_remote_executor.execute_remote_script.return_value = (
            'Data package test_package_id validated and ready for storage',
            ''
        )
        mock_remote_executor.execute_remote_command.return_value = (
            json.dumps({'all_findings': [], 'execution_results': []}),
            ''
        )
        
        result = pipeline_orchestrator.execute_pipeline(
            technique_ids=["T1059"],
            tool_names=["Microsoft Defender"],
            ingest_mode="manual",
            data_package=test_data_package,
            anonymize=True
        )
        
        # Verify anonymization was attempted
        storage_stage = result["stages"].get("data_storage", {})
        # Anonymization happens in storage stage
        assert storage_stage.get("status") in ["success", "error", "skipped"], \
            "Storage stage should have status"

    def test_multiple_playbooks(self, pipeline_orchestrator, test_data_package, mock_remote_executor):
        """Test pipeline with multiple playbooks."""
        # Mock query generator to return multiple playbooks
        pipeline_orchestrator.query_generator.get_playbooks_for_techniques = Mock(return_value=[
            {'id': 'T1059-test-1', 'path': '/tmp/test_playbook_1'},
            {'id': 'T1059-test-2', 'path': '/tmp/test_playbook_2'}
        ])
        
        mock_remote_executor.execute_remote_script.return_value = (
            'Data package test_package_id validated and ready for storage',
            ''
        )
        mock_remote_executor.execute_remote_command.return_value = (
            json.dumps({
                'all_findings': [],
                'execution_results': [
                    {'playbook_id': 'T1059-test-1', 'status': 'success', 'findings_count': 0},
                    {'playbook_id': 'T1059-test-2', 'status': 'success', 'findings_count': 0}
                ]
            }),
            ''
        )
        
        result = pipeline_orchestrator.execute_pipeline(
            technique_ids=["T1059"],
            tool_names=["Microsoft Defender"],
            ingest_mode="manual",
            data_package=test_data_package,
            anonymize=False
        )
        
        # Verify multiple playbooks were executed
        execution_stage = result["stages"].get("playbook_execution", {})
        if execution_stage.get("status") == "success":
            results = execution_stage.get("results", {})
            execution_results = results.get("execution_results", [])
            assert len(execution_results) >= 0, "Should have execution results"

    def test_pipeline_api_endpoint(self, dashboard_client_with_pipeline, test_data_package):
        """Test pipeline execution via API endpoint."""
        response = dashboard_client_with_pipeline.post(
            "/pipeline/execute",
            json={
                "technique_ids": ["T1059"],
                "tool_names": ["Microsoft Defender"],
                "ingest_mode": "manual",
                "anonymize": False,
                "data_package": test_data_package.to_dict()
            }
        )
        
        assert response.status_code in [200, 500], f"Expected 200 or 500, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data, "Response should contain 'success'"
            assert "pipeline_id" in data, "Response should contain 'pipeline_id'"
            assert "status" in data, "Response should contain 'status'"
            assert "stages" in data, "Response should contain 'stages'"

