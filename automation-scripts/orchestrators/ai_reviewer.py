"""
AI Reviewer - Automated AI review workflow for findings validation.

This module provides automated AI-powered review of threat hunting findings,
including validation, status updates, and review reporting.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from automation_scripts.services.ai_service import AIService, AIServiceError
from automation_scripts.utils.deterministic_anonymizer import DeterministicAnonymizer, DeterministicAnonymizerError


class AIReviewerError(Exception):
    """Base exception for AI reviewer errors."""
    pass


class AIReviewer:
    """
    AI Reviewer for automated findings validation.
    
    Provides automated AI-powered review of findings:
    - Batch validation of findings
    - Status updates based on validation
    - Review reporting
    - Integration with database
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        ai_service: Optional[AIService] = None,
        anonymizer: Optional[DeterministicAnonymizer] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize AI Reviewer.
        
        Args:
            config_path: Path to config.yml file
            ai_service: Optional AIService instance
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
        
        # Initialize AI service
        if ai_service:
            self.ai_service = ai_service
        else:
            ai_config = self.config.get('ai', {})
            openai_config = ai_config.get('openai', {})
            
            # Get API key from config or environment
            api_key = openai_config.get('api_key') or os.getenv('OPENAI_API_KEY')
            
            # Initialize anonymizer if not provided
            if anonymizer is None and ai_config.get('anonymize_before_ai', True):
                db_config = self._get_db_config()
                if db_config:
                    try:
                        anonymizer = DeterministicAnonymizer(
                            db_config=db_config,
                            logger=self.logger
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to initialize anonymizer: {e}")
            
            self.ai_service = AIService(
                api_key=api_key,
                model=openai_config.get('model', 'gpt-4'),
                temperature=openai_config.get('temperature', 0.3),
                max_tokens=openai_config.get('max_tokens', 2000),
                anonymizer=anonymizer,
                logger=self.logger
            )
        
        self.anonymizer = anonymizer
        
        self.logger.info("AIReviewer initialized")
    
    def review_finding(
        self,
        finding: Dict[str, Any],
        update_status: bool = True
    ) -> Dict[str, Any]:
        """
        Review a single finding using AI.
        
        Args:
            finding: Finding dictionary to review
            update_status: Whether to update finding status based on validation
        
        Returns:
            Review result dictionary
        """
        try:
            self.logger.info(f"Reviewing finding: {finding.get('finding_id')}")
            
            # Validate finding with AI
            validation = self.ai_service.validate_finding(
                finding=finding,
                anonymize=True
            )
            
            # Enhance description if needed
            enhancement = None
            if finding.get('description') and len(finding.get('description', '')) < 100:
                try:
                    enhancement = self.ai_service.enhance_finding_description(
                        finding=finding,
                        anonymize=True
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to enhance description: {e}")
            
            # Prepare review result
            review_result = {
                'finding_id': finding.get('finding_id'),
                'review_timestamp': datetime.utcnow().isoformat(),
                'validation': validation,
                'enhancement': enhancement,
                'recommended_status': self._determine_status(validation),
                'recommended_confidence': validation.get('confidence_assessment', {}).get('recommended'),
                'recommended_severity': validation.get('severity_assessment', {}).get('recommended'),
                'false_positive_risk': validation.get('false_positive_risk', 'unknown')
            }
            
            # Update finding if requested
            if update_status:
                finding['ai_review'] = review_result
                finding['status'] = review_result['recommended_status']
                if review_result['recommended_confidence']:
                    finding['confidence'] = review_result['recommended_confidence']
                if review_result['recommended_severity']:
                    finding['severity'] = review_result['recommended_severity']
                if enhancement and enhancement.get('enhanced_description'):
                    finding['description'] = enhancement['enhanced_description']
            
            self.logger.info(
                f"Finding {finding.get('finding_id')} reviewed: "
                f"status={review_result['recommended_status']}, "
                f"risk={review_result['false_positive_risk']}"
            )
            
            return review_result
            
        except AIServiceError as e:
            self.logger.error(f"AI service error during review: {e}")
            raise AIReviewerError(f"Failed to review finding: {e}")
        except Exception as e:
            self.logger.error(f"Error reviewing finding: {e}")
            raise AIReviewerError(f"Failed to review finding: {e}")
    
    def review_findings_batch(
        self,
        findings: List[Dict[str, Any]],
        update_status: bool = True,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Review multiple findings in batch.
        
        Args:
            findings: List of findings to review
            update_status: Whether to update finding status based on validation
            batch_size: Number of findings to process in parallel (default: 10)
        
        Returns:
            Batch review results dictionary
        """
        self.logger.info(f"Reviewing {len(findings)} findings in batches of {batch_size}")
        
        review_results = []
        review_summary = {
            'total_findings': len(findings),
            'reviewed': 0,
            'valid': 0,
            'needs_review': 0,
            'invalid': 0,
            'high_risk_false_positive': 0,
            'errors': []
        }
        
        # Process findings in batches
        for i in range(0, len(findings), batch_size):
            batch = findings[i:i + batch_size]
            self.logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} findings)")
            
            for finding in batch:
                try:
                    review_result = self.review_finding(
                        finding=finding,
                        update_status=update_status
                    )
                    review_results.append(review_result)
                    review_summary['reviewed'] += 1
                    
                    # Update summary statistics
                    status = review_result['recommended_status']
                    if status == 'confirmed':
                        review_summary['valid'] += 1
                    elif status == 'investigating':
                        review_summary['needs_review'] += 1
                    elif status == 'false_positive':
                        review_summary['invalid'] += 1
                    
                    if review_result['false_positive_risk'] == 'high':
                        review_summary['high_risk_false_positive'] += 1
                        
                except Exception as e:
                    error_msg = f"Error reviewing finding {finding.get('finding_id')}: {e}"
                    self.logger.error(error_msg)
                    review_summary['errors'].append({
                        'finding_id': finding.get('finding_id'),
                        'error': str(e)
                    })
        
        return {
            'review_timestamp': datetime.utcnow().isoformat(),
            'summary': review_summary,
            'results': review_results
        }
    
    def review_playbook_execution(
        self,
        execution_result: Dict[str, Any],
        update_status: bool = True
    ) -> Dict[str, Any]:
        """
        Review findings from a playbook execution.
        
        Args:
            execution_result: Playbook execution result from PlaybookEngine
            update_status: Whether to update finding status based on validation
        
        Returns:
            Review results dictionary
        """
        findings = execution_result.get('findings', [])
        
        self.logger.info(
            f"Reviewing {len(findings)} findings from playbook execution: "
            f"{execution_result.get('playbook_id')}"
        )
        
        # Review all findings
        batch_review = self.review_findings_batch(
            findings=findings,
            update_status=update_status
        )
        
        # Generate executive summary if multiple findings
        executive_summary = None
        if len(findings) > 1:
            try:
                context = {
                    'playbook_id': execution_result.get('playbook_id'),
                    'technique_id': execution_result.get('technique_id'),
                    'technique_name': execution_result.get('technique_name'),
                    'tactic': execution_result.get('tactic'),
                    'execution_timestamp': execution_result.get('execution_timestamp'),
                    'total_findings': len(findings)
                }
                
                executive_summary = self.ai_service.generate_executive_summary(
                    findings=findings,
                    context=context,
                    anonymize=True
                )
            except Exception as e:
                self.logger.warning(f"Failed to generate executive summary: {e}")
        
        return {
            'playbook_id': execution_result.get('playbook_id'),
            'execution_timestamp': execution_result.get('execution_timestamp'),
            'review_timestamp': datetime.utcnow().isoformat(),
            'batch_review': batch_review,
            'executive_summary': executive_summary
        }
    
    def get_review_summary(
        self,
        review_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get summary of review results.
        
        Args:
            review_results: Review results dictionary
        
        Returns:
            Summary dictionary
        """
        summary = review_results.get('summary', {})
        results = review_results.get('results', [])
        
        # Calculate statistics
        status_distribution = {}
        risk_distribution = {}
        
        for result in results:
            status = result.get('recommended_status', 'unknown')
            status_distribution[status] = status_distribution.get(status, 0) + 1
            
            risk = result.get('false_positive_risk', 'unknown')
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1
        
        return {
            'review_timestamp': review_results.get('review_timestamp'),
            'total_findings': summary.get('total_findings', 0),
            'reviewed': summary.get('reviewed', 0),
            'status_distribution': status_distribution,
            'risk_distribution': risk_distribution,
            'high_risk_count': summary.get('high_risk_false_positive', 0),
            'errors': summary.get('errors', [])
        }
    
    def _determine_status(
        self,
        validation: Dict[str, Any]
    ) -> str:
        """
        Determine recommended status based on validation result.
        
        Args:
            validation: Validation result from AI
        
        Returns:
            Recommended status string
        """
        validation_status = validation.get('validation_status', 'needs_review')
        false_positive_risk = validation.get('false_positive_risk', 'medium')
        
        if validation_status == 'invalid' or false_positive_risk == 'high':
            return 'false_positive'
        elif validation_status == 'valid' and false_positive_risk == 'low':
            return 'confirmed'
        else:
            return 'investigating'
    
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

