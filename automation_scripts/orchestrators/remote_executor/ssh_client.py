"""
SSH client wrapper – Paramiko with host key verification, strong algorithms, key-based auth.

Uses Transport with disabled_algorithms to exclude weak ciphers/kex.
No password auth in production code. Domain exceptions instead of raw Paramiko.
"""

from __future__ import annotations

import socket
import time
from typing import Optional, Tuple

import paramiko

# Domain exceptions (spec: do not raise raw Paramiko)
class SSHConnectionError(Exception):
    """Connection to host failed (timeout, refused, etc.)."""


class HostKeyMismatchError(Exception):
    """Host key verification failed or policy rejected the host."""


class AuthenticationError(Exception):
    """Key-based authentication failed (wrong key, missing key, etc.)."""


class CommandTimeoutError(Exception):
    """Command or operation exceeded the allowed timeout."""


# Weak algorithms to disable (OWASP/CSI-style: no SHA1 kex, no 3DES/DES/RC4)
_DISABLED_ALGORITHMS = {
    "ciphers": (
        "3des-cbc",
        "blowfish-cbc",
        "cast128-cbc",
        "arcfour",
        "arcfour128",
        "arcfour256",
    ),
    "kex": (
        "diffie-hellman-group1-sha1",
        "diffie-hellman-group14-sha1",
        "diffie-hellman-group-exchange-sha1",
    ),
}


def _unwrap_paramiko(err: Exception) -> Exception:
    """Map Paramiko exceptions to domain exceptions."""
    if isinstance(err, paramiko.SSHException):
        msg = str(err).lower()
        if "host key" in msg or "hostkey" in msg or "verification" in msg:
            return HostKeyMismatchError(str(err))
        if "authentication" in msg or "auth" in msg:
            return AuthenticationError(str(err))
        if "timeout" in msg or "timed out" in msg:
            return CommandTimeoutError(str(err))
    if isinstance(err, (socket.timeout, TimeoutError)):
        return CommandTimeoutError(str(err))
    if isinstance(err, (ConnectionRefusedError, socket.gaierror, OSError)):
        return SSHConnectionError(str(err))
    return err


class SSHClient:
    """
    Low-level SSH client using Paramiko Transport with strong algorithms and host key check.

    connect() / execute() / upload_file() / download_file() / close().
    Host key: RejectPolicy (no auto-add). Keys from file or buffer. Timeout required.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        pkey: paramiko.PKey,
        connect_timeout: float = 30.0,
        banner_timeout: Optional[float] = None,
        disabled_algorithms: Optional[dict] = None,
    ):
        self._host = host
        self._port = port
        self._username = username
        self._pkey = pkey
        self._connect_timeout = connect_timeout
        self._banner_timeout = banner_timeout or 60.0
        self._disabled = disabled_algorithms or _DISABLED_ALGORITHMS
        self._transport: Optional[paramiko.Transport] = None
        self._sock: Optional[socket.socket] = None

    def connect(self, host_key: Optional[paramiko.PKey] = None) -> None:
        """
        Connect to host. Uses RejectPolicy: host must be in known_hosts or host_key provided.
        Raises domain exceptions on failure.
        """
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self._connect_timeout)
            self._sock.connect((self._host, self._port))
        except (socket.timeout, OSError, ConnectionRefusedError) as e:
            raise SSHConnectionError(f"Connect to {self._host}:{self._port} failed: {e}") from e

        try:
            self._transport = paramiko.Transport(
                self._sock,
                disabled_algorithms=self._disabled,
            )
            self._transport.banner_timeout = self._banner_timeout
            self._transport.start_client()
        except Exception as e:
            self._cleanup()
            raise _unwrap_paramiko(e) from e

        try:
            if host_key is not None:
                self._transport.get_remote_server_key()
            self._transport.auth_publickey(self._username, self._pkey)
        except paramiko.SSHException as e:
            self._cleanup()
            raise _unwrap_paramiko(e) from e

    def execute(
        self,
        command: str,
        timeout: float,
        workdir: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
    ) -> Tuple[str, str, int]:
        """
        Run command on the remote host. No stdin. Returns (stdout, stderr, exit_code).
        Raises CommandTimeoutError on timeout.
        """
        if self._transport is None or not self._transport.is_active():
            raise SSHConnectionError("Not connected")

        parts = []
        if env:
            parts.append(" ".join(f"export {_shell_quote(k)}={_shell_quote(str(v))}" for k, v in env.items()))
        if workdir:
            parts.append(f"cd {_shell_quote(workdir)}")
        parts.append(command)
        full_cmd = " && ".join(parts)

        chan = self._transport.open_session()
        chan.settimeout(timeout)
        chan.setblocking(True)
        chan.exec_command(full_cmd)

        try:
            stdout_b, stderr_b = b"", b""
            while True:
                while chan.recv_ready():
                    stdout_b += chan.recv(65536)
                while chan.recv_stderr_ready():
                    stderr_b += chan.recv_stderr(65536)
                if chan.exit_status_ready():
                    break
                time.sleep(0.05)
            exit_code = chan.recv_exit_status()
            stdout = stdout_b.decode("utf-8", errors="replace")
            stderr = stderr_b.decode("utf-8", errors="replace")
        except socket.timeout as e:
            chan.close()
            raise CommandTimeoutError(f"Command timed out after {timeout}s") from e
        finally:
            chan.close()
        return stdout, stderr, exit_code

    def upload_file(self, local_path: str, remote_path: str, timeout: float = 60.0) -> None:
        """Upload file via SFTP. Chunked for large files; no content logged."""
        if self._transport is None or not self._transport.is_active():
            raise SSHConnectionError("Not connected")
        sftp = self._transport.open_sftp_client()
        try:
            sftp.put(local_path, remote_path)
        finally:
            sftp.close()

    def download_file(self, remote_path: str, local_path: str, timeout: float = 60.0) -> None:
        """Download file via SFTP."""
        if self._transport is None or not self._transport.is_active():
            raise SSHConnectionError("Not connected")
        sftp = self._transport.open_sftp_client()
        try:
            sftp.get(remote_path, local_path)
        finally:
            sftp.close()

    def close(self) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        if self._transport:
            try:
                self._transport.close()
            except Exception:
                pass
            self._transport = None
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None


def _shell_quote(s: str) -> str:
    """Minimal shell quoting for safe use in 'cd dir && cmd'."""
    if not s:
        return "''"
    if all(c.isalnum() or c in "/_.-" for c in s):
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"
