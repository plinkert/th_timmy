"""
Playbook Engine - Deterministic analysis engine for threat hunting playbooks.

This module provides a deterministic playbook execution engine that processes
data packages and executes playbook analyzers without AI dependencies.
"""

import os
import sys
import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from automation_scripts.utils.data_package import DataPackage, DataPackageError
from automation_scripts.utils.deterministic_anonymizer import DeterministicAnonymizer, DeterministicAnonymizerError
from automation_scripts.utils.playbook_validator import PlaybookValidator


class PlaybookEngineError(Exception):
    """Base exception for playbook engine errors."""
    pass


class PlaybookExecutionError(PlaybookEngineError):
    """Exception raised when playbook execution fails."""
    pass


class PlaybookEngine:
    """
    Deterministic playbook execution engine.
    
    Executes playbooks with deterministic analysis logic (no AI).
    Integrates with DataPackage and DeterministicAnonymizer for data processing.
    """
    
    def __init__(
        self,
        playbooks_dir: Optional[Path] = None,
        anonymizer: Optional[DeterministicAnonymizer] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Playbook Engine.
        
        Args:
            playbooks_dir: Path to playbooks directory
            anonymizer: Optional DeterministicAnonymizer instance
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Determine playbooks directory
        if playbooks_dir:
            self.playbooks_dir = Path(playbooks_dir)
        else:
            self.playbooks_dir = project_root / "playbooks"
        
        # Initialize anonymizer if not provided
        self.anonymizer = anonymizer
        
        # Initialize validator
        self.validator = PlaybookValidator(playbooks_dir=str(self.playbooks_dir), logger=self.logger)
        
        self.logger.info(f"PlaybookEngine initialized with playbooks_dir: {self.playbooks_dir}")
    
    def execute_playbook(
        self,
        playbook_id: str,
        data_package: DataPackage,
        anonymize_before: bool = True,
        deanonymize_after: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a playbook on a data package.
        
        Args:
            playbook_id: Playbook identifier
            data_package: DataPackage instance with data to analyze
            anonymize_before: Whether to anonymize data before analysis
            deanonymize_after: Whether to deanonymize results after analysis
        
        Returns:
            Dictionary with execution results and findings
        
        Raises:
            PlaybookExecutionError: If execution fails
        """
        playbook_path = self.playbooks_dir / playbook_id
        
        if not playbook_path.exists():
            raise PlaybookExecutionError(f"Playbook not found: {playbook_id}")
        
        if not playbook_path.is_dir():
            raise PlaybookExecutionError(f"Playbook path is not a directory: {playbook_path}")
        
        # Validate playbook
        is_valid, errors, warnings = self.validator.validate_playbook(playbook_path, strict=False)
        if not is_valid:
            self.logger.warning(f"Playbook {playbook_id} has validation errors: {errors}")
        
        try:
            # Load playbook metadata
            metadata_file = playbook_path / "metadata.yml"
            if not metadata_file.exists():
                raise PlaybookExecutionError(f"metadata.yml not found for playbook {playbook_id}")
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = yaml.safe_load(f)
            
            # Prepare data
            analysis_data = data_package.data.copy()
            
            # Anonymize data before analysis if requested
            if anonymize_before and self.anonymizer:
                self.logger.info(f"Anonymizing data before analysis for playbook {playbook_id}")
                anonymized_data = []
                for record in analysis_data:
                    anonymized_record = self.anonymizer.anonymize_record(record)
                    anonymized_data.append(anonymized_record)
                analysis_data = anonymized_data
                data_package.set_anonymization_info(
                    is_anonymized=True,
                    method="deterministic"
                )
            
            # Load and execute analyzer
            analyzer = self._load_analyzer(playbook_path)
            if not analyzer:
                raise PlaybookExecutionError(f"Analyzer not found for playbook {playbook_id}")
            
            # Execute analysis
            self.logger.info(f"Executing playbook {playbook_id} on {len(analysis_data)} records")
            findings = analyzer.analyze(analysis_data, metadata)
            
            # Deanonymize findings if requested
            if deanonymize_after and self.anonymizer and data_package.metadata.get('anonymization', {}).get('is_anonymized', False):
                self.logger.info(f"Deanonymizing findings for playbook {playbook_id}")
                deanonymized_findings = []
                for finding in findings:
                    deanonymized_finding = self.anonymizer.deanonymize_record(finding)
                    deanonymized_findings.append(deanonymized_finding)
                findings = deanonymized_findings
            
            # Prepare execution result
            result = {
                'playbook_id': playbook_id,
                'technique_id': metadata.get('mitre', {}).get('technique_id', ''),
                'technique_name': metadata.get('mitre', {}).get('technique_name', ''),
                'tactic': metadata.get('mitre', {}).get('tactic', ''),
                'execution_timestamp': datetime.utcnow().isoformat(),
                'records_analyzed': len(analysis_data),
                'findings_count': len(findings),
                'findings': findings,
                'anonymized': anonymize_before,
                'deanonymized': deanonymize_after,
                'validation_status': {
                    'is_valid': is_valid,
                    'errors': errors,
                    'warnings': warnings
                }
            }
            
            self.logger.info(f"Playbook {playbook_id} executed successfully: {len(findings)} findings")
            return result
            
        except Exception as e:
            error_msg = f"Failed to execute playbook {playbook_id}: {e}"
            self.logger.error(error_msg)
            raise PlaybookExecutionError(error_msg)
    
    def execute_playbooks_sequentially(
        self,
        playbook_data_map: Dict[str, DataPackage],
        anonymize_before: bool = True,
        deanonymize_after: bool = True
    ) -> Dict[str, Any]:
        """
        Execute multiple playbooks sequentially.
        
        Args:
            playbook_data_map: Dictionary mapping playbook_id -> DataPackage
            anonymize_before: Whether to anonymize data before analysis
            deanonymize_after: Whether to deanonymize results after analysis
        
        Returns:
            Dictionary with execution results for all playbooks
        """
        all_findings = []
        execution_results = []
        
        for playbook_id, data_package in playbook_data_map.items():
            try:
                result = self.execute_playbook(
                    playbook_id=playbook_id,
                    data_package=data_package,
                    anonymize_before=anonymize_before,
                    deanonymize_after=deanonymize_after
                )
                
                all_findings.extend(result['findings'])
                execution_results.append(result)
                
            except PlaybookExecutionError as e:
                self.logger.error(f"Error executing playbook {playbook_id}: {e}")
                execution_results.append({
                    'playbook_id': playbook_id,
                    'status': 'error',
                    'error': str(e),
                    'execution_timestamp': datetime.utcnow().isoformat()
                })
        
        return {
            'all_findings': all_findings,
            'execution_results': execution_results,
            'total_findings': len(all_findings),
            'total_playbooks': len(playbook_data_map),
            'successful_playbooks': sum(1 for r in execution_results if r.get('status') != 'error'),
            'failed_playbooks': sum(1 for r in execution_results if r.get('status') == 'error'),
            'execution_timestamp': datetime.utcnow().isoformat()
        }
    
    def _load_analyzer(self, playbook_path: Path) -> Optional[Any]:
        """
        Load analyzer module from playbook.
        
        Args:
            playbook_path: Path to playbook directory
        
        Returns:
            Analyzer module or None if not found
        """
        analyzer_file = playbook_path / "scripts" / "analyzer.py"
        
        if not analyzer_file.exists():
            self.logger.warning(f"Analyzer not found: {analyzer_file}")
            return None
        
        try:
            spec = importlib.util.spec_from_file_location("analyzer", analyzer_file)
            if spec is None or spec.loader is None:
                raise PlaybookExecutionError(f"Failed to load analyzer spec from {analyzer_file}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules["analyzer"] = module
            spec.loader.exec_module(module)
            
            if not hasattr(module, 'analyze'):
                self.logger.warning(f"Analyzer module does not have 'analyze' function: {analyzer_file}")
                return None
            
            return module
            
        except Exception as e:
            self.logger.error(f"Failed to load analyzer from {analyzer_file}: {e}")
            return None
    
    def get_execution_summary(self, execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of execution results.
        
        Args:
            execution_results: Results from execute_playbooks_sequentially()
        
        Returns:
            Summary dictionary
        """
        findings = execution_results.get('all_findings', [])
        
        # Count findings by severity
        severity_counts = {}
        for finding in findings:
            severity = finding.get('severity', 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Count findings by technique
        technique_counts = {}
        for result in execution_results.get('execution_results', []):
            if result.get('status') != 'error':
                technique_id = result.get('technique_id', 'unknown')
                count = result.get('findings_count', 0)
                technique_counts[technique_id] = technique_counts.get(technique_id, 0) + count
        
        return {
            'total_findings': execution_results.get('total_findings', 0),
            'total_playbooks': execution_results.get('total_playbooks', 0),
            'successful_playbooks': execution_results.get('successful_playbooks', 0),
            'failed_playbooks': execution_results.get('failed_playbooks', 0),
            'severity_distribution': severity_counts,
            'technique_distribution': technique_counts,
            'execution_timestamp': execution_results.get('execution_timestamp')
        }

