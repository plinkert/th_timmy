"""
Unit tests for PHASE1-04: n8n Hunt Selection Form.

Test Cases:
- TC-1-04-01: Wybór huntów (checkboxy)
- TC-1-04-02: Wybór źródła danych
- TC-1-04-03: Wybór narzędzi
- TC-1-04-04: Generowanie zapytań w formularzu
- TC-1-04-05: Wyświetlanie zapytań do copy-paste
"""

import pytest
from pathlib import Path


class TestHuntSelection:
    """TC-1-04-01: Wybór huntów (checkboxy)"""

    def _setup_query_generator(self, dashboard_client, playbooks_dir):
        """Helper to setup query generator with custom playbooks directory."""
        dashboard_api_module = dashboard_client._dashboard_api_module
        import sys
        import importlib.util
        import types
        
        automation_scripts_path = Path(__file__).parent.parent.parent / "automation-scripts"
        sys.path.insert(0, str(automation_scripts_path))
        
        if "automation_scripts.utils" not in sys.modules:
            sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
            sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
        
        query_generator_path = automation_scripts_path / "utils" / "query_generator.py"
        spec = importlib.util.spec_from_file_location(
            "automation_scripts.utils.query_generator", query_generator_path
        )
        query_generator_module = importlib.util.module_from_spec(spec)
        sys.modules["automation_scripts.utils.query_generator"] = query_generator_module
        spec.loader.exec_module(query_generator_module)
        
        QueryGenerator = query_generator_module.QueryGenerator
        dashboard_api_module.get_query_generator = lambda: QueryGenerator(playbooks_dir=playbooks_dir)

    def test_get_available_playbooks(self, dashboard_client, temp_playbooks_with_t1059):
        """Test that playbooks endpoint returns available playbooks."""
        self._setup_query_generator(dashboard_client, temp_playbooks_with_t1059)
        
        response = dashboard_client.get("/query-generator/playbooks")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "success" in data, "Response should contain 'success' field"
        assert data["success"] is True, "Success should be True"
        assert "playbooks" in data, "Response should contain 'playbooks' field"
        assert isinstance(data["playbooks"], list), "Playbooks should be a list"
        assert "total" in data, "Response should contain 'total' field"

    def test_select_multiple_hunts(self, dashboard_client, temp_playbooks_with_multiple):
        """Test that multiple hunts can be selected and passed to query generation."""
        self._setup_query_generator(dashboard_client, temp_playbooks_with_multiple)
        
        # Select multiple hunts (T1059, T1047, T1071)
        selected_techniques = ["T1059", "T1047", "T1071"]
        
        # Generate queries with multiple hunts
        generate_response = dashboard_client.post(
            "/query-generator/generate",
            json={
                "technique_ids": selected_techniques,
                "tool_names": ["Microsoft Defender for Endpoint"],
                "mode": "manual",
                "parameters": {"time_range": "7d"}
            }
        )
        
        assert generate_response.status_code == 200, \
            f"Expected 200, got {generate_response.status_code}: {generate_response.text}"
        
        data = generate_response.json()
        assert "queries" in data, "Response should contain 'queries' field"
        
        # Verify all selected hunts are in the response
        queries = data.get("queries", {})
        assert len(queries) > 0, "Should have at least some queries generated"
        
        # Verify techniques are in response
        assert "techniques" in data, "Response should contain 'techniques' field"
        techniques_in_response = data.get("techniques", [])
        for technique_id in selected_techniques:
            assert technique_id in techniques_in_response, \
                f"Technique {technique_id} should be in response"


