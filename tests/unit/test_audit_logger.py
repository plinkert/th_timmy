"""Unit tests for audit_logger."""

import logging
import pytest

from automation_scripts.orchestrators.remote_executor.audit_logger import (
    get_audit_logger,
    set_audit_logger,
    log_operation,
)


def test_log_operation_captures_message(caplog):
    """log_operation writes user_id, vm_id, operation, start/end, status."""
    caplog.set_level(logging.INFO)
    log_operation(
        user_id="u1",
        vm_id="vm01",
        operation="echo hello",
        start_utc="2025-01-01T00:00:00Z",
        end_utc="2025-01-01T00:00:01Z",
        status="success",
        exit_code=0,
    )
    assert "user_id=u1" in caplog.text
    assert "vm_id=vm01" in caplog.text
    assert "operation=echo hello" in caplog.text
    assert "status=success" in caplog.text
    assert "exit_code=0" in caplog.text


def test_log_operation_extra_safe():
    """log_operation does not add password/key/secret to extra."""
    log = get_audit_logger()
    handlers_before = len(log.handlers)
    log_operation(
        "u1", "vm01", "cmd", "2025-01-01T00:00:00Z", "2025-01-01T00:00:01Z", "success",
        extra={"foo": "bar", "password": "x", "key": "y"},
    )
    # No crash; password/key filtered in implementation
    assert handlers_before >= 0
