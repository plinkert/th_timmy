"""
Report Generator - Generate reports with deanonymized data.

This module provides report generation with automatic deanonymization
before creating final reports for stakeholders.
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

from automation_scripts.utils.deanonymizer import Deanonymizer, DeanonymizerError
from automation_scripts.services.executive_summary_generator import (
    ExecutiveSummaryGenerator,
    ExecutiveSummaryGeneratorError
)


class ReportGeneratorError(Exception):
    """Base exception for report generator errors."""
    pass


class ReportGenerator:
    """
    Report Generator for creating final reports with deanonymized data.
    
    Provides report generation with:
    - Automatic deanonymization before reporting
    - Integration with Executive Summary Generator
    - Multiple report formats
    - Professional report structure
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        deanonymizer: Optional[Deanonymizer] = None,
        summary_generator: Optional[ExecutiveSummaryGenerator] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Report Generator.
        
        Args:
            config_path: Path to config.yml file
            deanonymizer: Optional Deanonymizer instance
            summary_generator: Optional ExecutiveSummaryGenerator instance
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
        
        self.logger.info("ReportGenerator initialized")
    
    def generate_report(
        self,
        findings: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        deanonymize: bool = True,
        include_executive_summary: bool = True,
        format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate a complete report with deanonymized data.
        
        Args:
            findings: List of findings to include in report
            context: Optional context information
            deanonymize: Whether to deanonymize data before reporting
            include_executive_summary: Whether to include AI-generated executive summary
            format: Output format ('markdown', 'json', 'both')
        
        Returns:
            Report dictionary
        """
        try:
            self.logger.info(f"Generating report for {len(findings)} findings")
            
            # Deanonymize findings if requested
            if deanonymize and self.deanonymizer:
                self.logger.info("Deanonymizing findings before report generation")
                findings = self.deanonymizer.deanonymize_findings(findings)
            elif deanonymize and not self.deanonymizer:
                self.logger.warning("Deanonymization requested but deanonymizer not available")
            
            # Generate executive summary if requested
            executive_summary = None
            if include_executive_summary and self.summary_generator:
                try:
                    self.logger.info("Generating executive summary")
                    summary_result = self.summary_generator.generate_summary(
                        findings=findings,
                        context=context,
                        format=format,
                        anonymize=False  # Already deanonymized
                    )
                    executive_summary = summary_result
                except Exception as e:
                    self.logger.warning(f"Failed to generate executive summary: {e}")
            
            # Prepare report
            report = {
                'report_id': f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'generated_at': datetime.utcnow().isoformat(),
                'findings_count': len(findings),
                'deanonymized': deanonymize,
                'context': context or {},
                'findings': findings,
                'executive_summary': executive_summary
            }
            
            # Add formatted content if markdown requested
            if format in ['markdown', 'both'] and executive_summary and 'markdown' in executive_summary:
                report['markdown'] = self._format_report_markdown(
                    findings=findings,
                    executive_summary=executive_summary.get('markdown', ''),
                    context=context
                )
            
            self.logger.info(f"Report generated: {report['report_id']}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            raise ReportGeneratorError(f"Failed to generate report: {e}")
    
    def generate_report_from_execution(
        self,
        execution_result: Dict[str, Any],
        deanonymize: bool = True,
        include_executive_summary: bool = True,
        format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate report from playbook execution result.
        
        Args:
            execution_result: Playbook execution result from PlaybookEngine
            deanonymize: Whether to deanonymize data before reporting
            include_executive_summary: Whether to include AI-generated executive summary
            format: Output format ('markdown', 'json', 'both')
        
        Returns:
            Report dictionary
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
        
        return self.generate_report(
            findings=findings,
            context=context,
            deanonymize=deanonymize,
            include_executive_summary=include_executive_summary,
            format=format
        )
    
    def save_report(
        self,
        report: Dict[str, Any],
        output_path: Optional[Path] = None,
        format: str = "markdown"
    ) -> Path:
        """
        Save report to file.
        
        Args:
            report: Report dictionary
            output_path: Optional output path (default: results/reports/)
            format: File format ('markdown', 'json', 'both')
        
        Returns:
            Path to saved file(s)
        """
        try:
            # Determine output path
            if output_path:
                output_file = Path(output_path)
            else:
                results_dir = project_root / "results" / "reports"
                results_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                output_file = results_dir / f"threat_hunting_report_{timestamp}"
            
            saved_files = []
            
            # Save markdown
            if format in ['markdown', 'both']:
                if 'markdown' in report:
                    md_file = output_file.with_suffix('.md')
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(report['markdown'])
                    saved_files.append(md_file)
                    self.logger.info(f"Markdown report saved: {md_file}")
                elif self.summary_generator and report.get('executive_summary'):
                    # Generate markdown from executive summary
                    summary = report['executive_summary']
                    if 'markdown' in summary:
                        md_file = output_file.with_suffix('.md')
                        with open(md_file, 'w', encoding='utf-8') as f:
                            f.write(summary['markdown'])
                        saved_files.append(md_file)
                        self.logger.info(f"Markdown report saved: {md_file}")
            
            # Save JSON
            if format in ['json', 'both']:
                import json
                json_file = output_file.with_suffix('.json')
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
                saved_files.append(json_file)
                self.logger.info(f"JSON report saved: {json_file}")
            
            return saved_files[0] if saved_files else output_file
            
        except Exception as e:
            self.logger.error(f"Error saving report: {e}")
            raise ReportGeneratorError(f"Failed to save report: {e}")
    
    def _format_report_markdown(
        self,
        findings: List[Dict[str, Any]],
        executive_summary: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Format complete report as markdown.
        
        Args:
            findings: List of findings
            executive_summary: Executive summary markdown
            context: Optional context information
        
        Returns:
            Formatted markdown report
        """
        report_lines = []
        
        # Header
        report_lines.append("# Threat Hunting Report")
        report_lines.append("")
        report_lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if context:
            if 'time_range' in context:
                report_lines.append(f"**Time Range:** {context['time_range']}")
            if 'playbooks_executed' in context:
                report_lines.append(f"**Playbooks Executed:** {', '.join(context['playbooks_executed'])}")
        report_lines.append(f"**Total Findings:** {len(findings)}")
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        # Executive Summary
        report_lines.append("## Executive Summary")
        report_lines.append("")
        report_lines.append(executive_summary)
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        # Findings Details
        report_lines.append("## Findings Details")
        report_lines.append("")
        
        for i, finding in enumerate(findings, 1):
            report_lines.append(f"### Finding {i}: {finding.get('title', 'N/A')}")
            report_lines.append("")
            report_lines.append(f"- **Finding ID:** {finding.get('finding_id', 'N/A')}")
            report_lines.append(f"- **Technique ID:** {finding.get('technique_id', 'N/A')}")
            report_lines.append(f"- **Technique Name:** {finding.get('technique_name', 'N/A')}")
            report_lines.append(f"- **Tactic:** {finding.get('tactic', 'N/A')}")
            report_lines.append(f"- **Severity:** {finding.get('severity', 'N/A')}")
            report_lines.append(f"- **Confidence:** {finding.get('confidence', 'N/A')}")
            report_lines.append(f"- **Status:** {finding.get('status', 'N/A')}")
            report_lines.append("")
            
            if finding.get('description'):
                report_lines.append(f"**Description:**")
                report_lines.append(f"{finding['description']}")
                report_lines.append("")
            
            if finding.get('indicators'):
                report_lines.append("**Indicators:**")
                for indicator in finding['indicators']:
                    report_lines.append(f"- {indicator}")
                report_lines.append("")
            
            if finding.get('recommendations'):
                report_lines.append("**Recommendations:**")
                for rec in finding['recommendations']:
                    report_lines.append(f"- {rec}")
                report_lines.append("")
            
            report_lines.append("---")
            report_lines.append("")
        
        # Footer
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("**Report Generated By:** Threat Hunting System")
        report_lines.append(f"**Report ID:** {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
        report_lines.append("**Data Status:** Deanonymized")
        
        return "\n".join(report_lines)

