"""
Deanonymizer Service - Deterministic deanonymization for reporting.

This module provides a service for deanonymizing data before generating reports.
It uses DeterministicAnonymizer to reverse anonymization using the mapping table.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from automation_scripts.utils.deterministic_anonymizer import (
    DeterministicAnonymizer,
    DeterministicAnonymizerError
)


class DeanonymizerError(Exception):
    """Base exception for deanonymizer errors."""
    pass


class Deanonymizer:
    """
    Deanonymizer Service for reversing anonymization before reporting.
    
    Provides deterministic deanonymization using the mapping table:
    - Deanonymize findings
    - Deanonymize evidence
    - Deanonymize reports
    - Batch deanonymization
    - Integration with DeterministicAnonymizer
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        anonymizer: Optional[DeterministicAnonymizer] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Deanonymizer Service.
        
        Args:
            config_path: Path to config.yml file
            anonymizer: Optional DeterministicAnonymizer instance
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Load config
        if config_path:
            import yaml
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            default_config = project_root / "configs" / "config.yml"
            if default_config.exists():
                import yaml
                with open(default_config, 'r') as f:
                    self.config = yaml.safe_load(f)
            else:
                self.config = {}
        
        # Initialize anonymizer (used for deanonymization)
        if anonymizer:
            self.anonymizer = anonymizer
        else:
            db_config = self._get_db_config()
            if not db_config:
                raise DeanonymizerError(
                    "Database configuration required for deanonymization. "
                    "Provide db_config or config_path with database settings."
                )
            
            try:
                self.anonymizer = DeterministicAnonymizer(
                    db_config=db_config,
                    logger=self.logger
                )
            except Exception as e:
                raise DeanonymizerError(f"Failed to initialize anonymizer: {e}")
        
        self.logger.info("Deanonymizer initialized")
    
    def deanonymize_finding(
        self,
        finding: Dict[str, Any],
        fields_to_deanonymize: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Deanonymize a finding.
        
        Args:
            finding: Finding dictionary to deanonymize
            fields_to_deanonymize: Optional list of field names to deanonymize
        
        Returns:
            Deanonymized finding dictionary
        """
        try:
            if fields_to_deanonymize is None:
                # Default fields that may contain anonymized data
                fields_to_deanonymize = [
                    'ip', 'source_ip', 'destination_ip', 'src_ip', 'dst_ip',
                    'email', 'user_email', 'sender_email', 'recipient_email',
                    'username', 'user', 'account', 'user_name',
                    'hostname', 'host', 'server', 'machine_name',
                    'domain', 'fqdn',
                    'description', 'title', 'summary', 'details',
                    'indicators', 'recommendations', 'evidence_references'
                ]
            
            # Deanonymize finding
            deanonymized = self.anonymizer.deanonymize_record(
                record=finding,
                fields_to_deanonymize=fields_to_deanonymize
            )
            
            # Handle nested structures
            if 'indicators' in deanonymized and isinstance(deanonymized['indicators'], list):
                deanonymized['indicators'] = [
                    self._deanonymize_value(indicator) if isinstance(indicator, str) else indicator
                    for indicator in deanonymized['indicators']
                ]
            
            if 'recommendations' in deanonymized and isinstance(deanonymized['recommendations'], list):
                deanonymized['recommendations'] = [
                    self._deanonymize_value(rec) if isinstance(rec, str) else rec
                    for rec in deanonymized['recommendations']
                ]
            
            if 'evidence_references' in deanonymized and isinstance(deanonymized['evidence_references'], list):
                for ref in deanonymized['evidence_references']:
                    if isinstance(ref, dict):
                        ref = self.anonymizer.deanonymize_record(
                            record=ref,
                            fields_to_deanonymize=fields_to_deanonymize
                        )
            
            self.logger.debug(f"Deanonymized finding: {finding.get('finding_id')}")
            
            return deanonymized
            
        except DeterministicAnonymizerError as e:
            self.logger.error(f"Anonymizer error during deanonymization: {e}")
            raise DeanonymizerError(f"Failed to deanonymize finding: {e}")
        except Exception as e:
            self.logger.error(f"Error deanonymizing finding: {e}")
            raise DeanonymizerError(f"Failed to deanonymize finding: {e}")
    
    def deanonymize_findings(
        self,
        findings: List[Dict[str, Any]],
        fields_to_deanonymize: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Deanonymize multiple findings.
        
        Args:
            findings: List of findings to deanonymize
            fields_to_deanonymize: Optional list of field names to deanonymize
        
        Returns:
            List of deanonymized findings
        """
        self.logger.info(f"Deanonymizing {len(findings)} findings")
        
        deanonymized_findings = []
        
        for finding in findings:
            try:
                deanonymized = self.deanonymize_finding(
                    finding=finding,
                    fields_to_deanonymize=fields_to_deanonymize
                )
                deanonymized_findings.append(deanonymized)
            except Exception as e:
                self.logger.warning(f"Failed to deanonymize finding {finding.get('finding_id')}: {e}")
                # Include original finding if deanonymization fails
                deanonymized_findings.append(finding)
        
        self.logger.info(f"Deanonymized {len(deanonymized_findings)} findings")
        
        return deanonymized_findings
    
    def deanonymize_evidence(
        self,
        evidence: Dict[str, Any],
        fields_to_deanonymize: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Deanonymize evidence.
        
        Args:
            evidence: Evidence dictionary to deanonymize
            fields_to_deanonymize: Optional list of field names to deanonymize
        
        Returns:
            Deanonymized evidence dictionary
        """
        try:
            if fields_to_deanonymize is None:
                fields_to_deanonymize = [
                    'ip', 'source_ip', 'destination_ip', 'src_ip', 'dst_ip',
                    'email', 'user_email', 'sender_email', 'recipient_email',
                    'username', 'user', 'account', 'user_name',
                    'hostname', 'host', 'server', 'machine_name',
                    'domain', 'fqdn',
                    'raw_data', 'normalized_fields', 'metadata'
                ]
            
            # Deanonymize evidence
            deanonymized = self.anonymizer.deanonymize_record(
                record=evidence,
                fields_to_deanonymize=fields_to_deanonymize
            )
            
            # Handle nested JSONB fields
            if 'raw_data' in deanonymized and isinstance(deanonymized['raw_data'], dict):
                deanonymized['raw_data'] = self.anonymizer.deanonymize_record(
                    record=deanonymized['raw_data'],
                    fields_to_deanonymize=fields_to_deanonymize
                )
            
            if 'normalized_fields' in deanonymized and isinstance(deanonymized['normalized_fields'], dict):
                deanonymized['normalized_fields'] = self.anonymizer.deanonymize_record(
                    record=deanonymized['normalized_fields'],
                    fields_to_deanonymize=fields_to_deanonymize
                )
            
            if 'metadata' in deanonymized and isinstance(deanonymized['metadata'], dict):
                deanonymized['metadata'] = self.anonymizer.deanonymize_record(
                    record=deanonymized['metadata'],
                    fields_to_deanonymize=fields_to_deanonymize
                )
            
            self.logger.debug(f"Deanonymized evidence: {evidence.get('evidence_id')}")
            
            return deanonymized
            
        except DeterministicAnonymizerError as e:
            self.logger.error(f"Anonymizer error during deanonymization: {e}")
            raise DeanonymizerError(f"Failed to deanonymize evidence: {e}")
        except Exception as e:
            self.logger.error(f"Error deanonymizing evidence: {e}")
            raise DeanonymizerError(f"Failed to deanonymize evidence: {e}")
    
    def deanonymize_report(
        self,
        report: Dict[str, Any],
        fields_to_deanonymize: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Deanonymize a report (e.g., executive summary).
        
        Args:
            report: Report dictionary to deanonymize
            fields_to_deanonymize: Optional list of field names to deanonymize
        
        Returns:
            Deanonymized report dictionary
        """
        try:
            deanonymized = report.copy()
            
            # Deanonymize findings if present
            if 'findings' in deanonymized and isinstance(deanonymized['findings'], list):
                deanonymized['findings'] = self.deanonymize_findings(
                    findings=deanonymized['findings'],
                    fields_to_deanonymize=fields_to_deanonymize
                )
            
            # Deanonymize critical findings if present
            if 'critical_findings' in deanonymized and isinstance(deanonymized['critical_findings'], list):
                deanonymized['critical_findings'] = self.deanonymize_findings(
                    findings=deanonymized['critical_findings'],
                    fields_to_deanonymize=fields_to_deanonymize
                )
            
            # Deanonymize text fields that may contain anonymized values
            text_fields = ['executive_summary', 'markdown', 'summary', 'description', 'title']
            for field in text_fields:
                if field in deanonymized and isinstance(deanonymized[field], str):
                    deanonymized[field] = self._deanonymize_text(deanonymized[field])
            
            # Deanonymize recommendations and next steps
            if 'recommendations' in deanonymized:
                recommendations = deanonymized['recommendations']
                if isinstance(recommendations, dict):
                    if 'immediate_actions' in recommendations:
                        recommendations['immediate_actions'] = [
                            self._deanonymize_text(action) if isinstance(action, str) else action
                            for action in recommendations['immediate_actions']
                        ]
                    if 'long_term_improvements' in recommendations:
                        recommendations['long_term_improvements'] = [
                            self._deanonymize_text(improvement) if isinstance(improvement, str) else improvement
                            for improvement in recommendations['long_term_improvements']
                        ]
            
            if 'next_steps' in deanonymized:
                next_steps = deanonymized['next_steps']
                if isinstance(next_steps, dict):
                    if 'follow_up_investigations' in next_steps:
                        next_steps['follow_up_investigations'] = [
                            self._deanonymize_text(inv) if isinstance(inv, str) else inv
                            for inv in next_steps['follow_up_investigations']
                        ]
                    if 'additional_queries' in next_steps:
                        next_steps['additional_queries'] = [
                            self._deanonymize_text(query) if isinstance(query, str) else query
                            for query in next_steps['additional_queries']
                        ]
            
            self.logger.info("Deanonymized report")
            
            return deanonymized
            
        except Exception as e:
            self.logger.error(f"Error deanonymizing report: {e}")
            raise DeanonymizerError(f"Failed to deanonymize report: {e}")
    
    def _deanonymize_value(self, value: str) -> str:
        """
        Attempt to deanonymize a single value.
        
        Args:
            value: Value to deanonymize
        
        Returns:
            Deanonymized value or original if not found
        """
        if not value or not isinstance(value, str):
            return value
        
        # Try different value types
        value_types = ['ip', 'email', 'username', 'hostname', 'generic']
        
        for value_type in value_types:
            try:
                original = self.anonymizer.deanonymize(value, value_type=value_type)
                if original:
                    return original
            except Exception:
                continue
        
        return value
    
    def _deanonymize_text(self, text: str) -> str:
        """
        Deanonymize text by finding and replacing anonymized values.
        
        Args:
            text: Text to deanonymize
        
        Returns:
            Text with deanonymized values
        """
        if not text or not isinstance(text, str):
            return text
        
        # Simple approach: try to find patterns that look like anonymized values
        # This is a basic implementation - can be enhanced with regex patterns
        
        # Try to find IP addresses (anonymized IPs often follow patterns)
        import re
        
        # Pattern for anonymized IPs (e.g., 10.123.45.67)
        ip_pattern = r'\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
        for match in re.finditer(ip_pattern, text):
            anonymized_ip = match.group(1)
            original_ip = self.anonymizer.deanonymize(anonymized_ip, value_type='ip')
            if original_ip:
                text = text.replace(anonymized_ip, original_ip)
        
        # Pattern for anonymized emails (e.g., user_abc12345@example.local)
        email_pattern = r'\b([a-zA-Z0-9_]+_[a-zA-Z0-9]+@[a-zA-Z0-9.-]+\.local)\b'
        for match in re.finditer(email_pattern, text):
            anonymized_email = match.group(1)
            original_email = self.anonymizer.deanonymize(anonymized_email, value_type='email')
            if original_email:
                text = text.replace(anonymized_email, original_email)
        
        # Pattern for anonymized usernames (e.g., user_abc123456789)
        username_pattern = r'\b(user_[a-zA-Z0-9]{12,})\b'
        for match in re.finditer(username_pattern, text):
            anonymized_username = match.group(1)
            original_username = self.anonymizer.deanonymize(anonymized_username, value_type='username')
            if original_username:
                text = text.replace(anonymized_username, original_username)
        
        return text
    
    def _get_db_config(self) -> Optional[Dict[str, Any]]:
        """Get database configuration from config."""
        try:
            db_config = self.config.get('database', {})
            vms = self.config.get('vms', {})
            
            # Get VM02 IP
            vm02_ip = vms.get('vm02', {}).get('ip', 'localhost')
            
            return {
                'host': vm02_ip,
                'port': db_config.get('port', 5432),
                'database': db_config.get('name', 'threat_hunting'),
                'user': db_config.get('user', 'threat_hunter'),
                'password': os.getenv('POSTGRES_PASSWORD') or db_config.get('password', '')
            }
        except Exception as e:
            self.logger.warning(f"Failed to get DB config: {e}")
            return None

