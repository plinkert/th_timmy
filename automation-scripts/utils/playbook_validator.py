"""
Playbook Validator - Validation of threat hunting playbooks.

This module provides functionality for validating playbook structure,
metadata.yml files, required files, and query syntax.
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import yaml
from jsonschema import validate, ValidationError, Draft7Validator

from pathlib import Path as PathType


class PlaybookValidatorError(Exception):
    """Base exception for playbook validator errors."""
    pass


class PlaybookValidationError(PlaybookValidatorError):
    """Exception raised when playbook validation fails."""
    pass


class PlaybookValidator:
    """
    Validator for threat hunting playbooks.
    
    Validates:
    - Directory structure
    - metadata.yml (YAML syntax, required fields, query format)
    - Required files presence
    - Query file syntax (basic checks)
    """
    
    REQUIRED_FILES = [
        "metadata.yml",
        "README.md"
    ]
    
    REQUIRED_DIRECTORIES = [
        "queries"
    ]
    
    OPTIONAL_DIRECTORIES = [
        "scripts",
        "config",
        "tests",
        "examples"
    ]
    
    QUERY_FILE_EXTENSIONS = {
        ".kql": "KQL",
        ".spl": "SPL",
        ".json": "JSON",
        ".txt": "TEXT"
    }
    
    def __init__(
        self,
        playbooks_dir: Optional[Union[str, PathType]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Playbook Validator.
        
        Args:
            playbooks_dir: Path to playbooks directory
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Determine playbooks directory
        if playbooks_dir:
            self.playbooks_dir = Path(playbooks_dir)
        else:
            project_root = Path(__file__).parent.parent.parent
            self.playbooks_dir = project_root / "playbooks"
        
        if not self.playbooks_dir.exists():
            self.logger.warning(f"Playbooks directory not found: {self.playbooks_dir}")
        
        # Load schema
        self._schema = self._load_schema()
        
        self.logger.info(f"PlaybookValidator initialized with playbooks_dir: {self.playbooks_dir}")
    
    @staticmethod
    def _load_schema() -> Dict[str, Any]:
        """Load JSON schema for validation."""
        schema_path = Path(__file__).parent.parent / "schemas" / "playbook_schema.json"
        
        if not schema_path.exists():
            raise PlaybookValidatorError(f"Schema file not found: {schema_path}")
        
        try:
            with open(schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise PlaybookValidatorError(f"Failed to load schema: {e}")
    
    def validate_playbook(
        self,
        playbook_path: Union[str, PathType],
        strict: bool = True
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a playbook.
        
        Args:
            playbook_path: Path to playbook directory
            strict: If True, raise exception on validation failure
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        
        Raises:
            PlaybookValidationError: If validation fails and strict=True
        """
        playbook_path = Path(playbook_path)
        
        if not playbook_path.exists():
            error_msg = f"Playbook directory not found: {playbook_path}"
            if strict:
                raise PlaybookValidationError(error_msg)
            return False, [error_msg], []
        
        if not playbook_path.is_dir():
            error_msg = f"Playbook path is not a directory: {playbook_path}"
            if strict:
                raise PlaybookValidationError(error_msg)
            return False, [error_msg], []
        
        errors = []
        warnings = []
        
        # Validate directory structure
        structure_errors, structure_warnings = self._validate_directory_structure(playbook_path)
        errors.extend(structure_errors)
        warnings.extend(structure_warnings)
        
        # Validate metadata.yml
        metadata_file = playbook_path / "metadata.yml"
        if metadata_file.exists():
            metadata_errors, metadata_warnings = self._validate_metadata(metadata_file)
            errors.extend(metadata_errors)
            warnings.extend(metadata_warnings)
        else:
            errors.append(f"Required file not found: metadata.yml")
        
        # Validate query files
        queries_dir = playbook_path / "queries"
        if queries_dir.exists():
            query_errors, query_warnings = self._validate_query_files(playbook_path, queries_dir)
            errors.extend(query_errors)
            warnings.extend(query_warnings)
        
        # Validate required files
        required_errors = self._validate_required_files(playbook_path)
        errors.extend(required_errors)
        
        is_valid = len(errors) == 0
        
        if not is_valid and strict:
            error_msg = f"Playbook validation failed with {len(errors)} error(s)"
            raise PlaybookValidationError(error_msg)
        
        return is_valid, errors, warnings
    
    def _validate_directory_structure(
        self,
        playbook_path: Path
    ) -> Tuple[List[str], List[str]]:
        """Validate playbook directory structure."""
        errors = []
        warnings = []
        
        # Check required directories
        for req_dir in self.REQUIRED_DIRECTORIES:
            dir_path = playbook_path / req_dir
            if not dir_path.exists():
                errors.append(f"Required directory not found: {req_dir}/")
            elif not dir_path.is_dir():
                errors.append(f"Required path is not a directory: {req_dir}/")
        
        # Check optional directories (warnings only)
        for opt_dir in self.OPTIONAL_DIRECTORIES:
            dir_path = playbook_path / opt_dir
            if dir_path.exists() and not dir_path.is_dir():
                warnings.append(f"Optional path is not a directory: {opt_dir}/")
        
        return errors, warnings
    
    def _validate_metadata(self, metadata_file: Path) -> Tuple[List[str], List[str]]:
        """Validate metadata.yml file."""
        errors = []
        warnings = []
        
        # Check YAML syntax
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML syntax in metadata.yml: {e}")
            return errors, warnings
        except Exception as e:
            errors.append(f"Failed to read metadata.yml: {e}")
            return errors, warnings
        
        if metadata is None:
            errors.append("metadata.yml is empty")
            return errors, warnings
        
        # Validate against JSON schema
        try:
            validate(instance=metadata, schema=self._schema)
        except ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
            if e.path:
                errors.append(f"  Path: {' -> '.join(str(p) for p in e.path)}")
        
        # Additional custom validations
        custom_errors, custom_warnings = self._validate_metadata_custom(metadata, metadata_file.parent)
        errors.extend(custom_errors)
        warnings.extend(custom_warnings)
        
        return errors, warnings
    
    def _validate_metadata_custom(
        self,
        metadata: Dict[str, Any],
        playbook_path: Path
    ) -> Tuple[List[str], List[str]]:
        """Custom validations for metadata."""
        errors = []
        warnings = []
        
        # Check playbook ID format
        playbook_info = metadata.get('playbook', {})
        playbook_id = playbook_info.get('id', '')
        if playbook_id and not re.match(r'^[A-Z0-9]+(-[a-z0-9-]+)*$', playbook_id):
            warnings.append(f"Playbook ID '{playbook_id}' does not follow recommended format (e.g., 'T1566-phishing')")
        
        # Check MITRE technique ID format
        mitre_info = metadata.get('mitre', {})
        technique_id = mitre_info.get('technique_id', '')
        if technique_id and not re.match(r'^T\d{4}(\.\d{3})?$', technique_id):
            errors.append(f"Invalid MITRE technique ID format: {technique_id}")
        
        # Validate query file references
        data_sources = metadata.get('data_sources', [])
        for source in data_sources:
            queries = source.get('queries', {})
            
            # Check manual queries
            for query in queries.get('manual', []):
                query_file = query.get('file', '')
                if query_file:
                    file_path = playbook_path / query_file
                    if not file_path.exists():
                        errors.append(f"Query file not found: {query_file}")
                    elif not file_path.is_file():
                        errors.append(f"Query file path is not a file: {query_file}")
            
            # Check API queries
            for query in queries.get('api', []):
                query_file = query.get('file', '')
                if query_file:
                    file_path = playbook_path / query_file
                    if not file_path.exists():
                        errors.append(f"Query file not found: {query_file}")
                    elif not file_path.is_file():
                        errors.append(f"Query file path is not a file: {query_file}")
                
                # Check API endpoint format
                api_endpoint = query.get('api_endpoint', '')
                if api_endpoint and not (api_endpoint.startswith('http://') or api_endpoint.startswith('https://')):
                    warnings.append(f"API endpoint does not start with http:// or https://: {api_endpoint}")
        
        return errors, warnings
    
    def _validate_query_files(
        self,
        playbook_path: Path,
        queries_dir: Path
    ) -> Tuple[List[str], List[str]]:
        """Validate query files."""
        errors = []
        warnings = []
        
        # Get all query files
        query_files = list(queries_dir.glob('*'))
        
        if len(query_files) == 0:
            warnings.append("No query files found in queries/ directory")
            return errors, warnings
        
        # Validate each query file
        for query_file in query_files:
            if query_file.is_file():
                file_errors, file_warnings = self._validate_query_file(query_file)
                errors.extend([f"{query_file.name}: {e}" for e in file_errors])
                warnings.extend([f"{query_file.name}: {w}" for w in file_warnings])
        
        return errors, warnings
    
    def _validate_query_file(self, query_file: Path) -> Tuple[List[str], List[str]]:
        """Validate a single query file."""
        errors = []
        warnings = []
        
        # Check file extension
        file_ext = query_file.suffix.lower()
        if file_ext not in self.QUERY_FILE_EXTENSIONS:
            warnings.append(f"Unknown query file extension: {file_ext}")
        
        # Basic syntax checks based on file type
        try:
            with open(query_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            errors.append(f"Failed to read query file: {e}")
            return errors, warnings
        
        if len(content.strip()) == 0:
            errors.append("Query file is empty")
            return errors, warnings
        
        # Type-specific validation
        if file_ext == '.json':
            # Validate JSON syntax
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON syntax: {e}")
        elif file_ext == '.kql':
            # Basic KQL validation (check for common patterns)
            if not re.search(r'\b(where|project|summarize|join|union)\b', content, re.IGNORECASE):
                warnings.append("KQL query may be missing common operators")
        elif file_ext == '.spl':
            # Basic SPL validation
            if not re.search(r'\b(index|search|stats|eval|where)\b', content, re.IGNORECASE):
                warnings.append("SPL query may be missing common commands")
        
        return errors, warnings
    
    def _validate_required_files(self, playbook_path: Path) -> List[str]:
        """Validate presence of required files."""
        errors = []
        
        for req_file in self.REQUIRED_FILES:
            file_path = playbook_path / req_file
            if not file_path.exists():
                errors.append(f"Required file not found: {req_file}")
            elif not file_path.is_file():
                errors.append(f"Required path is not a file: {req_file}")
        
        return errors
    
    def validate_all_playbooks(
        self,
        strict: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Validate all playbooks in the playbooks directory.
        
        Args:
            strict: If True, stop on first error
        
        Returns:
            Dictionary mapping playbook IDs to validation results
        """
        results = {}
        
        if not self.playbooks_dir.exists():
            self.logger.warning(f"Playbooks directory does not exist: {self.playbooks_dir}")
            return results
        
        # Find all playbook directories
        for playbook_dir in self.playbooks_dir.iterdir():
            if not playbook_dir.is_dir():
                continue
            
            # Skip template and master-playbook
            if playbook_dir.name in ['template', 'master-playbook']:
                continue
            
            try:
                is_valid, errors, warnings = self.validate_playbook(playbook_dir, strict=False)
                
                results[playbook_dir.name] = {
                    "is_valid": is_valid,
                    "errors": errors,
                    "warnings": warnings,
                    "path": str(playbook_dir)
                }
                
                if strict and not is_valid:
                    break
                    
            except Exception as e:
                results[playbook_dir.name] = {
                    "is_valid": False,
                    "errors": [f"Validation exception: {str(e)}"],
                    "warnings": [],
                    "path": str(playbook_dir)
                }
        
        return results
    
    def get_validation_summary(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary of validation results.
        
        Args:
            results: Validation results from validate_all_playbooks()
        
        Returns:
            Summary dictionary
        """
        total = len(results)
        valid = sum(1 for r in results.values() if r.get('is_valid', False))
        invalid = total - valid
        
        total_errors = sum(len(r.get('errors', [])) for r in results.values())
        total_warnings = sum(len(r.get('warnings', [])) for r in results.values())
        
        return {
            "total_playbooks": total,
            "valid": valid,
            "invalid": invalid,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "validation_rate": (valid / total * 100) if total > 0 else 0
        }

