"""
AI Prompts - Prompt templates for AI service.

This module provides prompt templates for various AI operations including
findings validation, executive summary generation, and threat analysis.
"""

from typing import Dict, Any, List, Optional


class AIPrompts:
    """
    Prompt templates for AI service operations.
    
    Provides structured prompts for:
    - Findings validation
    - Executive summary generation
    - Threat analysis
    - Evidence analysis
    """
    
    @staticmethod
    def validate_finding_prompt(finding: Dict[str, Any]) -> str:
        """
        Generate prompt for validating a finding.
        
        Args:
            finding: Finding dictionary to validate
        
        Returns:
            Formatted prompt string
        """
        return f"""You are a cybersecurity expert reviewing a threat hunting finding. Analyze the following finding and provide validation feedback.

Finding Details:
- Finding ID: {finding.get('finding_id', 'N/A')}
- MITRE Technique: {finding.get('technique_id', 'N/A')} - {finding.get('technique_name', 'N/A')}
- Tactic: {finding.get('tactic', 'N/A')}
- Severity: {finding.get('severity', 'N/A')}
- Confidence: {finding.get('confidence', 'N/A')}
- Title: {finding.get('title', 'N/A')}
- Description: {finding.get('description', 'N/A')}
- Evidence Count: {finding.get('evidence_count', 0)}
- Indicators: {', '.join(finding.get('indicators', []))}
- Source: {finding.get('source', 'N/A')}

Please provide:
1. Validation Status: "valid", "needs_review", or "invalid"
2. Confidence Assessment: Is the confidence score appropriate? (0.0-1.0)
3. Severity Assessment: Is the severity level appropriate?
4. Evidence Quality: Are there sufficient evidence records?
5. Recommendations: Any additional recommendations for investigation?
6. False Positive Risk: What is the risk of this being a false positive? (low, medium, high)

Respond in JSON format:
{{
    "validation_status": "valid|needs_review|invalid",
    "confidence_assessment": {{
        "current": 0.0,
        "recommended": 0.0,
        "reason": "explanation"
    }},
    "severity_assessment": {{
        "current": "low|medium|high|critical",
        "recommended": "low|medium|high|critical",
        "reason": "explanation"
    }},
    "evidence_quality": {{
        "sufficient": true|false,
        "quality_score": 0.0,
        "recommendations": ["recommendation1", "recommendation2"]
    }},
    "additional_recommendations": ["recommendation1", "recommendation2"],
    "false_positive_risk": "low|medium|high",
    "overall_assessment": "detailed explanation"
}}"""
    
    @staticmethod
    def generate_executive_summary_prompt(
        findings: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate prompt for executive summary.
        
        Args:
            findings: List of findings to summarize
            context: Optional context information (time range, playbooks, etc.)
        
        Returns:
            Formatted prompt string
        """
        findings_summary = []
        for finding in findings[:20]:  # Limit to first 20 findings
            findings_summary.append(
                f"- {finding.get('technique_id', 'N/A')}: {finding.get('title', 'N/A')} "
                f"(Severity: {finding.get('severity', 'N/A')}, Confidence: {finding.get('confidence', 'N/A')})"
            )
        
        context_str = ""
        if context:
            context_str = f"""
Context:
- Time Range: {context.get('time_range', 'N/A')}
- Playbooks Executed: {', '.join(context.get('playbooks', []))}
- Total Findings: {context.get('total_findings', len(findings))}
- Analysis Date: {context.get('analysis_date', 'N/A')}
"""
        
        return f"""You are a cybersecurity analyst preparing an executive summary for threat hunting results. Generate a concise, actionable executive summary.

Findings Summary:
{chr(10).join(findings_summary)}
{context_str}

Please provide an executive summary in the following format:

1. Executive Summary (2-3 sentences)
   - High-level overview of the threat hunting exercise
   - Key findings and their significance

2. Critical Findings (Top 3-5 most severe)
   - List the most critical findings with brief descriptions
   - Include severity and confidence levels

3. Threat Landscape
   - Overview of MITRE ATT&CK techniques detected
   - Attack patterns and tactics observed

4. Risk Assessment
   - Overall risk level (Low, Medium, High, Critical)
   - Key risk factors

5. Recommendations
   - Immediate actions required
   - Long-term security improvements

6. Next Steps
   - Recommended follow-up investigations
   - Additional threat hunting queries

Respond in JSON format:
{{
    "executive_summary": "2-3 sentence overview",
    "critical_findings": [
        {{
            "finding_id": "id",
            "technique_id": "T####",
            "title": "title",
            "severity": "severity",
            "confidence": 0.0,
            "summary": "brief description"
        }}
    ],
    "threat_landscape": {{
        "techniques_detected": ["T####", "T####"],
        "tactics_observed": ["tactic1", "tactic2"],
        "attack_patterns": "description"
    }},
    "risk_assessment": {{
        "overall_risk": "Low|Medium|High|Critical",
        "risk_factors": ["factor1", "factor2"],
        "risk_score": 0.0
    }},
    "recommendations": {{
        "immediate_actions": ["action1", "action2"],
        "long_term_improvements": ["improvement1", "improvement2"]
    }},
    "next_steps": {{
        "follow_up_investigations": ["investigation1", "investigation2"],
        "additional_queries": ["query1", "query2"]
    }}
}}"""
    
    @staticmethod
    def analyze_evidence_prompt(evidence: Dict[str, Any]) -> str:
        """
        Generate prompt for analyzing evidence.
        
        Args:
            evidence: Evidence dictionary to analyze
        
        Returns:
            Formatted prompt string
        """
        return f"""You are a cybersecurity analyst analyzing evidence from a threat hunting exercise. Analyze the following evidence record.

Evidence Details:
- Evidence ID: {evidence.get('evidence_id', 'N/A')}
- Evidence Type: {evidence.get('evidence_type', 'N/A')}
- Source: {evidence.get('source', 'N/A')}
- Timestamp: {evidence.get('timestamp', 'N/A')}
- Normalized Fields: {str(evidence.get('normalized_fields', {}))[:500]}

Please provide:
1. Evidence Classification: What type of activity does this evidence represent?
2. Threat Indicators: What indicators of compromise (IOCs) are present?
3. Behavioral Analysis: What suspicious behaviors are observed?
4. Context: What is the context of this evidence?
5. Relevance: How relevant is this evidence to threat detection? (0.0-1.0)

Respond in JSON format:
{{
    "classification": "classification",
    "threat_indicators": ["indicator1", "indicator2"],
    "behavioral_analysis": "analysis",
    "context": "context description",
    "relevance_score": 0.0,
    "recommendations": ["recommendation1", "recommendation2"]
}}"""
    
    @staticmethod
    def correlate_findings_prompt(findings: List[Dict[str, Any]]) -> str:
        """
        Generate prompt for correlating multiple findings.
        
        Args:
            findings: List of findings to correlate
        
        Returns:
            Formatted prompt string
        """
        findings_list = []
        for finding in findings[:10]:  # Limit to first 10 findings
            findings_list.append(
                f"- {finding.get('finding_id', 'N/A')}: {finding.get('technique_id', 'N/A')} "
                f"({finding.get('severity', 'N/A')}, {finding.get('confidence', 'N/A')})"
            )
        
        return f"""You are a cybersecurity analyst correlating multiple threat hunting findings. Analyze the relationships between these findings.

Findings:
{chr(10).join(findings_list)}

Please provide:
1. Correlation Analysis: Are these findings related? Do they indicate a coordinated attack?
2. Attack Chain: Can you identify an attack chain or kill chain?
3. Common Indicators: What indicators are common across findings?
4. Timeline: What is the timeline of these findings?
5. Threat Actor Profile: Do these findings suggest a specific threat actor or attack pattern?

Respond in JSON format:
{{
    "correlated": true|false,
    "correlation_strength": 0.0,
    "attack_chain": [
        {{
            "stage": "stage",
            "technique_id": "T####",
            "finding_id": "id",
            "description": "description"
        }}
    ],
    "common_indicators": ["indicator1", "indicator2"],
    "timeline": {{
        "start": "timestamp",
        "end": "timestamp",
        "duration": "duration"
    }},
    "threat_actor_profile": {{
        "suggested_actor": "actor name or unknown",
        "attack_pattern": "pattern description",
        "confidence": 0.0
    }},
    "recommendations": ["recommendation1", "recommendation2"]
}}"""
    
    @staticmethod
    def enhance_finding_description_prompt(finding: Dict[str, Any]) -> str:
        """
        Generate prompt for enhancing finding description.
        
        Args:
            finding: Finding dictionary to enhance
        
        Returns:
            Formatted prompt string
        """
        return f"""You are a cybersecurity expert enhancing a threat hunting finding description. Improve the description to be more detailed and actionable.

Current Finding:
- Technique: {finding.get('technique_id', 'N/A')} - {finding.get('technique_name', 'N/A')}
- Current Description: {finding.get('description', 'N/A')}
- Evidence Count: {finding.get('evidence_count', 0)}
- Indicators: {', '.join(finding.get('indicators', []))}

Please provide an enhanced description that:
1. Is more detailed and specific
2. Includes context about the threat
3. Explains the significance of the finding
4. Provides actionable information for investigation
5. References MITRE ATT&CK framework appropriately

Respond in JSON format:
{{
    "enhanced_description": "enhanced description text",
    "key_points": ["point1", "point2", "point3"],
    "mitre_context": "MITRE ATT&CK context",
    "investigation_guidance": "guidance for investigation"
}}"""

