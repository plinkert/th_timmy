"""
AI Service - OpenAI API integration for threat hunting.

This module provides AI-powered services for:
- Findings validation
- Executive summary generation
- Evidence analysis
- Finding correlation
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .ai_prompts import AIPrompts

# Try relative import first, fallback to direct import if relative import fails
try:
    from ..utils.deterministic_anonymizer import DeterministicAnonymizer, DeterministicAnonymizerError
except (ImportError, ValueError):
    from utils.deterministic_anonymizer import DeterministicAnonymizer, DeterministicAnonymizerError


class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass


class AIService:
    """
    AI service for threat hunting operations.
    
    Provides AI-powered analysis using OpenAI API:
    - Findings validation
    - Executive summary generation
    - Evidence analysis
    - Finding correlation
    - Description enhancement
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        anonymizer: Optional[DeterministicAnonymizer] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize AI Service.
        
        Args:
            api_key: OpenAI API key (default: from environment or config)
            model: OpenAI model to use (default: "gpt-4")
            temperature: Temperature for generation (default: 0.3)
            max_tokens: Maximum tokens for response (default: 2000)
            anonymizer: Optional anonymizer for data anonymization
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        if not OPENAI_AVAILABLE:
            raise AIServiceError(
                "OpenAI library is not available. Install with: pip install openai>=1.0.0"
            )
        
        # Get API key
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise AIServiceError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        
        # Configuration
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Anonymizer for data anonymization before sending to AI
        self.anonymizer = anonymizer
        
        # Prompts
        self.prompts = AIPrompts()
        
        self.logger.info(f"AIService initialized with model: {model}")
    
    def validate_finding(
        self,
        finding: Dict[str, Any],
        anonymize: bool = True
    ) -> Dict[str, Any]:
        """
        Validate a finding using AI.
        
        Args:
            finding: Finding dictionary to validate
            anonymize: Whether to anonymize data before sending to AI
        
        Returns:
            Validation result dictionary
        """
        try:
            # Anonymize finding if requested
            finding_to_validate = finding.copy()
            if anonymize and self.anonymizer:
                self.logger.debug("Anonymizing finding before AI validation")
                finding_to_validate = self.anonymizer.anonymize_record(finding_to_validate)
            
            # Generate prompt
            prompt = self.prompts.validate_finding_prompt(finding_to_validate)
            
            # Call OpenAI API
            response = self._call_openai(prompt)
            
            # Parse response
            validation_result = self._parse_json_response(response)
            
            # Add metadata
            validation_result['validation_timestamp'] = datetime.utcnow().isoformat()
            validation_result['model_used'] = self.model
            validation_result['finding_id'] = finding.get('finding_id')
            
            self.logger.info(f"Finding {finding.get('finding_id')} validated: {validation_result.get('validation_status')}")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating finding: {e}")
            raise AIServiceError(f"Failed to validate finding: {e}")
    
    def generate_executive_summary(
        self,
        findings: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        anonymize: bool = True
    ) -> Dict[str, Any]:
        """
        Generate executive summary for findings.
        
        Args:
            findings: List of findings to summarize
            context: Optional context information
            anonymize: Whether to anonymize data before sending to AI
        
        Returns:
            Executive summary dictionary
        """
        try:
            # Anonymize findings if requested
            findings_to_summarize = findings.copy()
            if anonymize and self.anonymizer:
                self.logger.debug("Anonymizing findings before AI summary generation")
                findings_to_summarize = [
                    self.anonymizer.anonymize_record(f) for f in findings_to_summarize
                ]
            
            # Generate prompt
            prompt = self.prompts.generate_executive_summary_prompt(
                findings=findings_to_summarize,
                context=context
            )
            
            # Call OpenAI API
            response = self._call_openai(prompt)
            
            # Parse response
            summary = self._parse_json_response(response)
            
            # Add metadata
            summary['generated_at'] = datetime.utcnow().isoformat()
            summary['model_used'] = self.model
            summary['findings_count'] = len(findings)
            
            self.logger.info(f"Executive summary generated for {len(findings)} findings")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating executive summary: {e}")
            raise AIServiceError(f"Failed to generate executive summary: {e}")
    
    def analyze_evidence(
        self,
        evidence: Dict[str, Any],
        anonymize: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze evidence using AI.
        
        Args:
            evidence: Evidence dictionary to analyze
            anonymize: Whether to anonymize data before sending to AI
        
        Returns:
            Analysis result dictionary
        """
        try:
            # Anonymize evidence if requested
            evidence_to_analyze = evidence.copy()
            if anonymize and self.anonymizer:
                self.logger.debug("Anonymizing evidence before AI analysis")
                evidence_to_analyze = self.anonymizer.anonymize_record(evidence_to_analyze)
            
            # Generate prompt
            prompt = self.prompts.analyze_evidence_prompt(evidence_to_analyze)
            
            # Call OpenAI API
            response = self._call_openai(prompt)
            
            # Parse response
            analysis = self._parse_json_response(response)
            
            # Add metadata
            analysis['analysis_timestamp'] = datetime.utcnow().isoformat()
            analysis['model_used'] = self.model
            analysis['evidence_id'] = evidence.get('evidence_id')
            
            self.logger.info(f"Evidence {evidence.get('evidence_id')} analyzed")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing evidence: {e}")
            raise AIServiceError(f"Failed to analyze evidence: {e}")
    
    def correlate_findings(
        self,
        findings: List[Dict[str, Any]],
        anonymize: bool = True
    ) -> Dict[str, Any]:
        """
        Correlate multiple findings using AI.
        
        Args:
            findings: List of findings to correlate
            anonymize: Whether to anonymize data before sending to AI
        
        Returns:
            Correlation result dictionary
        """
        try:
            # Anonymize findings if requested
            findings_to_correlate = findings.copy()
            if anonymize and self.anonymizer:
                self.logger.debug("Anonymizing findings before AI correlation")
                findings_to_correlate = [
                    self.anonymizer.anonymize_record(f) for f in findings_to_correlate
                ]
            
            # Generate prompt
            prompt = self.prompts.correlate_findings_prompt(findings_to_correlate)
            
            # Call OpenAI API
            response = self._call_openai(prompt)
            
            # Parse response
            correlation = self._parse_json_response(response)
            
            # Add metadata
            correlation['correlation_timestamp'] = datetime.utcnow().isoformat()
            correlation['model_used'] = self.model
            correlation['findings_count'] = len(findings)
            
            self.logger.info(f"Correlated {len(findings)} findings")
            
            return correlation
            
        except Exception as e:
            self.logger.error(f"Error correlating findings: {e}")
            raise AIServiceError(f"Failed to correlate findings: {e}")
    
    def enhance_finding_description(
        self,
        finding: Dict[str, Any],
        anonymize: bool = True
    ) -> Dict[str, Any]:
        """
        Enhance finding description using AI.
        
        Args:
            finding: Finding dictionary to enhance
            anonymize: Whether to anonymize data before sending to AI
        
        Returns:
            Enhanced description dictionary
        """
        try:
            # Anonymize finding if requested
            finding_to_enhance = finding.copy()
            if anonymize and self.anonymizer:
                self.logger.debug("Anonymizing finding before AI enhancement")
                finding_to_enhance = self.anonymizer.anonymize_record(finding_to_enhance)
            
            # Generate prompt
            prompt = self.prompts.enhance_finding_description_prompt(finding_to_enhance)
            
            # Call OpenAI API
            response = self._call_openai(prompt)
            
            # Parse response
            enhancement = self._parse_json_response(response)
            
            # Add metadata
            enhancement['enhanced_at'] = datetime.utcnow().isoformat()
            enhancement['model_used'] = self.model
            enhancement['finding_id'] = finding.get('finding_id')
            
            self.logger.info(f"Finding {finding.get('finding_id')} description enhanced")
            
            return enhancement
            
        except Exception as e:
            self.logger.error(f"Error enhancing finding description: {e}")
            raise AIServiceError(f"Failed to enhance finding description: {e}")
    
    def _call_openai(self, prompt: str) -> str:
        """
        Call OpenAI API with prompt.
        
        Args:
            prompt: Prompt string
        
        Returns:
            Response text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a cybersecurity expert specializing in threat hunting and MITRE ATT&CK framework."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise AIServiceError(f"OpenAI API call failed: {e}")
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from OpenAI.
        
        Args:
            response: Response text (may contain JSON)
        
        Returns:
            Parsed JSON dictionary
        """
        try:
            # Try to extract JSON from response
            # Sometimes responses include markdown code blocks
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            # Remove leading/trailing whitespace and parse
            json_str = json_str.strip()
            if json_str.startswith("{"):
                return json.loads(json_str)
            else:
                # If no JSON found, return as text
                return {"response": json_str}
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON response: {e}")
            # Return response as text if JSON parsing fails
            return {"response": response, "parse_error": str(e)}