class TestDataSourceSelection:
    """TC-1-04-02: Wybór źródła danych"""

    def _setup_query_generator(self, dashboard_client, playbooks_dir):
        """Helper to setup query generator with custom playbooks directory."""
        dashboard_api_module = dashboard_client._dashboard_api_module
        import sys
        import importlib.util
        import types
        
        automation_scripts_path = Path(__file__).parent.parent.parent / "automation-scripts"
        sys.path.insert(0, str(automation_scripts_path))
        
        if "automation_scripts.utils" not in sys.modules:
            sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
            sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
        
        query_generator_path = automation_scripts_path / "utils" / "query_generator.py"
        spec = importlib.util.spec_from_file_location(
            "automation_scripts.utils.query_generator", query_generator_path
        )
        query_generator_module = importlib.util.module_from_spec(spec)
        sys.modules["automation_scripts.utils.query_generator"] = query_generator_module
        spec.loader.exec_module(query_generator_module)
        
        QueryGenerator = query_generator_module.QueryGenerator
        dashboard_api_module.get_query_generator = lambda: QueryGenerator(playbooks_dir=playbooks_dir)

    def test_select_manual_mode(self, dashboard_client, temp_playbooks_with_t1059):
        """Test that manual mode can be selected and saved."""
        self._setup_query_generator(dashboard_client, temp_playbooks_with_t1059)
        
        response = dashboard_client.post(
            "/query-generator/generate",
            json={
                "technique_ids": ["T1059"],
                "tool_names": ["Microsoft Defender for Endpoint"],
                "mode": "manual",
                "parameters": {"time_range": "7d"}
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "mode" in data, "Response should contain 'mode' field"
        assert data["mode"] == "manual", "Mode should be 'manual'"
        assert "queries" in data, "Response should contain 'queries' field"

    def test_select_api_mode(self, dashboard_client, temp_playbooks_with_t1059):
        """Test that API mode can be selected and saved."""
        self._setup_query_generator(dashboard_client, temp_playbooks_with_t1059)
        
        response = dashboard_client.post(
            "/query-generator/generate",
            json={
                "technique_ids": ["T1059"],
                "tool_names": ["Microsoft Defender for Endpoint"],
                "mode": "api",
                "parameters": {"time_range": "7d"}
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "mode" in data, "Response should contain 'mode' field"
        assert data["mode"] == "api", "Mode should be 'api'"
        assert "queries" in data, "Response should contain 'queries' field"


class TestToolSelection:
    """TC-1-04-03: Wybór narzędzi"""

    def _setup_query_generator(self, dashboard_client, playbooks_dir):
        """Helper to setup query generator with custom playbooks directory."""
        dashboard_api_module = dashboard_client._dashboard_api_module
        import sys
        import importlib.util
        import types
        
        automation_scripts_path = Path(__file__).parent.parent.parent / "automation-scripts"
        sys.path.insert(0, str(automation_scripts_path))
        
        if "automation_scripts.utils" not in sys.modules:
            sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
            sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
        
        query_generator_path = automation_scripts_path / "utils" / "query_generator.py"
        spec = importlib.util.spec_from_file_location(
            "automation_scripts.utils.query_generator", query_generator_path
        )
        query_generator_module = importlib.util.module_from_spec(spec)
        sys.modules["automation_scripts.utils.query_generator"] = query_generator_module
        spec.loader.exec_module(query_generator_module)
        
        QueryGenerator = query_generator_module.QueryGenerator
        dashboard_api_module.get_query_generator = lambda: QueryGenerator(playbooks_dir=playbooks_dir)

    def test_get_available_tools(self, dashboard_client, temp_playbooks_with_t1059):
        """Test that tools endpoint returns available tools."""
        self._setup_query_generator(dashboard_client, temp_playbooks_with_t1059)
        
        response = dashboard_client.get("/query-generator/tools")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "success" in data, "Response should contain 'success' field"
        assert data["success"] is True, "Success should be True"
        assert "tools" in data, "Response should contain 'tools' field"
        assert isinstance(data["tools"], list), "Tools should be a list"
        assert len(data["tools"]) > 0, "Should have at least one tool"

    def test_select_multiple_tools(self, dashboard_client, temp_playbooks_with_t1059):
        """Test that multiple tools can be selected and passed to query generation."""
        self._setup_query_generator(dashboard_client, temp_playbooks_with_t1059)
        
        # Select multiple tools (MDE, Sentinel)
        selected_tools = ["Microsoft Defender for Endpoint", "Microsoft Sentinel"]
        
        response = dashboard_client.post(
            "/query-generator/generate",
            json={
                "technique_ids": ["T1059"],
                "tool_names": selected_tools,
                "mode": "manual",
                "parameters": {"time_range": "7d"}
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "queries" in data, "Response should contain 'queries' field"
        assert "tools" in data, "Response should contain 'tools' field"
        
        # Verify tools are in response
        tools_in_response = data.get("tools", [])
        for tool in selected_tools:
            assert tool in tools_in_response, f"Tool {tool} should be in response"


class TestQueryGenerationInForm:
    """TC-1-04-04: Generowanie zapytań w formularzu"""

    def _setup_query_generator(self, dashboard_client, playbooks_dir):
        """Helper to setup query generator with custom playbooks directory."""
        dashboard_api_module = dashboard_client._dashboard_api_module
        import sys
        import importlib.util
        import types
        from pathlib import Path
        
        automation_scripts_path = Path(__file__).parent.parent.parent / "automation-scripts"
        sys.path.insert(0, str(automation_scripts_path))
        
        if "automation_scripts.utils" not in sys.modules:
            sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
            sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
        
        query_generator_path = automation_scripts_path / "utils" / "query_generator.py"
        spec = importlib.util.spec_from_file_location(
            "automation_scripts.utils.query_generator", query_generator_path
        )
        query_generator_module = importlib.util.module_from_spec(spec)
        sys.modules["automation_scripts.utils.query_generator"] = query_generator_module
        spec.loader.exec_module(query_generator_module)
        
        QueryGenerator = query_generator_module.QueryGenerator
        dashboard_api_module.get_query_generator = lambda: QueryGenerator(playbooks_dir=playbooks_dir)

    def test_generate_queries_with_form_data(self, dashboard_client, temp_playbooks_with_t1059):
        """Test that queries are generated when form is filled and submitted."""
        self._setup_query_generator(dashboard_client, temp_playbooks_with_t1059)
        
        response = dashboard_client.post(
            "/query-generator/generate",
            json={
                "technique_ids": ["T1059"],
                "tool_names": ["Microsoft Defender for Endpoint"],
                "mode": "manual",
                "parameters": {
                    "time_range": "7d",
                    "severity": "high"
                }
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "success" in data, "Response should contain 'success' field"
        assert data["success"] is True, "Success should be True"
        assert "queries" in data, "Response should contain 'queries' field"
        assert isinstance(data["queries"], dict), "Queries should be a dictionary"
        assert len(data["queries"]) > 0, "Should have at least one query generated"

    def test_queries_visible_in_response(self, dashboard_client, temp_playbooks_with_t1059):
        """Test that generated queries are visible in the response."""
        self._setup_query_generator(dashboard_client, temp_playbooks_with_t1059)
        
        response = dashboard_client.post(
            "/query-generator/generate",
            json={
                "technique_ids": ["T1059"],
                "tool_names": ["Microsoft Defender for Endpoint"],
                "mode": "manual",
                "parameters": {"time_range": "7d"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        queries = data.get("queries", {})
        assert len(queries) > 0, "Should have queries in response"
        
        # Verify query structure
        for technique_id, technique_data in queries.items():
            assert "tools" in technique_data, f"Technique {technique_id} should have 'tools' field"
            tools = technique_data.get("tools", {})
            assert len(tools) > 0, f"Technique {technique_id} should have at least one tool query"


class TestQueryDisplayAndCopyPaste:
    """TC-1-04-05: Wyświetlanie zapytań do copy-paste"""

    def _setup_query_generator(self, dashboard_client, playbooks_dir):
        """Helper to setup query generator with custom playbooks directory."""
        dashboard_api_module = dashboard_client._dashboard_api_module
        import sys
        import importlib.util
        import types
        from pathlib import Path
        
        automation_scripts_path = Path(__file__).parent.parent.parent / "automation-scripts"
        sys.path.insert(0, str(automation_scripts_path))
        
        if "automation_scripts.utils" not in sys.modules:
            sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
            sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
        
        query_generator_path = automation_scripts_path / "utils" / "query_generator.py"
        spec = importlib.util.spec_from_file_location(
            "automation_scripts.utils.query_generator", query_generator_path
        )
        query_generator_module = importlib.util.module_from_spec(spec)
        sys.modules["automation_scripts.utils.query_generator"] = query_generator_module
        spec.loader.exec_module(query_generator_module)
        
        QueryGenerator = query_generator_module.QueryGenerator
        dashboard_api_module.get_query_generator = lambda: QueryGenerator(playbooks_dir=playbooks_dir)

    def test_queries_are_displayed_in_readable_format(self, dashboard_client, temp_playbooks_with_t1059):
        """Test that queries are displayed in a readable format."""
        self._setup_query_generator(dashboard_client, temp_playbooks_with_t1059)
        
        response = dashboard_client.post(
            "/query-generator/generate",
            json={
                "technique_ids": ["T1059"],
                "tool_names": ["Microsoft Defender for Endpoint"],
                "mode": "manual",
                "parameters": {"time_range": "7d"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        queries = data.get("queries", {})
        assert len(queries) > 0, "Should have queries"
        
        # Verify query format is readable (string, not empty)
        for technique_id, technique_data in queries.items():
            tools = technique_data.get("tools", {})
            for tool_name, query_data in tools.items():
                assert "query" in query_data, f"Query data for {tool_name} should contain 'query' field"
                query_text = query_data.get("query", "")
                assert isinstance(query_text, str), "Query should be a string"
                assert len(query_text) > 0, "Query should not be empty"
                assert "\n" in query_text or len(query_text) > 50, \
                    "Query should be substantial and readable"

    def test_queries_are_ready_for_copy_paste(self, dashboard_client, temp_playbooks_with_t1059):
        """Test that queries are ready for copy-paste (no placeholders, proper format)."""
        self._setup_query_generator(dashboard_client, temp_playbooks_with_t1059)
        
        response = dashboard_client.post(
            "/query-generator/generate",
            json={
                "technique_ids": ["T1059"],
                "tool_names": ["Microsoft Defender for Endpoint"],
                "mode": "manual",
                "parameters": {"time_range": "7d"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        queries = data.get("queries", {})
        assert len(queries) > 0, "Should have queries"
        
        # Verify queries are ready for copy-paste
        for technique_id, technique_data in queries.items():
            tools = technique_data.get("tools", {})
            for tool_name, query_data in tools.items():
                query_text = query_data.get("query", "")
                
                # Query should not contain unresolved placeholders (for manual mode)
                # Note: API mode may have placeholders, but manual mode should not
                # Manual mode queries should have time_range already replaced
                assert "{{{" not in query_text or "{{{{" not in query_text, \
                    f"Query for {tool_name} should not contain unresolved placeholders"
                
                # Query should be substantial
                assert len(query_text) > 20, f"Query for {tool_name} should be substantial"

    def test_query_has_instructions(self, dashboard_client, temp_playbooks_with_t1059):
        """Test that queries have instructions for use."""
        self._setup_query_generator(dashboard_client, temp_playbooks_with_t1059)
        
        response = dashboard_client.post(
            "/query-generator/generate",
            json={
                "technique_ids": ["T1059"],
                "tool_names": ["Microsoft Defender for Endpoint"],
                "mode": "manual",
                "parameters": {"time_range": "7d"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        queries = data.get("queries", {})
        assert len(queries) > 0, "Should have queries"
        
        # Verify queries have instructions or description
        for technique_id, technique_data in queries.items():
            tools = technique_data.get("tools", {})
            for tool_name, query_data in tools.items():
                # Should have either instructions or description
                has_instructions = "instructions" in query_data and query_data["instructions"]
                has_description = "description" in query_data and query_data["description"]
                assert has_instructions or has_description, \
                    f"Query for {tool_name} should have instructions or description"

