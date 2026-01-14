"""
Executive Summary Generator - AI-powered executive summary generation.

This module provides specialized executive summary generation using AI
with markdown template formatting for professional reporting.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Try relative imports first, fallback to direct imports if relative imports fail
try:
    from .ai_service import AIService, AIServiceError
    from ..utils.deterministic_anonymizer import DeterministicAnonymizer, DeterministicAnonymizerError
except (ImportError, ValueError):
    from services.ai_service import AIService, AIServiceError
    from utils.deterministic_anonymizer import DeterministicAnonymizer, DeterministicAnonymizerError


class ExecutiveSummaryGeneratorError(Exception):
    """Base exception for executive summary generator errors."""
    pass


class ExecutiveSummaryGenerator:
    """
    Executive Summary Generator for threat hunting results.
    
    Provides AI-powered executive summary generation with:
    - Markdown template formatting
    - Professional report structure
    - Integration with AIService
    - Customizable templates
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        ai_service: Optional[AIService] = None,
        template_path: Optional[Path] = None,
        anonymizer: Optional[DeterministicAnonymizer] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Executive Summary Generator.
        
        Args:
            config_path: Path to config.yml file
            ai_service: Optional AIService instance
            template_path: Optional path to markdown template
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
        
        # Load template
        if template_path:
            self.template_path = Path(template_path)
        else:
            self.template_path = project_root / "automation-scripts" / "templates" / "executive_summary_template.md"
        
        self.template = self._load_template()
        
        self.logger.info("ExecutiveSummaryGenerator initialized")
    
    def generate_summary(
        self,
        findings: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        format: str = "markdown",
        anonymize: bool = True
    ) -> Dict[str, Any]:
        """
        Generate executive summary for findings.
        
        Args:
            findings: List of findings to summarize
            context: Optional context information
            format: Output format ('markdown', 'json', 'both')
            anonymize: Whether to anonymize data before sending to AI
        
        Returns:
            Executive summary dictionary with formatted content
        """
        try:
            self.logger.info(f"Generating executive summary for {len(findings)} findings")
            
            # Generate AI summary
            ai_summary = self.ai_service.generate_executive_summary(
                findings=findings,
                context=context,
                anonymize=anonymize
            )
            
            # Calculate statistics
            statistics = self._calculate_statistics(findings)
            
            # Prepare context for template
            template_context = self._prepare_template_context(
                ai_summary=ai_summary,
                findings=findings,
                context=context,
                statistics=statistics
            )
            
            # Generate formatted summary
            result = {
                'summary_id': f"summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'generated_at': datetime.utcnow().isoformat(),
                'findings_count': len(findings),
                'ai_summary': ai_summary,
                'statistics': statistics,
                'context': context or {}
            }
            
            # Format based on requested format
            if format in ['markdown', 'both']:
                result['markdown'] = self._render_template(template_context)
            
            if format in ['json', 'both']:
                result['json'] = ai_summary
            
            self.logger.info(f"Executive summary generated: {result['summary_id']}")
            
            return result
            
        except AIServiceError as e:
            self.logger.error(f"AI service error during summary generation: {e}")
            raise ExecutiveSummaryGeneratorError(f"Failed to generate executive summary: {e}")
        except Exception as e:
            self.logger.error(f"Error generating executive summary: {e}")
            raise ExecutiveSummaryGeneratorError(f"Failed to generate executive summary: {e}")
    
    def generate_summary_from_execution(
        self,
        execution_result: Dict[str, Any],
        format: str = "markdown",
        anonymize: bool = True
    ) -> Dict[str, Any]:
        """
        Generate executive summary from playbook execution result.
        
        Args:
            execution_result: Playbook execution result from PlaybookEngine
            format: Output format ('markdown', 'json', 'both')
            anonymize: Whether to anonymize data before sending to AI
        
        Returns:
            Executive summary dictionary
        """
        findings = execution_result.get('findings', [])
        
        context = {
            'playbook_id': execution_result.get('playbook_id'),
            'technique_id': execution_result.get('technique_id'),
            'technique_name': execution_result.get('technique_name'),
            'tactic': execution_result.get('tactic'),
            'execution_timestamp': execution_result.get('execution_timestamp'),
            'time_range': execution_result.get('time_range'),
            'playbooks_executed': [execution_result.get('playbook_id')]
        }
        
        return self.generate_summary(
            findings=findings,
            context=context,
            format=format,
            anonymize=anonymize
        )
    
    def save_summary(
        self,
        summary: Dict[str, Any],
        output_path: Optional[Path] = None,
        format: str = "markdown"
    ) -> Path:
        """
        Save executive summary to file.
        
        Args:
            summary: Executive summary dictionary
            output_path: Optional output path (default: results/summaries/)
            format: File format ('markdown', 'json', 'both')
        
        Returns:
            Path to saved file(s)
        """
        try:
            # Determine output path
            if output_path:
                output_file = Path(output_path)
            else:
                results_dir = project_root / "results" / "summaries"
                results_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                output_file = results_dir / f"executive_summary_{timestamp}"
            
            saved_files = []
            
            # Save markdown
            if format in ['markdown', 'both']:
                if 'markdown' in summary:
                    md_file = output_file.with_suffix('.md')
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(summary['markdown'])
                    saved_files.append(md_file)
                    self.logger.info(f"Markdown summary saved: {md_file}")
            
            # Save JSON
            if format in ['json', 'both']:
                import json
                json_file = output_file.with_suffix('.json')
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                saved_files.append(json_file)
                self.logger.info(f"JSON summary saved: {json_file}")
            
            return saved_files[0] if saved_files else output_file
            
        except Exception as e:
            self.logger.error(f"Error saving summary: {e}")
            raise ExecutiveSummaryGeneratorError(f"Failed to save summary: {e}")
    
    def _load_template(self) -> str:
        """Load markdown template."""
        try:
            if self.template_path.exists():
                with open(self.template_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.warning(f"Template not found: {self.template_path}, using default")
                return self._get_default_template()
        except Exception as e:
            self.logger.warning(f"Failed to load template: {e}, using default")
            return self._get_default_template()
    
    def _get_default_template(self) -> str:
        """Get default template if file not found."""
        return """# Executive Summary - Threat Hunting Exercise

**Generated:** {{generated_at}}
**Total Findings:** {{total_findings}}

## Executive Overview

{{executive_summary}}

## Critical Findings

{{#critical_findings}}
- **{{technique_id}}:** {{title}} (Severity: {{severity}}, Confidence: {{confidence}})
{{/critical_findings}}

## Risk Assessment

**Overall Risk:** {{overall_risk}}

## Recommendations

{{#immediate_actions}}
- {{action}}
{{/immediate_actions}}
"""
    
    def _calculate_statistics(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics from findings."""
        severity_counts = {}
        technique_counts = {}
        
        for finding in findings:
            severity = finding.get('severity', 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            technique_id = finding.get('technique_id', 'unknown')
            technique_counts[technique_id] = technique_counts.get(technique_id, 0) + 1
        
        return {
            'total_findings': len(findings),
            'critical_count': severity_counts.get('critical', 0),
            'high_severity_count': severity_counts.get('high', 0),
            'medium_severity_count': severity_counts.get('medium', 0),
            'low_severity_count': severity_counts.get('low', 0),
            'technique_distribution': technique_counts,
            'severity_distribution': severity_counts
        }
    
    def _prepare_template_context(
        self,
        ai_summary: Dict[str, Any],
        findings: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        statistics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context for template rendering."""
        # Extract techniques with names
        techniques_detected = []
        for technique_id, count in statistics.get('technique_distribution', {}).items():
            # Find technique name from findings
            technique_name = None
            for finding in findings:
                if finding.get('technique_id') == technique_id:
                    technique_name = finding.get('technique_name', technique_id)
                    break
            
            techniques_detected.append({
                'technique_id': technique_id,
                'technique_name': technique_name or technique_id,
                'count': count
            })
        
        # Extract tactics
        tactics_observed = []
        for finding in findings:
            tactic = finding.get('tactic')
            if tactic and tactic not in tactics_observed:
                tactics_observed.append(tactic)
        
        template_context = {
            'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'time_range': context.get('time_range', 'N/A') if context else 'N/A',
            'total_findings': statistics['total_findings'],
            'playbooks_executed': ', '.join(context.get('playbooks_executed', [])) if context else 'N/A',
            'executive_summary': ai_summary.get('executive_summary', 'N/A'),
            'critical_findings': ai_summary.get('critical_findings', []),
            'techniques_detected': techniques_detected,
            'tactics_observed': tactics_observed,
            'attack_patterns': ai_summary.get('threat_landscape', {}).get('attack_patterns', 'N/A'),
            'overall_risk': ai_summary.get('risk_assessment', {}).get('overall_risk', 'Unknown'),
            'risk_score': ai_summary.get('risk_assessment', {}).get('risk_score', 0),
            'risk_factors': ai_summary.get('risk_assessment', {}).get('risk_factors', []),
            'immediate_actions': ai_summary.get('recommendations', {}).get('immediate_actions', []),
            'long_term_improvements': ai_summary.get('recommendations', {}).get('long_term_improvements', []),
            'follow_up_investigations': ai_summary.get('next_steps', {}).get('follow_up_investigations', []),
            'additional_queries': ai_summary.get('next_steps', {}).get('additional_queries', []),
            'critical_count': statistics['critical_count'],
            'high_severity_count': statistics['high_severity_count'],
            'medium_severity_count': statistics['medium_severity_count'],
            'low_severity_count': statistics['low_severity_count'],
            'model_used': ai_summary.get('model_used', 'N/A'),
            'anonymization_status': 'Enabled' if self.anonymizer else 'Disabled'
        }
        
        return template_context
    
    def _render_template(self, context: Dict[str, Any]) -> str:
        """
        Render template with context.
        
        Simple template engine using {{variable}} syntax.
        """
        result = self.template
        
        # Replace simple variables {{variable}}
        for key, value in context.items():
            if isinstance(value, (str, int, float)):
                result = result.replace(f'{{{{{key}}}}}', str(value))
            elif isinstance(value, list):
                # Handle list rendering
                if key == 'critical_findings':
                    findings_text = []
                    for finding in value:
                        findings_text.append(
                            f"### {finding.get('technique_id', 'N/A')}: {finding.get('title', 'N/A')}\n\n"
                            f"- **Severity:** {finding.get('severity', 'N/A')}\n"
                            f"- **Confidence:** {finding.get('confidence', 'N/A')}\n"
                            f"- **Finding ID:** {finding.get('finding_id', 'N/A')}\n"
                            f"- **Description:** {finding.get('summary', 'N/A')}\n"
                        )
                    result = result.replace('{{#critical_findings}}\n{{/critical_findings}}', '\n'.join(findings_text))
                    result = re.sub(r'\{\{#critical_findings\}\}.*?\{\{/critical_findings\}\}', '\n'.join(findings_text), result, flags=re.DOTALL)
                elif key in ['techniques_detected', 'tactics_observed', 'risk_factors', 'immediate_actions', 
                            'long_term_improvements', 'follow_up_investigations', 'additional_queries']:
                    items_text = []
                    for item in value:
                        if isinstance(item, dict):
                            if key == 'techniques_detected':
                                items_text.append(f"- **{item.get('technique_id', 'N/A')}:** {item.get('technique_name', 'N/A')} ({item.get('count', 0)} findings)")
                            elif key == 'risk_factors':
                                items_text.append(f"- {item}")
                            else:
                                items_text.append(f"- {item}")
                        else:
                            items_text.append(f"- {item}")
                    result = result.replace(f'{{{{#{key}}}}}', '')
                    result = result.replace(f'{{{{/{key}}}}}', '\n'.join(items_text))
                    result = re.sub(r'\{\{#' + key + r'\}\}.*?\{\{/' + key + r'\}\}', '\n'.join(items_text), result, flags=re.DOTALL)
        
        # Clean up any remaining template syntax
        result = re.sub(r'\{\{[^}]+\}\}', '', result)
        
        return result
    
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

