"""
Unit tests for PHASE1-01: Playbook Structure validation.

Test Cases:
- TC-1-01-01: Walidacja struktury playbooka
- TC-1-01-02: Walidacja metadata.yml z zapytaniami
- TC-1-01-03: Format zapytań manual
- TC-1-01-04: Format zapytań API
"""

import pytest
import yaml
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List


class TestPlaybookStructure:
    """TC-1-01-01: Walidacja struktury playbooka"""

    def test_playbook_has_required_files(self, temp_playbook_dir):
        """Test that playbook has all required files."""
        playbook_path = temp_playbook_dir
        
        # Required files
        required_files = [
            "README.md",
            "metadata.yml"
        ]
        
        for file_name in required_files:
            file_path = playbook_path / file_name
            assert file_path.exists(), f"Required file {file_name} not found"
            assert file_path.is_file(), f"{file_name} is not a file"

    def test_playbook_has_required_directories(self, temp_playbook_dir):
        """Test that playbook has all required directories."""
        playbook_path = temp_playbook_dir
        
        # Required directories (may be empty)
        required_dirs = [
            "queries",
            "scripts",
            "config",
            "tests",
            "examples"
        ]
        
        for dir_name in required_dirs:
            dir_path = playbook_path / dir_name
            assert dir_path.exists(), f"Required directory {dir_name} not found"
            assert dir_path.is_dir(), f"{dir_name} is not a directory"

    def test_playbook_structure_complete(self, temp_playbook_dir):
        """Test that playbook structure is complete."""
        playbook_path = temp_playbook_dir
        
        # Check all components
        assert (playbook_path / "README.md").exists(), "README.md missing"
        assert (playbook_path / "metadata.yml").exists(), "metadata.yml missing"
        assert (playbook_path / "queries").is_dir(), "queries directory missing"
        assert (playbook_path / "scripts").is_dir(), "scripts directory missing"
        assert (playbook_path / "config").is_dir(), "config directory missing"
        assert (playbook_path / "tests").is_dir(), "tests directory missing"
        assert (playbook_path / "examples").is_dir(), "examples directory missing"


class TestMetadataQueries:
    """TC-1-01-02: Walidacja metadata.yml z zapytaniami"""

    def test_metadata_has_data_sources_section(self, temp_playbook_dir):
        """Test that metadata.yml has data_sources section."""
        metadata_path = temp_playbook_dir / "metadata.yml"
        
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        assert "data_sources" in metadata, "data_sources section missing"
        assert isinstance(metadata["data_sources"], list), "data_sources must be a list"
        assert len(metadata["data_sources"]) > 0, "data_sources list is empty"

    def test_data_sources_have_queries(self, temp_playbook_dir):
        """Test that data_sources contain queries."""
        metadata_path = temp_playbook_dir / "metadata.yml"
        
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        data_sources = metadata.get("data_sources", [])
        
        # At least one data source should have queries
        has_queries = False
        for source in data_sources:
            if "queries" in source:
                has_queries = True
                break
        
        assert has_queries, "No data source has queries defined"

    def test_queries_defined_for_tools(self, temp_playbook_dir):
        """Test that queries are defined for each tool."""
        metadata_path = temp_playbook_dir / "metadata.yml"
        
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        data_sources = metadata.get("data_sources", [])
        
        # Check that each data source with queries has both manual and api
        for source in data_sources:
            if "queries" in source:
                queries = source["queries"]
                # At least one query type should be defined
                assert "manual" in queries or "api" in queries, \
                    f"Data source {source.get('name', 'unknown')} has queries but no manual or api defined"


