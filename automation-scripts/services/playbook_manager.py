"""
Playbook Manager - Service for managing threat hunting playbooks.

This module provides functionality for managing playbooks including:
- Listing all playbooks
- Creating new playbooks
- Editing playbooks
- Validating playbooks
- Testing playbooks
"""

import os
import shutil
import logging
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from ..utils.playbook_validator import PlaybookValidator, PlaybookValidationError
from ..utils.query_generator import QueryGenerator


class PlaybookManagerError(Exception):
    """Base exception for playbook manager errors."""
    pass


class PlaybookManager:
    """
    Service for managing threat hunting playbooks.
    
    Provides functionality for:
    - Discovering and listing playbooks
    - Creating new playbooks from template
    - Editing playbook metadata
    - Validating playbooks
    - Testing playbooks
    """
    
    def __init__(
        self,
        playbooks_dir: Optional[Path] = None,
        template_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Playbook Manager.
        
        Args:
            playbooks_dir: Path to playbooks directory
            template_dir: Path to template directory
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Determine directories
        if playbooks_dir:
            self.playbooks_dir = Path(playbooks_dir)
        else:
            project_root = Path(__file__).parent.parent.parent
            self.playbooks_dir = project_root / "playbooks"
        
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            self.template_dir = self.playbooks_dir / "template"
        
        # Initialize validator
        self.validator = PlaybookValidator(playbooks_dir=str(self.playbooks_dir), logger=self.logger)
        
        # Initialize query generator for discovery
        self.query_generator = QueryGenerator(playbooks_dir=str(self.playbooks_dir), logger=self.logger)
        
        self.logger.info(f"PlaybookManager initialized with playbooks_dir: {self.playbooks_dir}")
    
    def list_playbooks(self) -> List[Dict[str, Any]]:
        """
        List all available playbooks.
        
        Returns:
            List of playbook information dictionaries
        """
        playbooks = self.query_generator.discover_playbooks()
        
        # Add validation status
        for playbook in playbooks:
            playbook_path = playbook.get('path', Path(playbook.get('id', '')))
            if isinstance(playbook_path, str):
                playbook_path = Path(playbook_path)
            
            # Validate playbook
            try:
                is_valid, errors, warnings = self.validator.validate_playbook(playbook_path, strict=False)
                playbook['is_valid'] = is_valid
                playbook['validation_errors'] = errors
                playbook['validation_warnings'] = warnings
            except Exception as e:
                self.logger.error(f"Error validating playbook {playbook.get('id')}: {e}")
                playbook['is_valid'] = False
                playbook['validation_errors'] = [str(e)]
                playbook['validation_warnings'] = []
        
        return playbooks
    
    def get_playbook(self, playbook_id: str) -> Optional[Dict[str, Any]]:
        """
        Get playbook by ID.
        
        Args:
            playbook_id: Playbook ID
        
        Returns:
            Playbook information dictionary or None if not found
        """
        playbooks = self.list_playbooks()
        
        for playbook in playbooks:
            if playbook.get('id') == playbook_id:
                return playbook
        
        return None
    
    def create_playbook(
        self,
        playbook_id: str,
        technique_id: str,
        technique_name: str,
        tactic: str,
        author: str,
        description: str,
        hypothesis: str,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new playbook from template.
        
        Args:
            playbook_id: Unique playbook identifier (e.g., 'T1566-phishing')
            technique_id: MITRE technique ID (e.g., 'T1566')
            technique_name: MITRE technique name
            tactic: MITRE tactic name
            author: Playbook author
            description: Playbook description
            hypothesis: Threat hunting hypothesis
            overwrite: If True, overwrite existing playbook
        
        Returns:
            Dictionary with creation result
        
        Raises:
            PlaybookManagerError: If playbook already exists and overwrite=False
        """
        playbook_path = self.playbooks_dir / playbook_id
        
        # Check if playbook already exists
        if playbook_path.exists() and not overwrite:
            raise PlaybookManagerError(f"Playbook {playbook_id} already exists. Use overwrite=True to replace.")
        
        # Check if template exists
        if not self.template_dir.exists():
            raise PlaybookManagerError(f"Template directory not found: {self.template_dir}")
        
        try:
            # Remove existing if overwrite
            if playbook_path.exists() and overwrite:
                shutil.rmtree(playbook_path)
            
            # Copy template
            shutil.copytree(self.template_dir, playbook_path)
            
            # Update metadata.yml
            metadata_file = playbook_path / "metadata.yml"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = yaml.safe_load(f)
                
                # Update playbook info
                metadata['playbook'] = {
                    'id': playbook_id,
                    'name': technique_name,
                    'version': '1.0.0',
                    'author': author,
                    'created': datetime.now().strftime('%Y-%m-%d'),
                    'updated': datetime.now().strftime('%Y-%m-%d'),
                    'description': description
                }
                
                # Update MITRE info
                metadata['mitre'] = {
                    'technique_id': technique_id,
                    'technique_name': technique_name,
                    'tactic': tactic,
                    'sub_techniques': []
                }
                
                # Update hypothesis
                metadata['hypothesis'] = hypothesis
                
                # Save metadata
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Validate created playbook
            is_valid, errors, warnings = self.validator.validate_playbook(playbook_path, strict=False)
            
            result = {
                'success': True,
                'playbook_id': playbook_id,
                'path': str(playbook_path),
                'is_valid': is_valid,
                'validation_errors': errors,
                'validation_warnings': warnings
            }
            
            self.logger.info(f"Created playbook {playbook_id} at {playbook_path}")
            return result
            
        except Exception as e:
            # Cleanup on error
            if playbook_path.exists():
                shutil.rmtree(playbook_path, ignore_errors=True)
            
            error_msg = f"Failed to create playbook {playbook_id}: {e}"
            self.logger.error(error_msg)
            raise PlaybookManagerError(error_msg)
    
    def update_playbook_metadata(
        self,
        playbook_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update playbook metadata.
        
        Args:
            playbook_id: Playbook ID
            updates: Dictionary with metadata updates
        
        Returns:
            Dictionary with update result
        
        Raises:
            PlaybookManagerError: If playbook not found or update fails
        """
        playbook = self.get_playbook(playbook_id)
        if not playbook:
            raise PlaybookManagerError(f"Playbook {playbook_id} not found")
        
        playbook_path = playbook.get('path')
        if isinstance(playbook_path, str):
            playbook_path = Path(playbook_path)
        
        metadata_file = playbook_path / "metadata.yml"
        if not metadata_file.exists():
            raise PlaybookManagerError(f"metadata.yml not found for playbook {playbook_id}")
        
        try:
            # Load current metadata
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = yaml.safe_load(f)
            
            # Update metadata
            if 'playbook' in updates:
                if 'playbook' not in metadata:
                    metadata['playbook'] = {}
                metadata['playbook'].update(updates['playbook'])
                # Always update 'updated' date
                metadata['playbook']['updated'] = datetime.now().strftime('%Y-%m-%d')
            
            if 'mitre' in updates:
                if 'mitre' not in metadata:
                    metadata['mitre'] = {}
                metadata['mitre'].update(updates['mitre'])
            
            if 'hypothesis' in updates:
                metadata['hypothesis'] = updates['hypothesis']
            
            if 'description' in updates:
                if 'playbook' not in metadata:
                    metadata['playbook'] = {}
                metadata['playbook']['description'] = updates['description']
            
            # Save metadata
            with open(metadata_file, 'w', encoding='utf-8') as f:
                yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Validate updated playbook
            is_valid, errors, warnings = self.validator.validate_playbook(playbook_path, strict=False)
            
            result = {
                'success': True,
                'playbook_id': playbook_id,
                'is_valid': is_valid,
                'validation_errors': errors,
                'validation_warnings': warnings
            }
            
            self.logger.info(f"Updated playbook {playbook_id}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to update playbook {playbook_id}: {e}"
            self.logger.error(error_msg)
            raise PlaybookManagerError(error_msg)
    
    def validate_playbook(self, playbook_id: str) -> Dict[str, Any]:
        """
        Validate a playbook.
        
        Args:
            playbook_id: Playbook ID
        
        Returns:
            Dictionary with validation results
        
        Raises:
            PlaybookManagerError: If playbook not found
        """
        playbook = self.get_playbook(playbook_id)
        if not playbook:
            raise PlaybookManagerError(f"Playbook {playbook_id} not found")
        
        playbook_path = playbook.get('path')
        if isinstance(playbook_path, str):
            playbook_path = Path(playbook_path)
        
        try:
            is_valid, errors, warnings = self.validator.validate_playbook(playbook_path, strict=False)
            
            return {
                'playbook_id': playbook_id,
                'is_valid': is_valid,
                'errors': errors,
                'warnings': warnings,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            error_msg = f"Validation failed for playbook {playbook_id}: {e}"
            self.logger.error(error_msg)
            raise PlaybookManagerError(error_msg)
    
    def test_playbook(self, playbook_id: str) -> Dict[str, Any]:
        """
        Test a playbook (basic validation and structure check).
        
        Args:
            playbook_id: Playbook ID
        
        Returns:
            Dictionary with test results
        
        Raises:
            PlaybookManagerError: If playbook not found
        """
        playbook = self.get_playbook(playbook_id)
        if not playbook:
            raise PlaybookManagerError(f"Playbook {playbook_id} not found")
        
        playbook_path = playbook.get('path')
        if isinstance(playbook_path, str):
            playbook_path = Path(playbook_path)
        
        test_results = {
            'playbook_id': playbook_id,
            'timestamp': datetime.utcnow().isoformat(),
            'tests': {}
        }
        
        # Test 1: Validation
        try:
            validation_result = self.validate_playbook(playbook_id)
            test_results['tests']['validation'] = {
                'passed': validation_result['is_valid'],
                'errors': validation_result['errors'],
                'warnings': validation_result['warnings']
            }
        except Exception as e:
            test_results['tests']['validation'] = {
                'passed': False,
                'error': str(e)
            }
        
        # Test 2: Structure check
        try:
            required_files = ['metadata.yml', 'README.md']
            missing_files = []
            for file_name in required_files:
                if not (playbook_path / file_name).exists():
                    missing_files.append(file_name)
            
            test_results['tests']['structure'] = {
                'passed': len(missing_files) == 0,
                'missing_files': missing_files
            }
        except Exception as e:
            test_results['tests']['structure'] = {
                'passed': False,
                'error': str(e)
            }
        
        # Test 3: Query files check
        try:
            queries_dir = playbook_path / "queries"
            query_files = []
            if queries_dir.exists():
                query_files = [f.name for f in queries_dir.iterdir() if f.is_file()]
            
            test_results['tests']['queries'] = {
                'passed': len(query_files) > 0,
                'query_files': query_files,
                'count': len(query_files)
            }
        except Exception as e:
            test_results['tests']['queries'] = {
                'passed': False,
                'error': str(e)
            }
        
        # Overall test result
        all_passed = all(
            test.get('passed', False)
            for test in test_results['tests'].values()
        )
        test_results['all_tests_passed'] = all_passed
        
        return test_results
    
    def delete_playbook(self, playbook_id: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete a playbook.
        
        Args:
            playbook_id: Playbook ID
            confirm: If True, delete the playbook
        
        Returns:
            Dictionary with deletion result
        
        Raises:
            PlaybookManagerError: If playbook not found or confirm=False
        """
        playbook = self.get_playbook(playbook_id)
        if not playbook:
            raise PlaybookManagerError(f"Playbook {playbook_id} not found")
        
        if not confirm:
            raise PlaybookManagerError("Deletion requires confirm=True")
        
        playbook_path = playbook.get('path')
        if isinstance(playbook_path, str):
            playbook_path = Path(playbook_path)
        
        try:
            shutil.rmtree(playbook_path)
            
            result = {
                'success': True,
                'playbook_id': playbook_id,
                'message': f"Playbook {playbook_id} deleted successfully"
            }
            
            self.logger.info(f"Deleted playbook {playbook_id}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to delete playbook {playbook_id}: {e}"
            self.logger.error(error_msg)
            raise PlaybookManagerError(error_msg)
    
    def get_playbook_summary(self) -> Dict[str, Any]:
        """
        Get summary of all playbooks.
        
        Returns:
            Dictionary with summary statistics
        """
        playbooks = self.list_playbooks()
        
        total = len(playbooks)
        valid = sum(1 for p in playbooks if p.get('is_valid', False))
        invalid = total - valid
        
        # Group by tactic
        by_tactic = {}
        for playbook in playbooks:
            tactic = playbook.get('tactic', 'Unknown')
            if tactic not in by_tactic:
                by_tactic[tactic] = []
            by_tactic[tactic].append(playbook.get('id'))
        
        return {
            'total_playbooks': total,
            'valid_playbooks': valid,
            'invalid_playbooks': invalid,
            'by_tactic': by_tactic,
            'timestamp': datetime.utcnow().isoformat()
        }

