"""
Security utilities for data anonymization and hashing.

This module provides basic anonymization utilities that can be used
as fallback or for simple anonymization needs without database dependency.
"""

import hashlib
import secrets
from typing import Any, Dict, Optional
from ipaddress import IPv4Address, IPv6Address, AddressValueError


class DataAnonymizer:
    """
    Basic data anonymizer (non-deterministic).
    
    Provides simple anonymization methods without database dependency.
    For deterministic anonymization with mapping table, use DeterministicAnonymizer.
    """
    
    def __init__(self, salt: Optional[str] = None):
        """
        Initialize anonymizer.
        
        Args:
            salt: Salt for hashing (if None, generates random salt)
        """
        self.salt = salt or secrets.token_hex(16)
    
    def anonymize_ip(self, ip: str) -> str:
        """
        Anonymize IP address (e.g., 192.168.1.100 -> 192.168.1.0).
        
        Args:
            ip: IP address to anonymize
            
        Returns:
            Anonymized IP address
        """
        try:
            # Try IPv4
            addr = IPv4Address(ip)
            # Zero out last octet
            return str(IPv4Address(int(addr) & 0xFFFFFF00))
        except AddressValueError:
            try:
                # Try IPv6
                addr = IPv6Address(ip)
                # Zero out last 64 bits
                return str(IPv6Address(int(addr) & 0xFFFFFFFFFFFFFFFF0000000000000000))
            except AddressValueError:
                # Invalid IP, return as-is
                return ip
    
    def hash_user_id(self, user_id: str) -> str:
        """
        Hash user ID with salt.
        
        Args:
            user_id: User ID to hash
            
        Returns:
            Hashed user ID (hex digest, first 16 chars)
        """
        hash_obj = hashlib.sha256()
        hash_obj.update(self.salt.encode())
        hash_obj.update(user_id.encode())
        return hash_obj.hexdigest()[:16]  # First 16 chars for readability
    
    def tokenize_email(self, email: str) -> str:
        """
        Tokenize email address.
        
        Args:
            email: Email address to tokenize
            
        Returns:
            Tokenized email (e.g., user***@domain.com)
        """
        if '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        if len(local) > 3:
            tokenized_local = local[:2] + '***'
        else:
            tokenized_local = '***'
        
        return f"{tokenized_local}@{domain}"
    
    def anonymize_record(
        self,
        record: Dict[str, Any],
        fields_to_anonymize: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Anonymize sensitive fields in a record.
        
        Args:
            record: Record to anonymize
            fields_to_anonymize: List of field names to anonymize
                (default: common sensitive fields)
            
        Returns:
            Anonymized record
        """
        if fields_to_anonymize is None:
            fields_to_anonymize = ['ip', 'user', 'email', 'username', 'account']
        
        anonymized = record.copy()
        
        for field in fields_to_anonymize:
            if field in anonymized:
                value = anonymized[field]
                if isinstance(value, str):
                    if '@' in value:
                        anonymized[field] = self.tokenize_email(value)
                    elif self._is_ip(value):
                        anonymized[field] = self.anonymize_ip(value)
                    else:
                        anonymized[field] = self.hash_user_id(value)
        
        return anonymized
    
    def _is_ip(self, value: str) -> bool:
        """
        Check if value is an IP address.
        
        Args:
            value: Value to check
            
        Returns:
            True if value is an IP address
        """
        try:
            IPv4Address(value)
            return True
        except AddressValueError:
            try:
                IPv6Address(value)
                return True
            except AddressValueError:
                return False


def anonymize_data(data: list, salt: Optional[str] = None) -> list:
    """
    Anonymize a list of records using basic anonymization.
    
    Args:
        data: List of records to anonymize
        salt: Salt for hashing
    
    Returns:
        List of anonymized records
    """
    anonymizer = DataAnonymizer(salt)
    return [anonymizer.anonymize_record(record) for record in data]