class TestManualQueryFormat:
    """TC-1-01-03: Format zapytań manual"""

    def test_manual_queries_have_name(self, temp_playbook_dir):
        """Test that manual queries have 'name' field."""
        metadata_path = temp_playbook_dir / "metadata.yml"
        
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        data_sources = metadata.get("data_sources", [])
        
        for source in data_sources:
            if "queries" in source and "manual" in source["queries"]:
                manual_queries = source["queries"]["manual"]
                for query in manual_queries:
                    assert "name" in query, f"Manual query missing 'name' field in {source.get('name', 'unknown')}"
                    assert query["name"], "Query name cannot be empty"

    def test_manual_queries_have_parameters(self, temp_playbook_dir):
        """Test that manual queries have 'parameters' field."""
        metadata_path = temp_playbook_dir / "metadata.yml"
        
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        data_sources = metadata.get("data_sources", [])
        
        for source in data_sources:
            if "queries" in source and "manual" in source["queries"]:
                manual_queries = source["queries"]["manual"]
                for query in manual_queries:
                    assert "parameters" in query, \
                        f"Manual query '{query.get('name', 'unknown')}' missing 'parameters' field"
                    assert isinstance(query["parameters"], dict), \
                        f"Parameters must be a dictionary in query '{query.get('name', 'unknown')}'"

    def test_manual_queries_have_time_range(self, temp_playbook_dir):
        """Test that manual queries have 'time_range' in parameters."""
        metadata_path = temp_playbook_dir / "metadata.yml"
        
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        data_sources = metadata.get("data_sources", [])
        
        for source in data_sources:
            if "queries" in source and "manual" in source["queries"]:
                manual_queries = source["queries"]["manual"]
                for query in manual_queries:
                    if "parameters" in query:
                        assert "time_range" in query["parameters"], \
                            f"Manual query '{query.get('name', 'unknown')}' missing 'time_range' parameter"
                        assert query["parameters"]["time_range"], \
                            f"time_range cannot be empty in query '{query.get('name', 'unknown')}'"

    def test_manual_queries_have_file_reference(self, temp_playbook_dir):
        """Test that manual queries reference query files."""
        metadata_path = temp_playbook_dir / "metadata.yml"
        
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        data_sources = metadata.get("data_sources", [])
        
        for source in data_sources:
            if "queries" in source and "manual" in source["queries"]:
                manual_queries = source["queries"]["manual"]
                for query in manual_queries:
                    assert "file" in query, \
                        f"Manual query '{query.get('name', 'unknown')}' missing 'file' field"
                    # Check that file exists
                    file_path = temp_playbook_dir / query["file"]
                    assert file_path.exists(), \
                        f"Query file {query['file']} referenced in '{query.get('name', 'unknown')}' does not exist"


class TestAPIQueryFormat:
    """TC-1-01-04: Format zapytań API"""

    def test_api_queries_have_endpoint(self, temp_playbook_dir):
        """Test that API queries have 'api_endpoint' field."""
        metadata_path = temp_playbook_dir / "metadata.yml"
        
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        data_sources = metadata.get("data_sources", [])
        
        for source in data_sources:
            if "queries" in source and "api" in source["queries"]:
                api_queries = source["queries"]["api"]
                for query in api_queries:
                    assert "api_endpoint" in query, \
                        f"API query '{query.get('name', 'unknown')}' missing 'api_endpoint' field"
                    assert query["api_endpoint"], \
                        f"api_endpoint cannot be empty in query '{query.get('name', 'unknown')}'"

    def test_api_queries_have_authentication(self, temp_playbook_dir):
        """Test that API queries have 'api_authentication' field."""
        metadata_path = temp_playbook_dir / "metadata.yml"
        
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        data_sources = metadata.get("data_sources", [])
        
        for source in data_sources:
            if "queries" in source and "api" in source["queries"]:
                api_queries = source["queries"]["api"]
                for query in api_queries:
                    assert "api_authentication" in query, \
                        f"API query '{query.get('name', 'unknown')}' missing 'api_authentication' field"
                    assert query["api_authentication"], \
                        f"api_authentication cannot be empty in query '{query.get('name', 'unknown')}'"

    def test_api_queries_have_method(self, temp_playbook_dir):
        """Test that API queries have 'api_method' field."""
        metadata_path = temp_playbook_dir / "metadata.yml"
        
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        data_sources = metadata.get("data_sources", [])
        
        for source in data_sources:
            if "queries" in source and "api" in source["queries"]:
                api_queries = source["queries"]["api"]
                for query in api_queries:
                    assert "api_method" in query, \
                        f"API query '{query.get('name', 'unknown')}' missing 'api_method' field"
                    assert query["api_method"] in ["GET", "POST", "PUT", "DELETE"], \
                        f"api_method must be a valid HTTP method in query '{query.get('name', 'unknown')}'"

    def test_api_queries_have_file_reference(self, temp_playbook_dir):
        """Test that API queries reference query files."""
        metadata_path = temp_playbook_dir / "metadata.yml"
        
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        data_sources = metadata.get("data_sources", [])
        
        for source in data_sources:
            if "queries" in source and "api" in source["queries"]:
                api_queries = source["queries"]["api"]
                for query in api_queries:
                    assert "file" in query, \
                        f"API query '{query.get('name', 'unknown')}' missing 'file' field"
                    # Check that file exists
                    file_path = temp_playbook_dir / query["file"]
                    assert file_path.exists(), \
                        f"Query file {query['file']} referenced in '{query.get('name', 'unknown')}' does not exist"

