"""
Deterministic anonymizer – HMAC-SHA256 pseudonymization with mapping store.

Same input always produces same pseudonym. Deanonymization via MappingStore.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from .mapping_store import MappingStore
from .mapping_store import InMemoryMappingStore
from .mapping_store import SQLiteMappingStore

logger = logging.getLogger(__name__)

# Default PII field names to anonymize in dicts
DEFAULT_PII_FIELDS: Set[str] = {
    "username",
    "user_id",
    "user",
    "email",
    "ip_address",
    "ip",
    "source_ip",
    "destination_ip",
    "src_ip",
    "dst_ip",
    "hostname",
    "computer_name",
    "account",
    "subject",
    "target_user",
    "process_user",
    "file_path",
    "path",
    "command_line",
    "parent_command_line",
}


def _compute_pseudonym(value: str, secret: bytes) -> str:
    """Compute HMAC-SHA256 pseudonym. Same input + secret → same output."""
    return hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()


class DeterministicAnonymizer:
    """
    Deterministic anonymization using HMAC-SHA256.

    - anonymize(value, field_type): pseudonymize and store mapping
    - deanonymize(pseudonym): lookup original via MappingStore
    - anonymize_dict(d, fields): anonymize specified keys in dict
    - anonymize_list(lst, field_type): anonymize list items
    """

    def __init__(
        self,
        secret: bytes,
        mapping_store: Optional[MappingStore] = None,
        pii_fields: Optional[Set[str]] = None,
    ) -> None:
        """
        Args:
            secret: 32-byte HMAC key (from get_anonymization_secret)
            mapping_store: backend for original↔pseudonym; default InMemoryMappingStore
            pii_fields: field names to anonymize in anonymize_dict; default DEFAULT_PII_FIELDS
        """
        if len(secret) < 16:
            raise ValueError("Secret must be at least 16 bytes for HMAC-SHA256")
        self._secret = secret[:32] if len(secret) > 32 else secret.ljust(32, b"\0")
        self._store = mapping_store or InMemoryMappingStore()
        self._pii_fields = pii_fields or DEFAULT_PII_FIELDS.copy()

    def anonymize(self, value: str, field_type: Optional[str] = None) -> str:
        """
        Anonymize a value. Same value always returns same pseudonym.
        Stores mapping for deanonymization.
        """
        if not value or not isinstance(value, str):
            return value
        pseudonym = self._store.lookup_pseudonym(value)
        if pseudonym is not None:
            return pseudonym
        pseudonym = _compute_pseudonym(value, self._secret)
        self._store.store(value, pseudonym, field_type)
        return pseudonym

    def deanonymize(self, pseudonym: str) -> Optional[str]:
        """Lookup original value by pseudonym. Returns None if not found."""
        if not pseudonym or not isinstance(pseudonym, str):
            return pseudonym
        return self._store.lookup_original(pseudonym)

    def anonymize_dict(
        self,
        data: Dict[str, Any],
        fields: Optional[Set[str]] = None,
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """
        Anonymize values in dict for specified keys (case-insensitive match).

        Args:
            data: dict to anonymize
            fields: keys to anonymize; default self._pii_fields
            recursive: if True, recurse into nested dicts/lists

        Returns:
            New dict with anonymized values (original unchanged).
        """
        keys_to_anon = fields or self._pii_fields
        keys_lower = {k.lower(): k for k in keys_to_anon}

        def _anon_val(v: Any, key_hint: Optional[str] = None) -> Any:
            if isinstance(v, str):
                return self.anonymize(v, key_hint)
            if isinstance(v, dict) and recursive:
                return self.anonymize_dict(v, fields=fields, recursive=True)
            if isinstance(v, list) and recursive:
                return [ _anon_val(x, key_hint) for x in v ]
            return v

        out: Dict[str, Any] = {}
        for k, v in data.items():
            key_lower = k.lower()
            if key_lower in keys_lower:
                out[k] = _anon_val(v, k)
            elif recursive and isinstance(v, (dict, list)):
                out[k] = _anon_val(v, k)
            else:
                out[k] = v
        return out

    def anonymize_list(
        self,
        items: List[Any],
        field_type: Optional[str] = None,
        recursive: bool = True,
    ) -> List[Any]:
        """
        Anonymize items in list. String items are anonymized; dicts/lists recurse if recursive=True.
        """
        result: List[Any] = []
        for item in items:
            if isinstance(item, str):
                result.append(self.anonymize(item, field_type))
            elif isinstance(item, dict) and recursive:
                result.append(self.anonymize_dict(item, recursive=True))
            elif isinstance(item, list) and recursive:
                result.append(self.anonymize_list(item, field_type, recursive=True))
            else:
                result.append(item)
        return result


def create_anonymizer(
    mapping_store: Optional[MappingStore] = None,
    db_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    config_path: Optional[Union[str, Path]] = None,
    pii_fields: Optional[Set[str]] = None,
) -> DeterministicAnonymizer:
    """
    Factory: create DeterministicAnonymizer with secret and mapping store.

    Args:
        mapping_store: optional pre-built store
        db_path: if provided and mapping_store is None, use SQLiteMappingStore(db_path)
        config: optional config dict for get_anonymization_secret
        config_path: optional path to config.yml
        pii_fields: optional set of field names for anonymize_dict

    Returns:
        DeterministicAnonymizer instance
    """
    from ..security import get_anonymization_secret

    secret = get_anonymization_secret(config=config, config_path=config_path)
    store = mapping_store
    if store is None and db_path is not None:
        store = SQLiteMappingStore(db_path)
    return DeterministicAnonymizer(
        secret=secret,
        mapping_store=store,
        pii_fields=pii_fields,
    )
