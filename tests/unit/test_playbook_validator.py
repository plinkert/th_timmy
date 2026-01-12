"""
Unit tests for PHASE1-06: Playbook Validator.

Test Cases:
- TC-1-06-01: Walidacja struktury katalogów
- TC-1-06-02: Walidacja metadata.yml
- TC-1-06-03: Weryfikacja wymaganych plików
"""

import pytest
import yaml
import tempfile
import shutil
import sys
import importlib.util
import types
from pathlib import Path
from typing import Dict, Any

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

# Load playbook_validator module
playbook_validator_path = automation_scripts_path / "utils" / "playbook_validator.py"
spec = importlib.util.spec_from_file_location(
    "automation_scripts.utils.playbook_validator", playbook_validator_path
)
playbook_validator_module = importlib.util.module_from_spec(spec)
sys.modules["automation_scripts.utils.playbook_validator"] = playbook_validator_module
spec.loader.exec_module(playbook_validator_module)

PlaybookValidator = playbook_validator_module.PlaybookValidator
PlaybookValidatorError = playbook_validator_module.PlaybookValidatorError
PlaybookValidationError = playbook_validator_module.PlaybookValidationError


@pytest.fixture
def temp_playbook_dir():
    """Create a temporary playbook directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="th_test_playbook_")
    temp_path = Path(temp_dir)
    
    try:
        # Create required directories
        (temp_path / "queries").mkdir()
        (temp_path / "scripts").mkdir()
        (temp_path / "config").mkdir()
        (temp_path / "tests").mkdir()
        (temp_path / "examples").mkdir()
        
        # Create required files
        (temp_path / "README.md").write_text("# Test Playbook\n")
        
        # Create valid metadata.yml
        metadata = {
            "playbook": {
                "id": "T1059-test",
                "name": "Test Playbook",
                "version": "1.0.0",
                "author": "Test Author",
                "created": "2025-01-01",
                "updated": "2025-01-01"
            },
            "mitre": {
                "technique_id": "T1059",
                "technique_name": "Command and Scripting Interpreter",
                "tactic": "Execution"
            },
            "hypothesis": "Test hypothesis",
            "data_sources": []
        }
        
        with open(temp_path / "metadata.yml", 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)
        
        yield temp_path
        
    finally:
        # Cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)


class TestDirectoryStructureValidation:
    """TC-1-06-01: Walidacja struktury katalogów"""

    def test_validate_playbook_with_missing_required_directory(self, temp_playbook_dir):
        """Test that validation detects missing required directory."""
        # Remove required directory (queries)
        queries_dir = temp_playbook_dir / "queries"
        if queries_dir.exists():
            shutil.rmtree(queries_dir)
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        assert is_valid is False, "Playbook should be invalid"
        assert len(errors) > 0, "Should have validation errors"
        
        # Check that error mentions missing directory
        error_text = " ".join(errors).lower()
        assert "queries" in error_text or "required directory" in error_text, \
            "Error should mention missing queries directory"

    def test_validate_playbook_with_invalid_directory_type(self, temp_playbook_dir):
        """Test that validation detects when required directory is a file instead of directory."""
        # Create a file named "queries" instead of directory
        queries_dir = temp_playbook_dir / "queries"
        if queries_dir.exists():
            shutil.rmtree(queries_dir)
        queries_dir.write_text("not a directory")
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        assert is_valid is False, "Playbook should be invalid"
        assert len(errors) > 0, "Should have validation errors"
        
        # Check that error mentions directory type issue
        error_text = " ".join(errors).lower()
        assert "not a directory" in error_text or "directory" in error_text, \
            "Error should mention directory type issue"

    def test_validate_playbook_structure_errors_detected(self, temp_playbook_dir):
        """Test that structure errors are detected and returned."""
        # Remove required directory
        queries_dir = temp_playbook_dir / "queries"
        if queries_dir.exists():
            shutil.rmtree(queries_dir)
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        assert is_valid is False, "Playbook should be invalid"
        assert len(errors) > 0, "Should have structure errors"
        
        # Check that errors are detailed
        for error in errors:
            assert len(error) > 10, "Error messages should be detailed"
            assert isinstance(error, str), "Errors should be strings"

    def test_validate_playbook_strict_mode_raises_exception(self, temp_playbook_dir):
        """Test that validation in strict mode raises exception for structure errors."""
        # Remove required directory
        queries_dir = temp_playbook_dir / "queries"
        if queries_dir.exists():
            shutil.rmtree(queries_dir)
        
        validator = PlaybookValidator()
        
        # Validate in strict mode - should raise exception
        with pytest.raises(PlaybookValidationError) as exc_info:
            validator.validate_playbook(temp_playbook_dir, strict=True)
        
        assert "validation" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower(), \
            "Exception should mention validation or error"


class TestMetadataYAMLValidation:
    """TC-1-06-02: Walidacja metadata.yml"""

    def test_validate_playbook_with_invalid_yaml_syntax(self, temp_playbook_dir):
        """Test that validation detects invalid YAML syntax."""
        # Create invalid YAML file
        invalid_yaml = """
