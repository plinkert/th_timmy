"""
Configuration Validator - Advanced configuration validation.

This module provides comprehensive validation for different configuration types
including central config, VM-specific configs, and environment files.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import yaml


class ConfigValidatorError(Exception):
    """Base exception for configuration validator errors."""
    pass


class ConfigValidator:
    """
    Configuration validator with support for multiple configuration types.
    
    Provides validation for:
    - Central configuration (configs/config.yml)
    - VM-specific configurations (hosts/vmXX-*/config.yml)
    - Environment files (.env)
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize Configuration Validator.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def validate_config(
        self,
        config_data: Dict[str, Any],
        config_type: str = "central"
    ) -> Tuple[bool, List[str]]:
        """
        Validate configuration data.
        
        Args:
            config_data: Configuration dictionary
            config_type: Type of configuration ('central', 'vm', 'env')
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if config_type == "central":
            return self._validate_central_config(config_data)
        elif config_type == "vm":
            return self._validate_vm_config(config_data)
        elif config_type == "env":
            return self._validate_env_config(config_data)
        else:
            return False, [f"Unknown config type: {config_type}"]
    
    def _validate_central_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate central configuration.
        
        Args:
            config: Configuration dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required top-level keys
        required_keys = ['vms']
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required key: {key}")
        
        # Validate VMs section
        if 'vms' in config:
            vms = config['vms']
            if not isinstance(vms, dict):
                errors.append("'vms' must be a dictionary")
            else:
                # Check each VM has required fields
                for vm_id, vm_config in vms.items():
                    if not isinstance(vm_config, dict):
                        errors.append(f"VM '{vm_id}' configuration must be a dictionary")
                        continue
                    
                    # Required fields
                    if 'ip' not in vm_config:
                        errors.append(f"VM '{vm_id}' missing required field: 'ip'")
                    else:
                        # Validate IP address format
                        ip = vm_config['ip']
                        if not self._validate_ip_address(ip):
                            errors.append(f"VM '{vm_id}' has invalid IP address: {ip}")
                    
                    if 'role' not in vm_config:
                        errors.append(f"VM '{vm_id}' missing required field: 'role'")
                    else:
                        # Validate role
                        valid_roles = ['ingest-parser', 'database', 'analysis-jupyter', 'orchestrator-n8n']
                        if vm_config['role'] not in valid_roles:
                            errors.append(
                                f"VM '{vm_id}' has invalid role: {vm_config['role']}. "
                                f"Valid roles: {', '.join(valid_roles)}"
                            )
        
        # Validate network configuration if present
        if 'network' in config:
            network = config['network']
            if isinstance(network, dict):
                if 'subnet' in network:
                    if not self._validate_cidr(network['subnet']):
                        errors.append(f"Invalid subnet CIDR: {network['subnet']}")
                if 'gateway' in network:
                    if not self._validate_ip_address(network['gateway']):
                        errors.append(f"Invalid gateway IP: {network['gateway']}")
        
        # Validate database configuration if present
        if 'database' in config:
            db = config['database']
            if isinstance(db, dict):
                if 'port' in db:
                    port = db['port']
                    if not isinstance(port, int) or port < 1 or port > 65535:
                        errors.append(f"Invalid database port: {port}")
        
        # Validate YAML structure
        try:
            yaml.dump(config)
        except Exception as e:
            errors.append(f"Invalid YAML structure: {e}")
        
        return len(errors) == 0, errors
    
    def _validate_vm_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate VM-specific configuration.
        
        Args:
            config: Configuration dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # VM-specific configs can have different structures depending on VM role
        # Basic validation - check if it's a valid dictionary
        if not isinstance(config, dict):
            errors.append("VM configuration must be a dictionary")
            return False, errors
        
        # Validate PostgreSQL config if present (VM-02)
        if 'postgresql' in config:
            pg = config['postgresql']
            if isinstance(pg, dict):
                if 'port' in pg:
                    port = pg['port']
                    if not isinstance(port, int) or port < 1 or port > 65535:
                        errors.append(f"Invalid PostgreSQL port: {port}")
                
                if 'database_password' in pg:
                    password = pg['database_password']
                    if password == "CHANGE_ME_STRONG_PASSWORD" or len(password) < 8:
                        errors.append("PostgreSQL password must be changed and at least 8 characters")
        
        # Validate network configuration if present
        if 'network' in config:
            network = config['network']
            if isinstance(network, dict):
                if 'allowed_ips' in network:
                    allowed_ips = network['allowed_ips']
                    if isinstance(allowed_ips, list):
                        for ip in allowed_ips:
                            if not self._validate_cidr(ip):
                                errors.append(f"Invalid allowed IP CIDR: {ip}")
        
        # Validate YAML structure
        try:
            yaml.dump(config)
        except Exception as e:
            errors.append(f"Invalid YAML structure: {e}")
        
        return len(errors) == 0, errors
    
    def _validate_env_config(self, config_data: Any) -> Tuple[bool, List[str]]:
        """
        Validate environment file configuration.
        
        Args:
            config_data: Environment file content (string or dict)
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Environment files are typically key=value pairs
        if isinstance(config_data, str):
            # Parse env file
            lines = config_data.split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Check format: KEY=VALUE
                if '=' not in line:
                    errors.append(f"Line {line_num}: Invalid format (missing '=')")
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                
                # Validate key name (alphanumeric and underscores)
                if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
                    errors.append(f"Line {line_num}: Invalid environment variable name: {key}")
        
        elif isinstance(config_data, dict):
            # If it's already a dict, validate keys
            for key in config_data.keys():
                if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
                    errors.append(f"Invalid environment variable name: {key}")
        else:
            errors.append("Environment config must be a string or dictionary")
        
        return len(errors) == 0, errors
    
    def _validate_ip_address(self, ip: str) -> bool:
        """
        Validate IP address format.
        
        Args:
            ip: IP address string
        
        Returns:
            True if valid IP address
        """
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        
        parts = ip.split('.')
        for part in parts:
            try:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            except ValueError:
                return False
        
        return True
    
    def _validate_cidr(self, cidr: str) -> bool:
        """
        Validate CIDR notation.
        
        Args:
            cidr: CIDR string (e.g., "192.168.1.0/24")
        
        Returns:
            True if valid CIDR
        """
        if '/' not in cidr:
            return False
        
        ip, mask = cidr.split('/', 1)
        
        if not self._validate_ip_address(ip):
            return False
        
        try:
            mask_num = int(mask)
            if mask_num < 0 or mask_num > 32:
                return False
        except ValueError:
            return False
        
        return True
    
    def validate_config_file(
        self,
        config_path: str,
        config_type: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate configuration file.
        
        Args:
            config_path: Path to configuration file
            config_type: Type of configuration (auto-detected if None)
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            return False, [f"Configuration file not found: {config_path}"]
        
        # Auto-detect config type if not provided
        if config_type is None:
            if 'config.yml' in str(config_path) or 'config.yaml' in str(config_path):
                if 'vm' in str(config_path):
                    config_type = 'vm'
                else:
                    config_type = 'central'
            elif config_path.name == '.env' or config_path.suffix == '.env':
                config_type = 'env'
            else:
                return False, [f"Could not determine configuration type for: {config_path}"]
        
        try:
            if config_type == 'env':
                # Read as text for env files
                with open(config_path, 'r') as f:
                    config_data = f.read()
            else:
                # Read as YAML
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
            
            return self.validate_config(config_data, config_type)
            
        except yaml.YAMLError as e:
            return False, [f"YAML parsing error: {e}"]
        except Exception as e:
            return False, [f"Error reading configuration file: {e}"]

