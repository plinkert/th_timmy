"""
Query Generator - Automatic query generation for threat hunting.

This module provides functionality for generating ready-to-use queries
based on selected MITRE ATT&CK techniques and available SIEM/EDR tools.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import yaml

from .query_templates import QueryTemplates, QueryTool, QueryMode


class QueryGeneratorError(Exception):
    """Base exception for query generator errors."""
    pass


class QueryGenerator:
    """
    Query generator for threat hunting.
    
    Generates ready-to-use queries based on:
    - Selected MITRE ATT&CK techniques
    - Available SIEM/EDR tools
    - Playbook metadata
    - User parameters (time range, severity, etc.)
    """
    
    def __init__(
        self,
        playbooks_dir: Optional[Union[str, Path]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Query Generator.
        
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
        
        self.logger.info(f"QueryGenerator initialized with playbooks_dir: {self.playbooks_dir}")
    
    def discover_playbooks(self) -> List[Dict[str, Any]]:
        """
        Discover all available playbooks.
        
        Returns:
            List of playbook metadata dictionaries
        """
        playbooks = []
        
        if not self.playbooks_dir.exists():
            self.logger.warning(f"Playbooks directory does not exist: {self.playbooks_dir}")
            return playbooks
        
        for playbook_dir in self.playbooks_dir.iterdir():
            if not playbook_dir.is_dir():
                continue
            
            # Skip template and master-playbook
            if playbook_dir.name in ['template', 'master-playbook']:
                continue
            
            metadata_file = playbook_dir / "metadata.yml"
            if not metadata_file.exists():
                continue
            
            try:
                with open(metadata_file, 'r') as f:
                    metadata = yaml.safe_load(f)
                
                playbook_info = {
                    'id': metadata.get('playbook', {}).get('id', playbook_dir.name),
                    'name': metadata.get('playbook', {}).get('name', playbook_dir.name),
                    'version': metadata.get('playbook', {}).get('version', '1.0.0'),
                    'technique_id': metadata.get('mitre', {}).get('technique_id', ''),
                    'technique_name': metadata.get('mitre', {}).get('technique_name', ''),
                    'tactic': metadata.get('mitre', {}).get('tactic', ''),
                    'path': playbook_dir,
                    'metadata': metadata
                }
                
                playbooks.append(playbook_info)
                
            except Exception as e:
                self.logger.error(f"Error loading playbook {playbook_dir.name}: {e}")
                continue
        
        # Sort by technique ID
        playbooks.sort(key=lambda x: x.get('technique_id', ''))
        
        self.logger.info(f"Discovered {len(playbooks)} playbooks")
        return playbooks
    
    def get_playbooks_for_techniques(
        self,
        technique_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get playbooks for specified MITRE techniques.
        
        Args:
            technique_ids: List of MITRE technique IDs (e.g., ["T1566", "T1059"])
        
        Returns:
            List of matching playbooks
        """
        all_playbooks = self.discover_playbooks()
        
        matching = []
        for playbook in all_playbooks:
            playbook_technique = playbook.get('technique_id', '')
            if playbook_technique in technique_ids:
                matching.append(playbook)
        
        self.logger.info(
            f"Found {len(matching)} playbooks for techniques: {technique_ids}"
        )
        return matching
    
    def get_available_tools(
        self,
        playbooks: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Get list of available tools from playbooks.
        
        Args:
            playbooks: Optional list of playbooks (if None, discovers all)
        
        Returns:
            List of unique tool names
        """
        if playbooks is None:
            playbooks = self.discover_playbooks()
        
        tools = set()
        for playbook in playbooks:
            metadata = playbook.get('metadata', {})
            data_sources = metadata.get('data_sources', [])
            
            for data_source in data_sources:
                tool_name = data_source.get('name', '')
                if tool_name:
                    tools.add(tool_name)
        
        tools_list = sorted(list(tools))
        self.logger.info(f"Found {len(tools_list)} available tools: {tools_list}")
        return tools_list
    
    def generate_queries(
        self,
        technique_ids: List[str],
        tool_names: List[str],
        mode: str = "manual",
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate queries for specified techniques and tools.
        
        Args:
            technique_ids: List of MITRE technique IDs
            tool_names: List of tool names (e.g., ["Microsoft Defender for Endpoint", "Splunk"])
            mode: Query mode ("manual" or "api")
            parameters: Optional parameters to replace in queries (e.g., {"time_range": "30d"})
        
        Returns:
            Dictionary with generated queries organized by technique and tool
        """
        if parameters is None:
            parameters = {}
        
        # Set default parameters
        default_params = {
            'time_range': '7d',
            'severity': 'high',
            'index': 'security',
            'workspace': 'your-workspace'
        }
        default_params.update(parameters)
        parameters = default_params
        
        # Validate mode
        if mode not in ['manual', 'api']:
            raise QueryGeneratorError(f"Invalid mode: {mode}. Must be 'manual' or 'api'")
        
        query_mode = QueryMode.MANUAL if mode == "manual" else QueryMode.API
        
        # Get playbooks for techniques
        playbooks = self.get_playbooks_for_techniques(technique_ids)
        
        if not playbooks:
            self.logger.warning(f"No playbooks found for techniques: {technique_ids}")
            return {
                'techniques': technique_ids,
                'tools': tool_names,
                'mode': mode,
                'queries': {},
                'warnings': [f"No playbooks found for techniques: {technique_ids}"]
            }
        
        # Generate queries
        result = {
            'techniques': technique_ids,
            'tools': tool_names,
            'mode': mode,
            'parameters': parameters,
            'queries': {},
            'warnings': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for playbook in playbooks:
            technique_id = playbook.get('technique_id', '')
            technique_name = playbook.get('technique_name', '')
            playbook_name = playbook.get('name', '')
            playbook_path = playbook.get('path')
            metadata = playbook.get('metadata', {})
            
            if technique_id not in result['queries']:
                result['queries'][technique_id] = {
                    'technique_name': technique_name,
                    'playbook_name': playbook_name,
                    'tools': {}
                }
            
            # Get queries from playbook metadata
            data_sources = metadata.get('data_sources', [])
            
            for data_source in data_sources:
                tool_name = data_source.get('name', '')
                
                # Check if this tool is requested
                if tool_name not in tool_names:
                    continue
                
                # Get queries for this tool
                queries = data_source.get('queries', {})
                mode_queries = queries.get(mode, [])
                
                if not mode_queries:
                    # No query found in playbook, use template
                    query_tool = QueryTemplates.get_tool_from_name(tool_name)
                    if query_tool:
                        query_text = QueryTemplates.get_template(
                            query_tool,
                            query_mode,
                            technique_id,
                            technique_name
                        )
                        result['queries'][technique_id]['tools'][tool_name] = {
                            'source': 'template',
                            'query': self._replace_parameters(query_text, parameters),
                            'instructions': f"Template query for {tool_name}. Customize as needed."
                        }
                        result['warnings'].append(
                            f"No {mode} query found in playbook for {technique_id} - {tool_name}, using template"
                        )
                    else:
                        result['warnings'].append(
                            f"Tool not supported: {tool_name} for {technique_id}"
                        )
                    continue
                
                # Use first available query (can be extended to support multiple queries)
                query_def = mode_queries[0]
                query_file = query_def.get('file', '')
                
                # Load query from file
                query_text = self._load_query_file(playbook_path, query_file)
                
                if not query_text:
                    # Fallback to template
                    query_tool = QueryTemplates.get_tool_from_name(tool_name)
                    if query_tool:
                        query_text = QueryTemplates.get_template(
                            query_tool,
                            query_mode,
                            technique_id,
                            technique_name
                        )
                        result['warnings'].append(
                            f"Query file not found: {query_file}, using template for {technique_id} - {tool_name}"
                        )
                    else:
                        result['warnings'].append(
                            f"Could not load query for {technique_id} - {tool_name}"
                        )
                        continue
                
                # Replace parameters in query
                query_text = self._replace_parameters(query_text, parameters)
                
                # Store query
                result['queries'][technique_id]['tools'][tool_name] = {
                    'source': 'playbook',
                    'name': query_def.get('name', ''),
                    'description': query_def.get('description', ''),
                    'query': query_text,
                    'instructions': query_def.get('instructions', ''),
                    'expected_fields': query_def.get('expected_fields', []),
                    'api_endpoint': query_def.get('api_endpoint') if mode == 'api' else None,
                    'api_method': query_def.get('api_method') if mode == 'api' else None,
                    'api_authentication': query_def.get('api_authentication') if mode == 'api' else None
                }
        
        self.logger.info(
            f"Generated queries for {len(result['queries'])} techniques and {len(tool_names)} tools"
        )
        
        return result
    
    def _load_query_file(
        self,
        playbook_path: Path,
        query_file: str
    ) -> Optional[str]:
        """
        Load query from file.
        
        Args:
            playbook_path: Path to playbook directory
            query_file: Relative path to query file
        
        Returns:
            Query text or None if file not found
        """
        if not query_file:
            return None
        
        query_path = playbook_path / query_file
        
        if not query_path.exists():
            self.logger.warning(f"Query file not found: {query_path}")
            return None
        
        try:
            with open(query_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading query file {query_path}: {e}")
            return None
    
    def _replace_parameters(
        self,
        query_text: str,
        parameters: Dict[str, Any]
    ) -> str:
        """
        Replace placeholders in query text with actual parameter values.
        
        Args:
            query_text: Query text with placeholders like {{time_range}}
            parameters: Dictionary of parameter values
        
        Returns:
            Query text with replaced parameters
        """
        result = query_text
        
        # Replace {{parameter}} placeholders
        for param_name, param_value in parameters.items():
            # Handle both {{param}} and {{{{param}}}} (double braces for JSON)
            patterns = [
                f"{{{{{{{{{{{{param_name}}}}}}}}}}}}",  # {{{{param}}}}
                f"{{{{{{{{param_name}}}}}}}}",  # {{{{param}}}}
                f"{{{{param_name}}}}",  # {{param}}
            ]
            
            for pattern in patterns:
                result = result.replace(pattern, str(param_value))
        
        return result
    
    def get_query_summary(
        self,
        technique_ids: Optional[List[str]] = None,
        tool_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get summary of available queries.
        
        Args:
            technique_ids: Optional filter by technique IDs
            tool_names: Optional filter by tool names
        
        Returns:
            Summary dictionary
        """
        if technique_ids:
            playbooks = self.get_playbooks_for_techniques(technique_ids)
        else:
            playbooks = self.discover_playbooks()
        
        summary = {
            'total_playbooks': len(playbooks),
            'techniques': {},
            'tools': set(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for playbook in playbooks:
            technique_id = playbook.get('technique_id', '')
            technique_name = playbook.get('technique_name', '')
            metadata = playbook.get('metadata', {})
            data_sources = metadata.get('data_sources', [])
            
            if technique_id not in summary['techniques']:
                summary['techniques'][technique_id] = {
                    'technique_name': technique_name,
                    'tools': set(),
                    'has_manual': False,
                    'has_api': False
                }
            
            for data_source in data_sources:
                tool_name = data_source.get('name', '')
                if tool_names and tool_name not in tool_names:
                    continue
                
                summary['tools'].add(tool_name)
                summary['techniques'][technique_id]['tools'].add(tool_name)
                
                queries = data_source.get('queries', {})
                if queries.get('manual'):
                    summary['techniques'][technique_id]['has_manual'] = True
                if queries.get('api'):
                    summary['techniques'][technique_id]['has_api'] = True
        
        # Convert sets to lists for JSON serialization
        summary['tools'] = sorted(list(summary['tools']))
        for tech_info in summary['techniques'].values():
            tech_info['tools'] = sorted(list(tech_info['tools']))
        
        return summary