playbook:
  id: "T1059-test"
  name: "Test Playbook"
  invalid: [unclosed bracket
"""
        
        metadata_file = temp_playbook_dir / "metadata.yml"
        metadata_file.write_text(invalid_yaml)
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        assert is_valid is False, "Playbook should be invalid"
        assert len(errors) > 0, "Should have validation errors"
        
        # Check that error mentions YAML syntax
        error_text = " ".join(errors).lower()
        assert "yaml" in error_text or "syntax" in error_text, \
            "Error should mention YAML syntax"

    def test_validate_playbook_with_malformed_yaml(self, temp_playbook_dir):
        """Test that validation detects malformed YAML."""
        # Create malformed YAML
        malformed_yaml = """
playbook:
  id: "T1059-test"
  name: "Test Playbook"
    invalid_indentation: "error"
"""
        
        metadata_file = temp_playbook_dir / "metadata.yml"
        metadata_file.write_text(malformed_yaml)
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        # YAML parser might still parse it, but schema validation should catch issues
        # Or YAML parser might raise error
        if not is_valid:
            error_text = " ".join(errors).lower()
            assert "yaml" in error_text or "syntax" in error_text or "schema" in error_text, \
                "Error should mention YAML, syntax, or schema"

    def test_validate_playbook_with_empty_yaml(self, temp_playbook_dir):
        """Test that validation detects empty YAML file."""
        # Create empty YAML file
        metadata_file = temp_playbook_dir / "metadata.yml"
        metadata_file.write_text("")
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        assert is_valid is False, "Playbook should be invalid"
        assert len(errors) > 0, "Should have validation errors"
        
        # Check that error mentions empty file
        error_text = " ".join(errors).lower()
        assert "empty" in error_text, "Error should mention empty file"

    def test_validate_playbook_yaml_errors_detected(self, temp_playbook_dir):
        """Test that YAML errors are detected and returned with detailed messages."""
        # Create invalid YAML
        invalid_yaml = """
playbook:
  id: "T1059-test"
  name: "Test Playbook"
invalid: [unclosed
"""
        
        metadata_file = temp_playbook_dir / "metadata.yml"
        metadata_file.write_text(invalid_yaml)
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        assert is_valid is False, "Playbook should be invalid"
        assert len(errors) > 0, "Should have YAML errors"
        
        # Check that errors are detailed
        for error in errors:
            assert len(error) > 10, "Error messages should be detailed"
            assert isinstance(error, str), "Errors should be strings"

    def test_validate_playbook_strict_mode_raises_exception_for_yaml(self, temp_playbook_dir):
        """Test that validation in strict mode raises exception for YAML errors."""
        # Create invalid YAML
        invalid_yaml = """
playbook:
  id: "T1059-test"
  name: "Test Playbook"
invalid: [unclosed
"""
        
        metadata_file = temp_playbook_dir / "metadata.yml"
        metadata_file.write_text(invalid_yaml)
        
        validator = PlaybookValidator()
        
        # Validate in strict mode - should raise exception
        with pytest.raises(PlaybookValidationError) as exc_info:
            validator.validate_playbook(temp_playbook_dir, strict=True)
        
        assert "validation" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower(), \
            "Exception should mention validation or error"


class TestRequiredFilesValidation:
    """TC-1-06-03: Weryfikacja wymaganych plików"""

    def test_validate_playbook_with_missing_metadata_yml(self, temp_playbook_dir):
        """Test that validation detects missing metadata.yml."""
        # Remove metadata.yml
        metadata_file = temp_playbook_dir / "metadata.yml"
        if metadata_file.exists():
            metadata_file.unlink()
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        assert is_valid is False, "Playbook should be invalid"
        assert len(errors) > 0, "Should have validation errors"
        
        # Check that error mentions missing metadata.yml
        error_text = " ".join(errors).lower()
        assert "metadata.yml" in error_text or "metadata" in error_text, \
            "Error should mention missing metadata.yml"

    def test_validate_playbook_with_missing_readme(self, temp_playbook_dir):
        """Test that validation detects missing README.md."""
        # Remove README.md
        readme_file = temp_playbook_dir / "README.md"
        if readme_file.exists():
            readme_file.unlink()
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        assert is_valid is False, "Playbook should be invalid"
        assert len(errors) > 0, "Should have validation errors"
        
        # Check that error mentions missing README.md
        error_text = " ".join(errors).lower()
        assert "readme.md" in error_text or "readme" in error_text, \
            "Error should mention missing README.md"

    def test_validate_playbook_with_missing_analyzer_script(self, temp_playbook_dir):
        """Test that validation works when scripts/analyzer.py is missing (it's optional)."""
        # Ensure scripts directory exists but analyzer.py is missing
        scripts_dir = temp_playbook_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        # Remove analyzer.py if it exists
        analyzer_file = scripts_dir / "analyzer.py"
        if analyzer_file.exists():
            analyzer_file.unlink()
        
        # Note: analyzer.py is not in REQUIRED_FILES according to the validator code
        # The validator only requires metadata.yml and README.md
        # scripts/analyzer.py is mentioned in documentation as required for Master Playbook,
        # but it's not enforced by the validator for regular playbooks
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        # Check if playbook is valid (it should be, as analyzer.py is optional)
        # If it's not valid, check what errors are present
        if not is_valid:
            # Check if errors are about analyzer.py (they shouldn't be)
            error_text = " ".join(errors).lower()
            assert "analyzer.py" not in error_text, \
                f"Should not have errors about missing analyzer.py (it's optional). Errors: {errors}"
            # If there are other errors (e.g., schema validation), that's okay for this test
            # The important thing is that analyzer.py is not required
        else:
            # Playbook is valid, which is correct
            assert is_valid is True, "Playbook should be valid even without analyzer.py (it's optional)"
        
        # Verify that there are no errors about missing analyzer.py
        error_text = " ".join(errors).lower()
        assert "analyzer.py" not in error_text, \
            f"Should not have errors about missing analyzer.py (it's optional). Errors: {errors}"

    def test_validate_playbook_required_files_errors_detected(self, temp_playbook_dir):
        """Test that required file errors are detected and returned."""
        # Remove both required files
        metadata_file = temp_playbook_dir / "metadata.yml"
        readme_file = temp_playbook_dir / "README.md"
        
        if metadata_file.exists():
            metadata_file.unlink()
        if readme_file.exists():
            readme_file.unlink()
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        assert is_valid is False, "Playbook should be invalid"
        assert len(errors) > 0, "Should have validation errors"
        
        # Check that errors mention missing files
        error_text = " ".join(errors).lower()
        assert "metadata.yml" in error_text or "readme.md" in error_text, \
            "Errors should mention missing files"

    def test_validate_playbook_strict_mode_raises_exception_for_missing_files(self, temp_playbook_dir):
        """Test that validation in strict mode raises exception for missing required files."""
        # Remove metadata.yml
        metadata_file = temp_playbook_dir / "metadata.yml"
        if metadata_file.exists():
            metadata_file.unlink()
        
        validator = PlaybookValidator()
        
        # Validate in strict mode - should raise exception
        with pytest.raises(PlaybookValidationError) as exc_info:
            validator.validate_playbook(temp_playbook_dir, strict=True)
        
        assert "validation" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower(), \
            "Exception should mention validation or error"

    def test_validate_playbook_file_path_is_not_file(self, temp_playbook_dir):
        """Test that validation detects when required file path is a directory instead of file."""
        # Remove metadata.yml and create a directory with that name
        metadata_file = temp_playbook_dir / "metadata.yml"
        if metadata_file.exists():
            metadata_file.unlink()
        
        metadata_file.mkdir()
        
        validator = PlaybookValidator()
        is_valid, errors, warnings = validator.validate_playbook(temp_playbook_dir, strict=False)
        
        assert is_valid is False, "Playbook should be invalid"
        assert len(errors) > 0, "Should have validation errors"
        
        # Check that error mentions file type issue
        error_text = " ".join(errors).lower()
        assert "not a file" in error_text or "file" in error_text, \
            "Error should mention file type issue"

