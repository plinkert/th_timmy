"""
Audit logger for remote execution operations.

Logs each operation with: user_id, vm_id, command/operation, start/end time, status, exit_code.
No passwords or raw keys are ever logged.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

# Module-level logger; can be redirected to file/database via app config
_logger: Optional[logging.Logger] = None


def get_audit_logger() -> logging.Logger:
    """Return the audit logger instance. Creates one if not set."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger("remote_executor.audit")
        if not _logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            _logger.addHandler(h)
            _logger.setLevel(logging.INFO)
    return _logger


def set_audit_logger(logger: logging.Logger) -> None:
    """Set the audit logger (e.g. from application config)."""
    global _logger
    _logger = logger


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_operation(
    user_id: str,
    vm_id: str,
    operation: str,
    start_utc: str,
    end_utc: str,
    status: str,
    exit_code: Optional[int] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """
    Write an audit log entry for a remote execution operation.

    Logged fields: user_id, vm_id, operation, start_utc, end_utc, status, exit_code (if any).
    extra is merged into the log record but must not contain secrets.
    """
    log = get_audit_logger()
    msg_parts = [
        f"user_id={user_id}",
        f"vm_id={vm_id}",
        f"operation={operation}",
        f"start={start_utc}",
        f"end={end_utc}",
        f"status={status}",
    ]
    if exit_code is not None:
        msg_parts.append(f"exit_code={exit_code}")
    if extra:
        safe_extra = {k: v for k, v in extra.items() if k not in ("password", "key", "secret")}
        msg_parts.append(f"extra={safe_extra}")
    log.info(" | ".join(msg_parts))
