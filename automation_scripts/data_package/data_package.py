"""
Data Package (Step 1.5) – standard format for threat hunting pipeline data.

Unifies structures from different sources (manual/API). Validates with JSON Schema.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema
from jsonschema import Draft7Validator

logger = logging.getLogger(__name__)

MAX_DATA_PACKAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
DEFAULT_SCHEMA_PATH = "configs/schemas/data_package_schema.json"


class DataPackageValidationError(Exception):
    """Raised when DataPackage validation fails."""

    def __init__(self, message: str, errors: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.errors = errors or [message]


@dataclass
class DataPackage:
    """
    Standard data package for threat hunting pipeline.

    Fields: id, source, timestamp, data, anonymized, context.
    """

    id: str
    source: str
    timestamp: str
    data: List[Dict[str, Any]]
    anonymized: bool
    context: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON / schema validation."""
        return {
            "id": self.id,
            "source": self.source,
            "timestamp": self.timestamp,
            "data": self.data,
            "anonymized": self.anonymized,
            "context": self.context if self.context is not None else {},
        }

    def validate(
        self,
        schema_path: Optional[Path] = None,
        max_size_bytes: int = MAX_DATA_PACKAGE_SIZE_BYTES,
        require_anonymized_for_ai: bool = False,
    ) -> bool:
        """
        Validate against data_package_schema.json.
        Raises DataPackageValidationError on failure.
        Returns True on success.
        """
        if require_anonymized_for_ai and not self.anonymized:
            raise DataPackageValidationError(
                "anonymized must be True before AI processing",
                errors=["anonymized must be True before AI processing"],
            )

        d = self.to_dict()
        json_bytes = json.dumps(d).encode("utf-8")
        if len(json_bytes) > max_size_bytes:
            raise DataPackageValidationError(
                f"Data package size {len(json_bytes)} bytes exceeds limit {max_size_bytes}",
                errors=[f"Size {len(json_bytes)} > {max_size_bytes}"],
            )

        schema = _load_schema(schema_path)
        start = time.perf_counter()
        try:
            jsonschema.validate(d, schema)
            elapsed = time.perf_counter() - start
            logger.info("DataPackage %s validated in %.3f s", self.id, elapsed)
            return True
        except jsonschema.ValidationError as e:
            elapsed = time.perf_counter() - start
            errors = [str(err) for err in Draft7Validator(schema).iter_errors(d)]
            if not errors:
                errors = [str(e)]
            logger.warning("DataPackage %s validation failed in %.3f s: %s", self.id, elapsed, errors)
            raise DataPackageValidationError(
                f"Validation failed: {e.message}",
                errors=errors,
            ) from e

    @classmethod
    def from_dict(
        cls,
        d: dict,
        validate_on_load: bool = False,
        schema_path: Optional[Path] = None,
        **validate_kwargs: Any,
    ) -> "DataPackage":
        """Deserialize from dict. Optionally validate."""
        data = d.get("data")
        if not isinstance(data, list):
            raise DataPackageValidationError(
                f"data must be a list, got {type(data).__name__}",
                errors=["data must be array of objects"],
            )
        ctx = d.get("context")
        if ctx is None:
            ctx = {}
        inst = cls(
            id=str(d["id"]),
            source=str(d["source"]),
            timestamp=str(d["timestamp"]),
            data=data,
            anonymized=bool(d["anonymized"]),
            context=ctx if isinstance(ctx, dict) else {},
        )
        if validate_on_load:
            inst.validate(schema_path=schema_path, **validate_kwargs)
        return inst

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(
        cls,
        s: str,
        validate_on_load: bool = False,
        schema_path: Optional[Path] = None,
        **validate_kwargs: Any,
    ) -> "DataPackage":
        """Deserialize from JSON string."""
        d = json.loads(s)
        return cls.from_dict(d, validate_on_load=validate_on_load, schema_path=schema_path, **validate_kwargs)


def _load_schema(schema_path: Optional[Path] = None) -> dict:
    """Load JSON schema from path. Default: configs/schemas/data_package_schema.json relative to cwd."""
    path = schema_path
    if path is None:
        path = Path.cwd() / DEFAULT_SCHEMA_PATH
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Schema not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)
