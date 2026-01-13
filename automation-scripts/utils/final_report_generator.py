"""
Final Report Generator - Generate comprehensive final reports with real data.

This module provides a comprehensive final report generator that creates
detailed reports with deanonymized (real) data for stakeholders.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import re
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from automation_scripts.utils.deanonymizer import Deanonymizer, DeanonymizerError
from automation_scripts.utils.report_generator import ReportGenerator, ReportGeneratorError
from automation_scripts.services.executive_summary_generator import (
    ExecutiveSummaryGenerator,
    ExecutiveSummaryGeneratorError
)


class FinalReportGeneratorError(Exception):
    """Base exception for final report generator errors."""
    pass


class FinalReportGenerator:
    """
    Final Report Generator for creating comprehensive final reports.
    
    Provides comprehensive report generation with:
    - Automatic deanonymization (real data)
    - Detailed findings analysis
    - Executive summary integration
    - Professional formatting
    - Multiple output formats
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        deanonymizer: Optional[Deanonymizer] = None,
        report_generator: Optional[ReportGenerator] = None,
        summary_generator: Optional[ExecutiveSummaryGenerator] = None,
        template_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Final Report Generator.
        
        Args:
            config_path: Path to config.yml file
            deanonymizer: Optional Deanonymizer instance
            report_generator: Optional ReportGenerator instance
            summary_generator: Optional ExecutiveSummaryGenerator instance
            template_path: Optional path to markdown template
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
        
        # Initialize deanonymizer
        if deanonymizer:
            self.deanonymizer = deanonymizer
        else:
            try:
                self.deanonymizer = Deanonymizer(config_path=config_path, logger=self.logger)
            except Exception as e:
                self.logger.warning(f"Failed to initialize deanonymizer: {e}")
                self.deanonymizer = None
        
        # Initialize report generator
        if report_generator:
            self.report_generator = report_generator
        else:
            try:
                self.report_generator = ReportGenerator(
                    config_path=config_path,
                    deanonymizer=self.deanonymizer,
                    logger=self.logger
                )
            except Exception as e:
                self.logger.warning(f"Failed to initialize report generator: {e}")
                self.report_generator = None
        
        # Initialize summary generator
        if summary_generator:
            self.summary_generator = summary_generator
        else:
            try:
                self.summary_generator = ExecutiveSummaryGenerator(
                    config_path=config_path,
                    logger=self.logger
                )
            except Exception as e:
                self.logger.warning(f"Failed to initialize summary generator: {e}")
                self.summary_generator = None
        
        # Load template
        if template_path:
            self.template_path = Path(template_path)
        else:
            self.template_path = project_root / "automation-scripts" / "templates" / "final_report_template.md"
        
        self.template = self._load_template()
        
        self.logger.info("FinalReportGenerator initialized")
    
    def generate_final_report(
        self,
        findings: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        deanonymize: bool = True,
        include_executive_summary: bool = True,
        format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive final report with real (deanonymized) data.
        
        Args:
            findings: List of findings to include in report
            context: Optional context information
            deanonymize: Whether to deanonymize data before reporting (default: True)
            include_executive_summary: Whether to include AI-generated executive summary
            format: Output format ('markdown', 'json', 'both')
        
        Returns:
            Final report dictionary
        """
        try:
            self.logger.info(f"Generating final report for {len(findings)} findings")
            
            # Deanonymize findings if requested
            if deanonymize and self.deanonymizer:
                self.logger.info("Deanonymizing findings before final report generation")
                findings = self.deanonymizer.deanonymize_findings(findings)
            elif deanonymize and not self.deanonymizer:
                self.logger.warning("Deanonymization requested but deanonymizer not available")
            
            # Generate executive summary if requested
            executive_summary = None
            executive_summary_text = ""
            if include_executive_summary and self.summary_generator:
                try:
                    self.logger.info("Generating executive summary")
                    summary_result = self.summary_generator.generate_summary(
                        findings=findings,
                        context=context,
                        format='json',
                        anonymize=False  # Already deanonymized
                    )
                    executive_summary = summary_result
                    if 'ai_summary' in summary_result:
                        executive_summary_text = summary_result['ai_summary'].get('executive_summary', '')
                except Exception as e:
                    self.logger.warning(f"Failed to generate executive summary: {e}")
            
            # Calculate comprehensive statistics
            statistics = self._calculate_comprehensive_statistics(findings)
            
            # Prepare template context
            template_context = self._prepare_template_context(
                findings=findings,
                context=context,
                statistics=statistics,
                executive_summary=executive_summary,
                executive_summary_text=executive_summary_text
            )
            
            # Generate report
            report = {
                'report_id': f"final_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'generated_at': datetime.utcnow().isoformat(),
                'findings_count': len(findings),
                'deanonymized': deanonymize,
                'context': context or {},
                'findings': findings,
                'executive_summary': executive_summary,
                'statistics': statistics
            }
            
            # Format based on requested format
            if format in ['markdown', 'both']:
                report['markdown'] = self._render_template(template_context)
            
            if format in ['json', 'both']:
                report['json'] = {
                    'report_id': report['report_id'],
                    'generated_at': report['generated_at'],
                    'findings': findings,
                    'executive_summary': executive_summary,
                    'statistics': statistics
                }
            
            self.logger.info(f"Final report generated: {report['report_id']}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating final report: {e}")
            raise FinalReportGeneratorError(f"Failed to generate final report: {e}")
    
    def generate_final_report_from_execution(
        self,
        execution_result: Dict[str, Any],
        deanonymize: bool = True,
        include_executive_summary: bool = True,
        format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate final report from playbook execution result.
        
        Args:
            execution_result: Playbook execution result from PlaybookEngine
            deanonymize: Whether to deanonymize data before reporting
            include_executive_summary: Whether to include AI-generated executive summary
            format: Output format ('markdown', 'json', 'both')
        
        Returns:
            Final report dictionary
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
        
        return self.generate_final_report(
            findings=findings,
            context=context,
            deanonymize=deanonymize,
            include_executive_summary=include_executive_summary,
            format=format
        )
    
    def save_final_report(
        self,
        report: Dict[str, Any],
        output_path: Optional[Path] = None,
        format: str = "markdown"
    ) -> Path:
        """
        Save final report to file.
        
        Args:
            report: Final report dictionary
            output_path: Optional output path (default: results/reports/final/)
            format: File format ('markdown', 'json', 'both')
        
        Returns:
            Path to saved file(s)
        """
        try:
            # Determine output path
            if output_path:
                output_file = Path(output_path)
            else:
                results_dir = project_root / "results" / "reports" / "final"
                results_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                output_file = results_dir / f"final_threat_hunting_report_{timestamp}"
            
            saved_files = []
            
            # Save markdown
            if format in ['markdown', 'both']:
                if 'markdown' in report:
                    md_file = output_file.with_suffix('.md')
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(report['markdown'])
                    saved_files.append(md_file)
                    self.logger.info(f"Markdown final report saved: {md_file}")
            
            # Save JSON
            if format in ['json', 'both']:
                import json
                json_file = output_file.with_suffix('.json')
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
                saved_files.append(json_file)
                self.logger.info(f"JSON final report saved: {json_file}")
            
            return saved_files[0] if saved_files else output_file
            
        except Exception as e:
            self.logger.error(f"Error saving final report: {e}")
            raise FinalReportGeneratorError(f"Failed to save final report: {e}")
    
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
        return """# Threat Hunting Final Report

**Report ID:** {{report_id}}
**Generated:** {{generated_at}}
**Total Findings:** {{total_findings}}

## Executive Summary

{{executive_summary_text}}

## Findings

{{#findings}}
### {{title}}
- **Severity:** {{severity}}
- **Confidence:** {{confidence}}
{{/findings}}
"""
    
    def _calculate_comprehensive_statistics(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive statistics from findings."""
        if not findings:
            return {
                'total_findings': 0,
                'critical_count': 0,
                'high_severity_count': 0,
                'medium_severity_count': 0,
                'low_severity_count': 0
            }
        
        severity_counts = defaultdict(int)
        technique_counts = defaultdict(lambda: {'count': 0, 'critical': 0, 'high': 0, 'medium': 0, 'low': 0})
        tactic_counts = defaultdict(int)
        status_counts = defaultdict(int)
        confidence_scores = []
        sources = defaultdict(int)
        timestamps = []
        
        for finding in findings:
            severity = finding.get('severity', 'unknown')
            severity_counts[severity] += 1
            
            technique_id = finding.get('technique_id', 'unknown')
            technique_name = finding.get('technique_name', '')
            tactic = finding.get('tactic', 'unknown')
            
            technique_counts[technique_id]['count'] += 1
            technique_counts[technique_id]['name'] = technique_name
            technique_counts[technique_id]['tactic'] = tactic
            technique_counts[technique_id][severity] += 1
            
            tactic_counts[tactic] += 1
            
            status = finding.get('status', 'unknown')
            status_counts[status] += 1
            
            confidence = finding.get('confidence')
            if confidence is not None:
                confidence_scores.append(float(confidence))
            
            source = finding.get('source', 'unknown')
            sources[source] += 1
            
            timestamp = finding.get('timestamp')
            if timestamp:
                timestamps.append(timestamp)
        
        # Calculate percentages
        total = len(findings)
        critical_count = severity_counts.get('critical', 0)
        high_count = severity_counts.get('high', 0)
        medium_count = severity_counts.get('medium', 0)
        low_count = severity_counts.get('low', 0)
        
        # Confidence distribution
        high_confidence = sum(1 for c in confidence_scores if c >= 0.8)
        medium_confidence = sum(1 for c in confidence_scores if 0.5 <= c < 0.8)
        low_confidence = sum(1 for c in confidence_scores if c < 0.5)
        
        # Format techniques
        techniques_detected = []
        for tech_id, data in technique_counts.items():
            techniques_detected.append({
                'technique_id': tech_id,
                'technique_name': data.get('name', tech_id),
                'tactic': data.get('tactic', 'unknown'),
                'count': data['count'],
                'critical_count': data.get('critical', 0),
                'high_count': data.get('high', 0),
                'medium_count': data.get('medium', 0),
                'low_count': data.get('low', 0)
            })
        
        # Format tactics
        tactics_observed = [{'tactic': t, 'count': c} for t, c in tactic_counts.items()]
        
        # Format sources
        data_sources = [{'source': s, 'count': c} for s, c in sources.items()]
        
        # Format playbook executions
        playbook_executions = []
        playbooks = {}
        for finding in findings:
            playbook_id = finding.get('playbook_id')
            if playbook_id and playbook_id not in playbooks:
                playbooks[playbook_id] = {
                    'playbook_id': playbook_id,
                    'technique_id': finding.get('technique_id'),
                    'technique_name': finding.get('technique_name'),
                    'tactic': finding.get('tactic'),
                    'findings_count': 0,
                    'execution_timestamp': finding.get('execution_timestamp') or finding.get('timestamp')
                }
            if playbook_id:
                playbooks[playbook_id]['findings_count'] += 1
        
        playbook_executions = list(playbooks.values())
        
        return {
            'total_findings': total,
            'critical_count': critical_count,
            'high_severity_count': high_count,
            'medium_severity_count': medium_count,
            'low_severity_count': low_count,
            'critical_percentage': round((critical_count / total * 100) if total > 0 else 0, 1),
            'high_percentage': round((high_count / total * 100) if total > 0 else 0, 1),
            'medium_percentage': round((medium_count / total * 100) if total > 0 else 0, 1),
            'low_percentage': round((low_count / total * 100) if total > 0 else 0, 1),
            'unique_techniques_count': len(technique_counts),
            'unique_tactics_count': len(tactic_counts),
            'average_confidence': round(sum(confidence_scores) / len(confidence_scores), 2) if confidence_scores else 0,
            'high_confidence_count': high_confidence,
            'medium_confidence_count': medium_confidence,
            'low_confidence_count': low_confidence,
            'techniques_detected': techniques_detected,
            'tactics_observed': tactics_observed,
            'data_sources': data_sources,
            'status_distribution': dict(status_counts),
            'new_count': status_counts.get('new', 0),
            'investigating_count': status_counts.get('investigating', 0),
            'confirmed_count': status_counts.get('confirmed', 0),
            'false_positive_count': status_counts.get('false_positive', 0),
            'resolved_count': status_counts.get('resolved', 0),
            'playbook_executions': playbook_executions,
            'first_finding_timestamp': min(timestamps) if timestamps else None,
            'last_finding_timestamp': max(timestamps) if timestamps else None
        }
    
    def _prepare_template_context(
        self,
        findings: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        statistics: Dict[str, Any],
        executive_summary: Optional[Dict[str, Any]],
        executive_summary_text: str
    ) -> Dict[str, Any]:
        """Prepare context for template rendering."""
        # Sort findings by severity (critical first)
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_findings = sorted(
            findings,
            key=lambda f: (severity_order.get(f.get('severity', 'low'), 99), f.get('confidence', 0)),
            reverse=True
        )
        
        # Get critical findings (top 5)
        critical_findings = [f for f in sorted_findings if f.get('severity') == 'critical'][:5]
        if not critical_findings:
            critical_findings = sorted_findings[:5]
        
        # Prepare findings with index
        findings_with_index = []
        for i, finding in enumerate(sorted_findings, 1):
            finding_copy = finding.copy()
            finding_copy['index'] = i
            findings_with_index.append(finding_copy)
        
        # Prepare critical findings with index
        critical_with_index = []
        for i, finding in enumerate(critical_findings, 1):
            finding_copy = finding.copy()
            finding_copy['index'] = i
            critical_with_index.append(finding_copy)
        
        # Get executive summary data
        overall_risk = 'Unknown'
        risk_score = 0
        risk_factors = []
        immediate_actions = []
        long_term_improvements = []
        follow_up_investigations = []
        additional_queries = []
        recommended_playbooks = []
        attack_patterns = ''
        
        if executive_summary and 'ai_summary' in executive_summary:
            ai_summary = executive_summary['ai_summary']
            risk_assessment = ai_summary.get('risk_assessment', {})
            overall_risk = risk_assessment.get('overall_risk', 'Unknown')
            risk_score = risk_assessment.get('risk_score', 0)
            risk_factors = risk_assessment.get('risk_factors', [])
            
            recommendations = ai_summary.get('recommendations', {})
            immediate_actions = recommendations.get('immediate_actions', [])
            long_term_improvements = recommendations.get('long_term_improvements', [])
            
            next_steps = ai_summary.get('next_steps', {})
            follow_up_investigations = next_steps.get('follow_up_investigations', [])
            additional_queries = next_steps.get('additional_queries', [])
            
            threat_landscape = ai_summary.get('threat_landscape', {})
            attack_patterns = threat_landscape.get('attack_patterns', '')
        
        # Calculate time span
        time_span = 'N/A'
        if statistics.get('first_finding_timestamp') and statistics.get('last_finding_timestamp'):
            try:
                from dateutil.parser import parse
                first = parse(statistics['first_finding_timestamp'])
                last = parse(statistics['last_finding_timestamp'])
                delta = last - first
                time_span = f"{delta.days} days, {delta.seconds // 3600} hours"
            except Exception:
                pass
        
        template_context = {
            'report_id': f"final_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'time_range': context.get('time_range', 'N/A') if context else 'N/A',
            'total_findings': statistics['total_findings'],
            'playbooks_executed': ', '.join(context.get('playbooks_executed', [])) if context else 'N/A',
            'report_status': 'Deanonymized' if self.deanonymizer else 'Anonymized',
            'executive_summary_text': executive_summary_text or 'Executive summary not available.',
            'critical_count': statistics['critical_count'],
            'high_severity_count': statistics['high_severity_count'],
            'medium_severity_count': statistics['medium_severity_count'],
            'low_severity_count': statistics['low_severity_count'],
            'overall_risk': overall_risk,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'critical_findings': critical_with_index,
            'findings': findings_with_index,
            'techniques_detected': statistics['techniques_detected'],
            'tactics_observed': statistics['tactics_observed'],
            'attack_patterns': attack_patterns,
            'immediate_actions': immediate_actions,
            'long_term_improvements': long_term_improvements,
            'follow_up_investigations': follow_up_investigations,
            'additional_queries': additional_queries,
            'recommended_playbooks': recommended_playbooks,
            'critical_percentage': statistics['critical_percentage'],
            'high_percentage': statistics['high_percentage'],
            'medium_percentage': statistics['medium_percentage'],
            'low_percentage': statistics['low_percentage'],
            'unique_techniques_count': statistics['unique_techniques_count'],
            'unique_tactics_count': statistics['unique_tactics_count'],
            'average_confidence': statistics['average_confidence'],
            'high_confidence_count': statistics['high_confidence_count'],
            'medium_confidence_count': statistics['medium_confidence_count'],
            'low_confidence_count': statistics['low_confidence_count'],
            'new_count': statistics['new_count'],
            'investigating_count': statistics['investigating_count'],
            'confirmed_count': statistics['confirmed_count'],
            'false_positive_count': statistics['false_positive_count'],
            'resolved_count': statistics['resolved_count'],
            'first_finding_timestamp': statistics.get('first_finding_timestamp', 'N/A'),
            'last_finding_timestamp': statistics.get('last_finding_timestamp', 'N/A'),
            'time_span': time_span,
            'data_sources': statistics['data_sources'],
            'playbook_executions': statistics['playbook_executions'],
            'report_version': '1.0',
            'generated_by': 'Threat Hunting System',
            'model_used': executive_summary.get('ai_summary', {}).get('model_used', 'N/A') if executive_summary else 'N/A',
            'anonymization_status': 'Deanonymized' if self.deanonymizer else 'Anonymized',
            'data_status': 'Real Data (Deanonymized)' if self.deanonymizer else 'Anonymized Data'
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
                if key == 'critical_findings' or key == 'findings':
                    findings_text = []
                    for finding in value:
                        finding_text = f"### Finding {finding.get('index', 'N/A')}: {finding.get('title', 'N/A')}\n\n"
                        finding_text += f"- **Finding ID:** {finding.get('finding_id', 'N/A')}\n"
                        finding_text += f"- **MITRE ATT&CK Technique:** {finding.get('technique_id', 'N/A')} - {finding.get('technique_name', 'N/A')}\n"
                        finding_text += f"- **Tactic:** {finding.get('tactic', 'N/A')}\n"
                        finding_text += f"- **Severity:** {finding.get('severity', 'N/A')}\n"
                        finding_text += f"- **Confidence:** {finding.get('confidence', 'N/A')}\n"
                        finding_text += f"- **Status:** {finding.get('status', 'N/A')}\n"
                        finding_text += f"- **Timestamp:** {finding.get('timestamp', 'N/A')}\n"
                        finding_text += f"- **Source:** {finding.get('source', 'N/A')}\n"
                        if key == 'findings':
                            finding_text += f"- **Playbook ID:** {finding.get('playbook_id', 'N/A')}\n"
                            finding_text += f"- **Execution ID:** {finding.get('execution_id', 'N/A')}\n"
                        finding_text += "\n**Description:**\n"
                        finding_text += f"{finding.get('description', 'N/A')}\n\n"
                        
                        if finding.get('indicators'):
                            finding_text += "**Indicators of Compromise:**\n"
                            for indicator in finding['indicators']:
                                finding_text += f"- {indicator}\n"
                            finding_text += "\n"
                        
                        if finding.get('recommendations'):
                            finding_text += "**Recommendations:**\n"
                            for rec in finding['recommendations']:
                                finding_text += f"- {rec}\n"
                            finding_text += "\n"
                        
                        if finding.get('evidence_references'):
                            finding_text += "**Evidence References:**\n"
                            for ref in finding['evidence_references']:
                                finding_text += f"- Evidence ID: {ref.get('evidence_id', 'N/A')} (Type: {ref.get('evidence_type', 'N/A')}, Relevance: {ref.get('relevance_score', 'N/A')})\n"
                            finding_text += "\n"
                        
                        finding_text += "---\n\n"
                        findings_text.append(finding_text)
                    
                    result = re.sub(
                        r'\{\{#' + key + r'\}\}.*?\{\{/' + key + r'\}\}',
                        '\n'.join(findings_text),
                        result,
                        flags=re.DOTALL
                    )
                elif key in ['techniques_detected', 'tactics_observed', 'risk_factors', 'immediate_actions',
                            'long_term_improvements', 'follow_up_investigations', 'additional_queries',
                            'recommended_playbooks', 'data_sources', 'playbook_executions']:
                    items_text = []
                    for item in value:
                        if isinstance(item, dict):
                            if key == 'techniques_detected':
                                items_text.append(
                                    f"- **{item.get('technique_id', 'N/A')}:** {item.get('technique_name', 'N/A')}\n"
                                    f"  - Findings: {item.get('count', 0)}\n"
                                    f"  - Tactic: {item.get('tactic', 'N/A')}\n"
                                    f"  - Severity Distribution: Critical: {item.get('critical_count', 0)}, "
                                    f"High: {item.get('high_count', 0)}, Medium: {item.get('medium_count', 0)}, "
                                    f"Low: {item.get('low_count', 0)}"
                                )
                            elif key == 'tactics_observed':
                                items_text.append(f"- **{item.get('tactic', 'N/A')}:** {item.get('count', 0)} findings")
                            elif key == 'data_sources':
                                items_text.append(f"- **{item.get('source', 'N/A')}:** {item.get('count', 0)} findings")
                            elif key == 'playbook_executions':
                                items_text.append(
                                    f"- **Playbook:** {item.get('playbook_id', 'N/A')}\n"
                                    f"  - Technique: {item.get('technique_id', 'N/A')} - {item.get('technique_name', 'N/A')}\n"
                                    f"  - Tactic: {item.get('tactic', 'N/A')}\n"
                                    f"  - Findings Generated: {item.get('findings_count', 0)}\n"
                                    f"  - Execution Time: {item.get('execution_timestamp', 'N/A')}"
                                )
                            else:
                                items_text.append(f"- {item}")
                        else:
                            items_text.append(f"- {item}")
                    
                    result = re.sub(
                        r'\{\{#' + key + r'\}\}.*?\{\{/' + key + r'\}\}',
                        '\n'.join(items_text),
                        result,
                        flags=re.DOTALL
                    )
        
        # Clean up any remaining template syntax
        result = re.sub(r'\{\{[^}]+\}\}', '', result)
        
        return result

