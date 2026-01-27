"""
Remote Execution Service – secure remote command execution and file transfer from VM04.

Uses SSH (Paramiko) with key-based auth, strong algorithms, and host key verification.
Keys are provided by ssh_key_manager (this phase: ~/.ssh/th_timmy_keys).

Package path: automation_scripts (ticket path "automation-scripts" refers to this).
"""

from .remote_executor import (
    execute_remote_command,
    execute_remote_script,
    upload_file,
    download_file,
    RemoteExecutionResult,
)
from .ssh_client import (
    SSHConnectionError,
    HostKeyMismatchError,
    AuthenticationError,
    CommandTimeoutError,
)

__all__ = [
    "execute_remote_command",
    "execute_remote_script",
    "upload_file",
    "download_file",
    "RemoteExecutionResult",
    "SSHConnectionError",
    "HostKeyMismatchError",
    "AuthenticationError",
    "CommandTimeoutError",
]
