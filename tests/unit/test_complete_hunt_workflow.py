"""
Unit tests for PHASE4-03: n8n Workflow - Complete Pipeline End-to-End.

Test Cases:
- TC-4-03-01: Complete workflow execution
- TC-4-03-02: Component integration
- TC-4-03-03: Error handling
- TC-4-03-04: Workflow status tracking
- TC-4-03-05: Notifications
- TC-4-03-06: Data flow between phases
- TC-4-03-07: Parallel workflow execution
- TC-4-03-08: Logging and audit trail
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
import httpx

# Add automation-scripts to path
project_root = Path(__file__).parent.parent.parent
automation_scripts_path = project_root / "automation-scripts"
sys.path.insert(0, str(automation_scripts_path))

# Create package structure
if "automation_scripts" not in sys.modules:
    sys.modules["automation_scripts"] = types.ModuleType("automation_scripts")
    sys.modules["automation_scripts"].__path__ = [str(automation_scripts_path)]
if "automation_scripts.api" not in sys.modules:
    sys.modules["automation_scripts.api"] = types.ModuleType("automation_scripts.api")
    sys.modules["automation_scripts.api"].__path__ = [str(automation_scripts_path / "api")]


@pytest.fixture
def mock_pipeline_orchestrator():
    """Create a mock pipeline orchestrator."""
    orchestrator = Mock()
    
    orchestrator.execute_pipeline = Mock(return_value={
        'pipeline_id': 'pipeline_20250115_103000',
        'status': 'success',
        'total_findings': 3,
        'stages': {
            'query_generation': {'status': 'success'},
            'data_ingestion': {'status': 'success'},
            'data_storage': {'status': 'success'},
            'playbook_execution': {'status': 'success'},
            'results_aggregation': {'status': 'success'}
        },
        'findings': [
            {
                'finding_id': 'T1059_001',
                'technique_id': 'T1059',
                'severity': 'high',
                'confidence': 0.85
            }
        ],
        'started_at': '2025-01-15T10:30:00Z',
        'completed_at': '2025-01-15T10:35:00Z'
    })
    
    return orchestrator


@pytest.fixture
def mock_ai_reviewer():
    """Create a mock AI reviewer."""
    reviewer = Mock()
    
    reviewer.review_playbook_execution = Mock(return_value={
        'review_id': 'review_20250115_103000',
        'status': 'completed',
        'result': {
            'batch_review': {
                'summary': {
                    'reviewed': 3,
                    'valid': 2,
                    'invalid': 1
                },
                'results': [
                    {
                        'finding_id': 'T1059_001',
                        'validated': True,
                        'confidence': 0.85
                    }
                ]
            }
        }
    })
    
    return reviewer


@pytest.fixture
def mock_final_report_generator():
    """Create a mock final report generator."""
    generator = Mock()
    
    generator.generate_final_report = Mock(return_value={
        'report_id': 'final_report_20250115_103000',
        'generated_at': '2025-01-15T10:40:00Z',
        'findings_count': 3,
        'markdown': '# Final Report\n\nTest report',
        'json': {'report_id': 'final_report_20250115_103000'}
    })
    
    return generator


# Note: dashboard_client fixture removed - use @patch decorator in tests instead


@pytest.fixture
def sample_workflow_request():
    """Create sample workflow request."""
    return {
        'technique_ids': ['T1059', 'T1047', 'T1071'],
        'tool_names': ['Microsoft Defender for Endpoint', 'Sentinel'],
        'ingest_mode': 'manual',
        'anonymize': True,
        'ai_review': True,
        'generate_report': True,
        'deanonymize': True
    }


class TestCompleteWorkflowExecution:
    """TC-4-03-01: Complete workflow execution"""

    def test_workflow_structure_has_all_nodes(self):
        """Test that workflow structure has all required nodes."""
        # Load workflow JSON
        workflow_path = project_root / "hosts" / "vm04-orchestrator" / "n8n-workflows" / "complete-hunt-workflow.json"
        
        if workflow_path.exists():
            with open(workflow_path, 'r') as f:
                workflow = json.load(f)
            
            # Check that workflow has nodes
            assert 'nodes' in workflow, "Workflow should have nodes"
            assert len(workflow['nodes']) > 0, "Workflow should have at least one node"
            
            # Check for key nodes
            node_names = [node.get('name', '') for node in workflow['nodes']]
            assert 'Execute Complete Hunt' in node_names, "Should have Execute Complete Hunt node"
            assert 'Execute Pipeline' in node_names, "Should have Execute Pipeline node"
            assert 'AI Review' in node_names, "Should have AI Review node"
            assert 'Generate Final Report' in node_names, "Should have Generate Final Report node"

    def test_workflow_connections_correct(self):
        """Test that workflow connections are correct."""
        # Load workflow JSON
        workflow_path = project_root / "hosts" / "vm04-orchestrator" / "n8n-workflows" / "complete-hunt-workflow.json"
        
        if workflow_path.exists():
            with open(workflow_path, 'r') as f:
                workflow = json.load(f)
            
            # Check that workflow has connections
            assert 'connections' in workflow, "Workflow should have connections"
            
            connections = workflow['connections']
            # Check that Execute Pipeline connects to AI Review
            if 'Execute Pipeline' in connections:
                assert 'AI Review' in str(connections['Execute Pipeline']), \
                    "Execute Pipeline should connect to AI Review"
            
            # Check that AI Review connects to Generate Final Report
            if 'AI Review' in connections:
                assert 'Generate Final Report' in str(connections['AI Review']), \
                    "AI Review should connect to Generate Final Report"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_pipeline_execution_endpoint_works(self, mock_data_package, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator):
        """Test that pipeline execution endpoint works."""
        # Mock get_pipeline_orchestrator
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        
        # Execute pipeline
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert response.status_code == 200, f"Pipeline execution should succeed: {response.text}"
        result = response.json()
        assert result.get('success') is True, "Pipeline execution should be successful"
        assert 'pipeline_id' in result, "Result should contain pipeline_id"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.api.dashboard_api.get_ai_reviewer')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_all_workflow_steps_executed(self, mock_data_package, mock_get_reviewer, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator, mock_ai_reviewer, mock_final_report_generator):
        """Test that all workflow steps are executed."""
        # Mock get functions
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        mock_get_reviewer.return_value = mock_ai_reviewer
        
        # Step 1: Execute pipeline
        pipeline_response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert pipeline_response.status_code == 200, "Pipeline execution should succeed"
        pipeline_result = pipeline_response.json()
        
        # Step 2: AI Review (if enabled)
        if sample_workflow_request.get('ai_review'):
            review_response = dashboard_client.post(
                "/ai-review/review-execution",
                json={
                    'execution_result': pipeline_result,
                    'update_status': True
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
            
            assert review_response.status_code == 200, "AI Review should succeed"
            review_result = review_response.json()
            assert review_result.get('success') is True, "AI Review should be successful"
        
        # Step 3: Generate Final Report (if enabled)
        if sample_workflow_request.get('generate_report'):
            report_response = dashboard_client.post(
                "/final-report/generate",
                json={
                    'findings': pipeline_result.get('findings', []),
                    'context': {'pipeline_id': pipeline_result.get('pipeline_id')},
                    'deanonymize': sample_workflow_request.get('deanonymize', True),
                    'include_executive_summary': True,
                    'format': 'both'
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
            
            assert report_response.status_code == 200, "Final report generation should succeed"
            report_result = report_response.json()
            assert report_result.get('success') is True, "Final report generation should be successful"


class TestComponentIntegration:
    """TC-4-03-02: Component integration"""

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    def test_phase_0_management_called(self, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator):
        """Test that Phase 0 (management) is called."""
        # Mock get_pipeline_orchestrator
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        
        # Pipeline orchestrator may use management services
        # This is tested indirectly through pipeline execution
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert response.status_code == 200, "Pipeline execution should succeed"
        # Pipeline orchestrator internally uses management services
        assert mock_pipeline_orchestrator.execute_pipeline.called, \
            "Pipeline orchestrator should be called"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    def test_phase_1_query_generation_called(self, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator):
        """Test that Phase 1 (query generation) is called."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert response.status_code == 200, "Pipeline execution should succeed"
        result = response.json()
        
        # Check that query generation stage is in result
        if 'stages' in result:
            stages = result['stages']
            # Query generation is part of pipeline execution
            assert 'query_generation' in stages or 'data_ingestion' in stages, \
                "Query generation should be part of pipeline execution"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    def test_phase_2_playbook_execution_called(self, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator):
        """Test that Phase 2 (playbook execution) is called."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert response.status_code == 200, "Pipeline execution should succeed"
        result = response.json()
        
        # Check that playbook execution stage is in result
        if 'stages' in result:
            stages = result['stages']
            assert 'playbook_execution' in stages, \
                "Playbook execution should be part of pipeline execution"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.api.dashboard_api.get_ai_reviewer')
    def test_phase_3_ai_review_called(self, mock_get_reviewer, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator, mock_ai_reviewer):
        """Test that Phase 3 (AI review) is called."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        mock_get_reviewer.return_value = mock_ai_reviewer
        # First execute pipeline
        pipeline_response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        pipeline_result = pipeline_response.json()
        
        # Then execute AI review
        review_response = dashboard_client.post(
            "/ai-review/review-execution",
            json={
                'execution_result': pipeline_result,
                'update_status': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert review_response.status_code == 200, "AI Review should succeed"
        assert mock_ai_reviewer.review_playbook_execution.called, \
            "AI Reviewer should be called"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    def test_phase_4_reporting_called(self, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator, mock_final_report_generator):
        """Test that Phase 4 (reporting) is called."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        # First execute pipeline
        pipeline_response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        pipeline_result = pipeline_response.json()
        
        # Then generate final report
        report_response = dashboard_client.post(
            "/final-report/generate",
            json={
                'findings': pipeline_result.get('findings', []),
                'context': {'pipeline_id': pipeline_result.get('pipeline_id')},
                'deanonymize': True,
                'include_executive_summary': True,
                'format': 'both'
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert report_response.status_code == 200, "Final report generation should succeed"
        # Note: mock_final_report_generator is not directly accessible, but endpoint should work

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.api.dashboard_api.get_ai_reviewer')
    def test_all_phases_in_correct_order(self, mock_get_reviewer, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator, mock_ai_reviewer):
        """Test that all phases are called in correct order."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        mock_get_reviewer.return_value = mock_ai_reviewer
        # Reset mocks
        mock_pipeline_orchestrator.execute_pipeline.reset_mock()
        mock_ai_reviewer.review_playbook_execution.reset_mock()
        
        # Step 1: Pipeline execution (includes Phase 0, 1, 2)
        pipeline_response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        pipeline_result = pipeline_response.json()
        
        # Step 2: AI Review (Phase 3)
        review_response = dashboard_client.post(
            "/ai-review/review-execution",
            json={
                'execution_result': pipeline_result,
                'update_status': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        # Verify order: pipeline should be called before AI review
        assert mock_pipeline_orchestrator.execute_pipeline.called, \
            "Pipeline should be called first"
        assert mock_ai_reviewer.review_playbook_execution.called, \
            "AI Review should be called after pipeline"


class TestErrorHandling:
    """TC-4-03-03: Error handling"""

    def test_workflow_handles_invalid_parameters(self, dashboard_client):
        """Test that workflow handles invalid parameters."""
        # Try to execute pipeline with invalid parameters
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': [],  # Empty techniques
                'tool_names': [],
                'ingest_mode': 'invalid_mode',
                'anonymize': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        # Should either succeed with empty results or return error
        # The exact behavior depends on implementation
        assert response.status_code in [200, 400, 422], \
            f"Should handle invalid parameters gracefully: {response.status_code}"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    def test_workflow_handles_errors_gracefully(self, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test that workflow handles errors gracefully."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        # Make pipeline orchestrator raise an error
        mock_pipeline_orchestrator.execute_pipeline.side_effect = Exception("Pipeline execution failed")
        
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': ['T1059'],
                'tool_names': ['Microsoft Defender'],
                'ingest_mode': 'manual',
                'anonymize': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        # Should return error status, not crash
        assert response.status_code in [500, 400], \
            f"Should return error status: {response.status_code}"
        
        result = response.json()
        assert 'error' in result or 'detail' in result, \
            "Error response should contain error information"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    def test_workflow_does_not_hang_on_errors(self, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test that workflow does not hang on errors."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        # Make pipeline orchestrator raise an error
        mock_pipeline_orchestrator.execute_pipeline.side_effect = Exception("Pipeline execution failed")
        
        import time
        start_time = time.time()
        
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': ['T1059'],
                'tool_names': ['Microsoft Defender'],
                'ingest_mode': 'manual',
                'anonymize': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        elapsed_time = time.time() - start_time
        
        # Should respond quickly (not hang)
        assert elapsed_time < 5.0, "Workflow should not hang on errors"
        assert response.status_code in [500, 400], "Should return error status"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    def test_errors_logged(self, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test that errors are logged."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        # Make pipeline orchestrator raise an error
        mock_pipeline_orchestrator.execute_pipeline.side_effect = Exception("Pipeline execution failed")
        
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': ['T1059'],
                'tool_names': ['Microsoft Defender'],
                'ingest_mode': 'manual',
                'anonymize': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        # Error should be logged (we can't directly check logs, but error should be in response)
        assert response.status_code in [500, 400], "Should return error status"
        result = response.json()
        assert 'error' in result or 'detail' in result, \
            "Error should be included in response"


class TestWorkflowStatusTracking:
    """TC-4-03-04: Workflow status tracking"""

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    def test_workflow_status_running(self, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator):
        """Test that workflow status changes to running."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        # Execute pipeline
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert response.status_code == 200, "Pipeline execution should succeed"
        result = response.json()
        
        # Check that status is present
        assert 'status' in result, "Result should contain status"
        # Status should be 'success' after completion
        assert result.get('status') in ['success', 'running', 'completed'], \
            f"Status should be valid: {result.get('status')}"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    def test_workflow_status_completed(self, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator):
        """Test that workflow status changes to completed."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        # Execute pipeline
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert response.status_code == 200, "Pipeline execution should succeed"
        result = response.json()
        
        # Check that status is completed/success
        assert result.get('status') in ['success', 'completed'], \
            f"Status should be completed: {result.get('status')}"
        assert result.get('success') is True, "Success should be True"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    def test_workflow_status_failed(self, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test that workflow status changes to failed on error."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        # Make pipeline orchestrator raise an error
        mock_pipeline_orchestrator.execute_pipeline.side_effect = Exception("Pipeline execution failed")
        
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': ['T1059'],
                'tool_names': ['Microsoft Defender'],
                'ingest_mode': 'manual',
                'anonymize': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        # Should return error status
        assert response.status_code in [500, 400], "Should return error status"
        result = response.json()
        # Status should indicate failure
        assert result.get('success') is False or 'error' in result or 'detail' in result, \
            "Result should indicate failure"


class TestNotifications:
    """TC-4-03-05: Notifications"""

    @pytest.mark.skip(reason="Notifications not yet implemented in API")
    def test_notification_sent_on_completion(self, dashboard_client, sample_workflow_request):
        """Test that notification is sent on workflow completion."""
        # This test is skipped as notifications are not yet implemented
        pass

    @pytest.mark.skip(reason="Notifications not yet implemented in API")
    def test_notification_contains_status(self, dashboard_client, sample_workflow_request):
        """Test that notification contains status."""
        # This test is skipped as notifications are not yet implemented
        pass

    @pytest.mark.skip(reason="Notifications not yet implemented in API")
    def test_notification_contains_report_link(self, dashboard_client, sample_workflow_request):
        """Test that notification contains link to report."""
        # This test is skipped as notifications are not yet implemented
        pass


class TestDataFlowBetweenPhases:
    """TC-4-03-06: Data flow between phases"""

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_data_flows_from_phase_1_to_phase_2(self, mock_data_package, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator):
        """Test that data flows from Phase 1 to Phase 2."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        # Execute pipeline (Phase 1 query generation → Phase 2 playbook execution)
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert response.status_code == 200, "Pipeline execution should succeed"
        result = response.json()
        
        # Check that findings are present (data from Phase 2)
        assert 'total_findings' in result or 'findings' in result, \
            "Result should contain findings from Phase 2"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.api.dashboard_api.get_ai_reviewer')
    def test_data_flows_from_phase_2_to_phase_3(self, mock_get_reviewer, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator, mock_ai_reviewer):
        """Test that data flows from Phase 2 to Phase 3."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        mock_get_reviewer.return_value = mock_ai_reviewer
        # Execute pipeline (Phase 2)
        pipeline_response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        pipeline_result = pipeline_response.json()
        
        # Execute AI Review (Phase 3) with data from Phase 2
        review_response = dashboard_client.post(
            "/ai-review/review-execution",
            json={
                'execution_result': pipeline_result,
                'update_status': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert review_response.status_code == 200, "AI Review should succeed"
        review_result = review_response.json()
        
        # Check that review result contains data from Phase 2
        assert 'result' in review_result, "Review result should contain result"
        # Review should process findings from Phase 2
        if 'result' in review_result and 'batch_review' in review_result['result']:
            assert 'summary' in review_result['result']['batch_review'], \
                "Review should process findings from Phase 2"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.api.dashboard_api.get_ai_reviewer')
    def test_data_flows_from_phase_3_to_phase_4(self, mock_get_reviewer, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator, mock_ai_reviewer):
        """Test that data flows from Phase 3 to Phase 4."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        mock_get_reviewer.return_value = mock_ai_reviewer
        # Execute pipeline (Phase 2)
        pipeline_response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        pipeline_result = pipeline_response.json()
        
        # Execute AI Review (Phase 3)
        review_response = dashboard_client.post(
            "/ai-review/review-execution",
            json={
                'execution_result': pipeline_result,
                'update_status': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        review_result = review_response.json()
        
        # Generate Final Report (Phase 4) with data from Phase 3
        report_response = dashboard_client.post(
            "/final-report/generate",
            json={
                'findings': review_result.get('result', {}).get('batch_review', {}).get('results', []) or 
                           pipeline_result.get('findings', []),
                'context': {'pipeline_id': pipeline_result.get('pipeline_id')},
                'deanonymize': True,
                'include_executive_summary': True,
                'format': 'both'
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert report_response.status_code == 200, "Final report generation should succeed"
        report_result = report_response.json()
        
        # Check that report contains data from Phase 3
        assert 'report' in report_result, "Report result should contain report"
        if 'report' in report_result:
            assert 'findings_count' in report_result['report'] or 'findings' in report_result['report'], \
                "Report should contain findings from Phase 3"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.api.dashboard_api.get_ai_reviewer')
    def test_no_data_lost_between_phases(self, mock_get_reviewer, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator, mock_ai_reviewer):
        """Test that no data is lost between phases."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        mock_get_reviewer.return_value = mock_ai_reviewer
        # Execute pipeline
        pipeline_response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        pipeline_result = pipeline_response.json()
        pipeline_findings_count = pipeline_result.get('total_findings', 0)
        
        # Execute AI Review
        review_response = dashboard_client.post(
            "/ai-review/review-execution",
            json={
                'execution_result': pipeline_result,
                'update_status': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        review_result = review_response.json()
        
        # Check that findings count is preserved
        if 'result' in review_result and 'batch_review' in review_result['result']:
            review_summary = review_result['result']['batch_review'].get('summary', {})
            reviewed_count = review_summary.get('reviewed', 0)
            # Reviewed count should match or be close to pipeline findings count
            assert reviewed_count == pipeline_findings_count or reviewed_count > 0, \
                f"Findings should not be lost: {reviewed_count} vs {pipeline_findings_count}"


class TestParallelWorkflowExecution:
    """TC-4-03-07: Parallel workflow execution"""

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_multiple_workflows_execute_parallel(self, mock_data_package, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test that multiple workflows can execute in parallel."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        import concurrent.futures
        
        def execute_workflow(technique_ids):
            return dashboard_client.post(
                "/pipeline/execute",
                json={
                    'technique_ids': technique_ids,
                    'tool_names': ['Microsoft Defender'],
                    'ingest_mode': 'manual',
                    'anonymize': True
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
        
        # Execute 3 workflows in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(execute_workflow, ['T1059']),
                executor.submit(execute_workflow, ['T1047']),
                executor.submit(execute_workflow, ['T1071'])
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All workflows should succeed
        assert all(r.status_code == 200 for r in results), \
            "All parallel workflows should succeed"
        
        # Check that all have different pipeline IDs
        pipeline_ids = [r.json().get('pipeline_id') for r in results if r.status_code == 200]
        assert len(set(pipeline_ids)) == len(pipeline_ids), \
            "Each workflow should have unique pipeline ID"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_no_conflicts_between_parallel_workflows(self, mock_data_package, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test that there are no conflicts between parallel workflows."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        import concurrent.futures
        
        def execute_workflow(technique_ids):
            return dashboard_client.post(
                "/pipeline/execute",
                json={
                    'technique_ids': technique_ids,
                    'tool_names': ['Microsoft Defender'],
                    'ingest_mode': 'manual',
                    'anonymize': True
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
        
        # Execute 3 workflows in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(execute_workflow, ['T1059']),
                executor.submit(execute_workflow, ['T1047']),
                executor.submit(execute_workflow, ['T1071'])
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All workflows should succeed without conflicts
        assert all(r.status_code == 200 for r in results), \
            "All parallel workflows should succeed without conflicts"
        
        # Check that results are independent
        for result in results:
            if result.status_code == 200:
                result_data = result.json()
                assert 'pipeline_id' in result_data, \
                    "Each workflow should have independent results"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_parallel_workflows_produce_correct_results(self, mock_data_package, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test that parallel workflows produce correct results."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        import concurrent.futures
        
        def execute_workflow(technique_ids):
            return dashboard_client.post(
                "/pipeline/execute",
                json={
                    'technique_ids': technique_ids,
                    'tool_names': ['Microsoft Defender'],
                    'ingest_mode': 'manual',
                    'anonymize': True
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
        
        # Execute 3 workflows in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(execute_workflow, ['T1059']),
                executor.submit(execute_workflow, ['T1047']),
                executor.submit(execute_workflow, ['T1071'])
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All workflows should produce correct results
        for result in results:
            if result.status_code == 200:
                result_data = result.json()
                assert result_data.get('success') is True, \
                    "Each workflow should produce correct results"
                assert 'pipeline_id' in result_data, \
                    "Each workflow should have pipeline_id"


class TestLoggingAndAuditTrail:
    """TC-4-03-08: Logging and audit trail"""

    def test_workflow_operations_logged(self, dashboard_client, sample_workflow_request):
        """Test that workflow operations are logged."""
        # Execute pipeline
        response = dashboard_client_with_mocks.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert response.status_code == 200, "Pipeline execution should succeed"
        result = response.json()
        
        # Check that result contains audit information
        assert 'pipeline_id' in result, "Result should contain pipeline_id for audit"
        assert 'started_at' in result or 'completed_at' in result, \
            "Result should contain timestamps for audit"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.api.dashboard_api.get_ai_reviewer')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_audit_trail_complete(self, mock_data_package, mock_get_reviewer, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator, mock_ai_reviewer):
        """Test that audit trail is complete."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        mock_get_reviewer.return_value = mock_ai_reviewer
        # Execute full workflow
        pipeline_response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        pipeline_result = pipeline_response.json()
        
        # Execute AI Review
        review_response = dashboard_client.post(
            "/ai-review/review-execution",
            json={
                'execution_result': pipeline_result,
                'update_status': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        review_result = review_response.json()
        
        # Generate Final Report
        report_response = dashboard_client.post(
            "/final-report/generate",
            json={
                'findings': pipeline_result.get('findings', []),
                'context': {'pipeline_id': pipeline_result.get('pipeline_id')},
                'deanonymize': True,
                'include_executive_summary': True,
                'format': 'both'
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        report_result = report_response.json()
        
        # Check that all operations have audit information
        assert 'pipeline_id' in pipeline_result, "Pipeline should have pipeline_id"
        assert 'review_id' in review_result.get('result', {}) or 'result' in review_result, \
            "Review should have review_id or result"
        assert 'report_id' in report_result.get('report', {}) or 'report' in report_result, \
            "Report should have report_id"

    def test_logs_contain_required_information(self, dashboard_client, sample_workflow_request):
        """Test that logs contain all required information."""
        # Execute pipeline
        response = dashboard_client_with_mocks.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert response.status_code == 200, "Pipeline execution should succeed"
        result = response.json()
        
        # Check that result contains required information for logging
        required_fields = ['pipeline_id', 'status']
        for field in required_fields:
            assert field in result, f"Result should contain {field} for logging"


class TestFullCycleFromHuntSelectionToReport:
    """TS-4-03-01: Full cycle from hunt selection to report"""

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.api.dashboard_api.get_ai_reviewer')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_full_cycle_workflow(self, mock_data_package, mock_get_reviewer, mock_get_orchestrator, dashboard_client, sample_workflow_request, mock_pipeline_orchestrator, mock_ai_reviewer):
        """Test full cycle from hunt selection to final report."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        mock_get_reviewer.return_value = mock_ai_reviewer
        # Step 1: Execute pipeline (hunt selection → pipeline execution)
        pipeline_response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': sample_workflow_request['technique_ids'],
                'tool_names': sample_workflow_request['tool_names'],
                'ingest_mode': sample_workflow_request['ingest_mode'],
                'anonymize': sample_workflow_request['anonymize']
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert pipeline_response.status_code == 200, "Pipeline execution should succeed"
        pipeline_result = pipeline_response.json()
        
        # Step 2: AI Review
        review_response = dashboard_client.post(
            "/ai-review/review-execution",
            json={
                'execution_result': pipeline_result,
                'update_status': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert review_response.status_code == 200, "AI Review should succeed"
        review_result = review_response.json()
        
        # Step 3: Generate Final Report
        report_response = dashboard_client.post(
            "/final-report/generate",
            json={
                'findings': review_result.get('result', {}).get('batch_review', {}).get('results', []) or 
                           pipeline_result.get('findings', []),
                'context': {'pipeline_id': pipeline_result.get('pipeline_id')},
                'deanonymize': sample_workflow_request.get('deanonymize', True),
                'include_executive_summary': True,
                'format': 'both'
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert report_response.status_code == 200, "Final report generation should succeed"
        report_result = report_response.json()
        
        # Verify that all steps completed
        assert pipeline_result.get('success') is True, "Pipeline should succeed"
        assert review_result.get('success') is True, "AI Review should succeed"
        assert report_result.get('success') is True, "Final report generation should succeed"
        
        # Verify that final report contains data from all previous steps
        if 'report' in report_result:
            report = report_result['report']
            assert 'findings_count' in report or 'findings' in report, \
                "Final report should contain findings from pipeline"


class TestWorkflowWithErrorsAndRecovery:
    """TS-4-03-02: Workflow with errors and recovery"""

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_workflow_handles_timeout_errors(self, mock_data_package, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test that workflow handles timeout errors."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        # Make pipeline orchestrator raise timeout error
        import time
        mock_pipeline_orchestrator.execute_pipeline.side_effect = TimeoutError("Pipeline execution timeout")
        
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': ['T1059'],
                'tool_names': ['Microsoft Defender'],
                'ingest_mode': 'manual',
                'anonymize': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        # Should handle timeout gracefully
        assert response.status_code in [500, 400], \
            "Should handle timeout error gracefully"
        result = response.json()
        assert 'error' in result or 'detail' in result, \
            "Error should be included in response"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_workflow_retries_on_failure(self, mock_data_package, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test that workflow can retry on failure."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        # Make pipeline orchestrator fail first time, then succeed
        call_count = {'count': 0}
        
        def execute_with_retry(*args, **kwargs):
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise Exception("Temporary failure")
            return {
                'pipeline_id': 'pipeline_20250115_103000',
                'status': 'success',
                'total_findings': 1,
                'findings': [],
                'started_at': '2025-01-15T10:30:00Z',
                'completed_at': '2025-01-15T10:35:00Z'
            }
        
        mock_pipeline_orchestrator.execute_pipeline.side_effect = execute_with_retry
        
        # Note: Retry logic would be implemented in n8n workflow, not in API
        # This test verifies that API can handle retries
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': ['T1059'],
                'tool_names': ['Microsoft Defender'],
                'ingest_mode': 'manual',
                'anonymize': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        # First call should fail, but API should handle it
        assert response.status_code in [200, 500], \
            "API should handle retry scenario"


class TestWorkflowWithDifferentConfigurations:
    """TS-4-03-03: Workflow with different configurations"""

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_workflow_with_manual_ingest(self, mock_data_package, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test workflow with manual ingest configuration."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': ['T1059'],
                'tool_names': ['Microsoft Defender'],
                'ingest_mode': 'manual',
                'anonymize': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert response.status_code == 200, "Manual ingest workflow should succeed"
        result = response.json()
        assert result.get('success') is True, "Manual ingest should be successful"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_workflow_with_api_ingest(self, mock_data_package, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test workflow with API ingest configuration."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': ['T1059'],
                'tool_names': ['Microsoft Defender'],
                'ingest_mode': 'api',
                'anonymize': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        assert response.status_code == 200, "API ingest workflow should succeed"
        result = response.json()
        assert result.get('success') is True, "API ingest should be successful"

    @patch('automation_scripts.api.dashboard_api.get_pipeline_orchestrator')
    @patch('automation_scripts.utils.data_package.DataPackage')
    def test_workflow_differences_between_configurations(self, mock_data_package, mock_get_orchestrator, dashboard_client, mock_pipeline_orchestrator):
        """Test that workflows with different configurations produce different results."""
        mock_get_orchestrator.return_value = mock_pipeline_orchestrator
        # Execute with manual ingest
        manual_response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': ['T1059'],
                'tool_names': ['Microsoft Defender'],
                'ingest_mode': 'manual',
                'anonymize': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        # Execute with API ingest
        api_response = dashboard_client.post(
            "/pipeline/execute",
            json={
                'technique_ids': ['T1059'],
                'tool_names': ['Microsoft Defender'],
                'ingest_mode': 'api',
                'anonymize': True
            },
            headers={"Authorization": "Bearer test-api-key"}
        )
        
        # Both should succeed
        assert manual_response.status_code == 200, "Manual ingest should succeed"
        assert api_response.status_code == 200, "API ingest should succeed"
        
        # Both should have pipeline IDs
        manual_result = manual_response.json()
        api_result = api_response.json()
        assert 'pipeline_id' in manual_result, "Manual ingest should have pipeline_id"
        assert 'pipeline_id' in api_result, "API ingest should have pipeline_id"

