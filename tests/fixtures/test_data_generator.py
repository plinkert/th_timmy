"""
Test data generator utilities.

Helper functions for generating test data for tests.
"""

import os
import tempfile
import random
import string
from pathlib import Path
from typing import List, Dict, Any


def generate_test_file(content: str = None, suffix: str = ".txt") -> str:
    """
    Generate a test file with content.
    
    Args:
        content: File content (default: random content)
        suffix: File suffix
    
    Returns:
        Path to generated test file
    """
    if content is None:
        content = f"Test content: {generate_random_string(20)}\n"
    
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="th_test_")
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        return path
    except Exception:
        os.close(fd)
        raise


def generate_test_script(commands: List[str] = None) -> str:
    """
    Generate a test bash script.
    
    Args:
        commands: List of commands to include in script
    
    Returns:
        Path to generated script file
    """
    if commands is None:
        commands = ["date", "echo 'Script executed successfully'"]
    
    script_content = "#!/bin/bash\n"
    script_content += "\n".join(commands)
    script_content += "\n"
    
    fd, path = tempfile.mkstemp(suffix=".sh", prefix="th_test_")
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(script_content)
        os.chmod(path, 0o755)
        return path
    except Exception:
        os.close(fd)
        raise


def generate_random_string(length: int = 10) -> str:
    """
    Generate random string.
    
    Args:
        length: String length
    
    Returns:
        Random string
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_test_commands(count: int = 10) -> List[Dict[str, str]]:
    """
    Generate list of test commands.
    
    Args:
        count: Number of commands to generate
    
    Returns:
        List of command dictionaries with 'vm_id' and 'command' keys
    """
    commands = [
        'echo "test"',
        'date',
        'whoami',
        'pwd',
        'ls -la /tmp | head -5',
        'uname -a',
        'hostname',
        'uptime',
        'df -h',
        'free -m',
    ]
    
    vm_ids = ['vm01', 'vm02', 'vm03', 'vm04']
    
    result = []
    for i in range(count):
        result.append({
            'vm_id': vm_ids[i % len(vm_ids)],
            'command': commands[i % len(commands)]
        })
    
    return result


def generate_test_config(vm_ips: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Generate test configuration.
    
    Args:
        vm_ips: Dictionary mapping VM IDs to IP addresses
    
    Returns:
        Test configuration dictionary
    """
    if vm_ips is None:
        vm_ips = {
            'vm01': '192.168.1.10',
            'vm02': '192.168.1.11',
            'vm03': '192.168.1.12',
            'vm04': '192.168.1.13',
        }
    
    config = {
        'vms': {
            vm_id: {
                'name': f'threat-hunt-{vm_id}',
                'ip': ip,
                'role': {
                    'vm01': 'ingest-parser',
                    'vm02': 'database',
                    'vm03': 'analysis-jupyter',
                    'vm04': 'orchestrator-n8n',
                }.get(vm_id, 'unknown'),
                'enabled': True,
                'ssh_user': 'thadmin',
                'ssh_port': 22,
            }
            for vm_id, ip in vm_ips.items()
        },
        'network': {
            'subnet': '192.168.1.0/24',
            'gateway': '192.168.1.1',
        },
        'hardening': {
            'ssh': {
                'port': 22,
                'timeout': 300,
            }
        }
    }
    
    return config


def cleanup_test_files(file_paths: List[str]) -> None:
    """
    Clean up test files.
    
    Args:
        file_paths: List of file paths to remove
    """
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass  # Ignore cleanup errors

