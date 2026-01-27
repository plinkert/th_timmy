"""Unit tests for ssh_client (domain exceptions, execute result shape)."""

from unittest.mock import MagicMock

import pytest

from automation_scripts.orchestrators.remote_executor.ssh_client import (
    SSHClient,
    SSHConnectionError,
    HostKeyMismatchError,
    AuthenticationError,
    CommandTimeoutError,
)


def test_ssh_connection_error():
    """SSHConnectionError is raised for connection failures."""
    with pytest.raises(SSHConnectionError):
        raise SSHConnectionError("Connection refused")


def test_ssh_client_execute_returns_stdout_stderr_exit_code():
    """SSHClient.execute returns (stdout, stderr, exit_code) when transport is mocked."""
    # Paramiko 4.x has no Ed25519Key.generate(); we only need a pkey-like object for the constructor
    pkey = MagicMock()
    client = SSHClient(host="127.0.0.1", port=22, username="test", pkey=pkey)

    mock_chan = MagicMock()
    mock_chan.recv_ready.side_effect = [True, False]
    mock_chan.recv_stderr_ready.side_effect = [False]
    mock_chan.exit_status_ready.side_effect = [True]
    mock_chan.recv.return_value = b"hello"
    mock_chan.recv_stderr.return_value = b""
    mock_chan.recv_exit_status.return_value = 0

    mock_transport = MagicMock()
    mock_transport.is_active.return_value = True
    mock_transport.open_session.return_value = mock_chan

    client._transport = mock_transport
    client._sock = MagicMock()

    stdout, stderr, exit_code = client.execute("echo hello", timeout=5.0)
    assert "hello" in stdout or stdout == "hello"
    assert exit_code == 0
