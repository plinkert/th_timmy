"""
Deterministic Anonymizer - Deterministic data anonymization with mapping table.

This module provides deterministic anonymization that ensures the same input
always produces the same anonymized output, with the ability to deanonymize
using a mapping table stored in PostgreSQL database.
"""

import hashlib
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import json

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class DeterministicAnonymizerError(Exception):
    """Base exception for deterministic anonymizer errors."""
    pass


class DeterministicAnonymizer:
    """
    Deterministic anonymizer with mapping table.
    
    Provides deterministic anonymization where the same input always produces
    the same anonymized output. Uses a mapping table stored in PostgreSQL
    database for deanonymization.
    
    Features:
    - Deterministic anonymization (same input = same output)
    - Mapping table in PostgreSQL database
    - Deanonymization capability
    - In-memory cache for performance
    - Support for multiple value types (IP, email, username, etc.)
    """
    
    def __init__(
        self,
        db_config: Optional[Dict[str, Any]] = None,
        db_connection: Optional[Any] = None,
        use_cache: bool = True,
        hash_original: bool = True,
        salt: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Deterministic Anonymizer.
        
        Args:
            db_config: Database configuration dictionary with keys:
                - host: Database host
                - port: Database port (default: 5432)
                - database: Database name
                - user: Database user
                - password: Database password
            db_connection: Optional existing database connection
            use_cache: Whether to use in-memory cache (default: True)
            hash_original: Whether to hash original values before storing (default: True)
            salt: Salt for deterministic hashing (if None, uses default)
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        if not PSYCOPG2_AVAILABLE:
            raise DeterministicAnonymizerError(
                "psycopg2 is required for DeterministicAnonymizer. "
                "Install with: pip install psycopg2-binary"
            )
        
        # Database configuration
        self.db_config = db_config or {}
        self.db_connection = db_connection
        self._own_connection = db_connection is None
        
        # Cache configuration
        self.use_cache = use_cache
        self._cache: Dict[str, Dict[str, str]] = {}  # {value_type: {original: anonymized}}
        self._reverse_cache: Dict[str, Dict[str, str]] = {}  # {value_type: {anonymized: original}}
        
        # Security configuration
        self.hash_original = hash_original
        self.salt = salt or "th_timmy_anonymization_salt_2024"
        
        # Initialize database connection and schema
        if self._own_connection:
            self._connect_database()
        
        self._ensure_schema()
        
        # Load cache if enabled
        if self.use_cache:
            self._load_cache()
        
        self.logger.info("DeterministicAnonymizer initialized")
    
    def _connect_database(self) -> None:
        """Connect to PostgreSQL database."""
        try:
            self.db_connection = psycopg2.connect(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 5432),
                database=self.db_config.get('database', 'threat_hunting'),
                user=self.db_config.get('user', 'threat_hunter'),
                password=self.db_config.get('password', '')
            )
            self.db_connection.autocommit = True
            self.logger.info("Connected to database")
        except Exception as e:
            raise DeterministicAnonymizerError(f"Failed to connect to database: {e}")
    
    def _ensure_schema(self) -> None:
        """Ensure anonymization_mapping table exists."""
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS anonymization_mapping (
                        id SERIAL PRIMARY KEY,
                        original_hash VARCHAR(64) NOT NULL,
                        original_value TEXT,
                        anonymized_value VARCHAR(255) NOT NULL,
                        value_type VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(original_hash, value_type)
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_anonymization_mapping_hash 
                        ON anonymization_mapping(original_hash, value_type);
                    CREATE INDEX IF NOT EXISTS idx_anonymization_mapping_anonymized 
                        ON anonymization_mapping(anonymized_value, value_type);
                    CREATE INDEX IF NOT EXISTS idx_anonymization_mapping_type 
                        ON anonymization_mapping(value_type);
                    CREATE INDEX IF NOT EXISTS idx_anonymization_mapping_original 
                        ON anonymization_mapping(original_value, value_type) 
                        WHERE original_value IS NOT NULL;
                """)
            self.logger.debug("Schema ensured")
        except Exception as e:
            raise DeterministicAnonymizerError(f"Failed to create schema: {e}")
    
    def _hash_value(self, value: str) -> str:
        """Hash value for storage in mapping table."""
        hash_obj = hashlib.sha256()
        hash_obj.update(self.salt.encode())
        hash_obj.update(value.encode())
        return hash_obj.hexdigest()
    
    def _generate_anonymized_value(
        self,
        original_value: str,
        value_type: str
    ) -> str:
        """
        Generate anonymized value deterministically.
        
        Args:
            original_value: Original value to anonymize
            value_type: Type of value (ip, email, username, etc.)
        
        Returns:
            Anonymized value
        """
        # Use deterministic hash based on salt, value, and type
        hash_obj = hashlib.sha256()
        hash_obj.update(self.salt.encode())
        hash_obj.update(value_type.encode())
        hash_obj.update(original_value.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Generate readable anonymized value based on type
        if value_type == 'ip':
            # Generate IP-like anonymized value (e.g., 10.0.0.123)
            parts = [int(hash_hex[i:i+2], 16) % 255 for i in range(0, 8, 2)]
            return f"10.{parts[0]}.{parts[1]}.{parts[2]}"
        elif value_type == 'email':
            # Generate email-like anonymized value (e.g., user_abc123@example.local)
            local_part = f"user_{hash_hex[:8]}"
            return f"{local_part}@example.local"
        elif value_type == 'username':
            # Generate username-like anonymized value (e.g., user_abc123)
            return f"user_{hash_hex[:12]}"
        elif value_type == 'hostname':
            # Generate hostname-like anonymized value (e.g., host-abc123.example.local)
            return f"host-{hash_hex[:8]}.example.local"
        else:
            # Generic anonymized value
            return f"anon_{hash_hex[:16]}"
    
    def _get_or_create_mapping(
        self,
        original_value: str,
        value_type: str
    ) -> str:
        """
        Get existing mapping or create new one.
        
        Args:
            original_value: Original value
            value_type: Type of value
        
        Returns:
            Anonymized value
        """
        # Check cache first
        if self.use_cache:
            cache_key = f"{value_type}:{original_value}"
            if cache_key in self._cache.get(value_type, {}):
                return self._cache[value_type][original_value]
        
        # Hash original value for storage
        original_hash = self._hash_value(original_value)
        
        # Try to get existing mapping
        try:
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT anonymized_value, original_value, last_used
                    FROM anonymization_mapping
                    WHERE original_hash = %s AND value_type = %s
                """, (original_hash, value_type))
                
                result = cursor.fetchone()
                
                if result:
                    anonymized_value = result['anonymized_value']
                    stored_original = result.get('original_value')
                    
                    # Update original_value if not stored (for backward compatibility)
                    if not stored_original:
                        cursor.execute("""
                            UPDATE anonymization_mapping
                            SET original_value = %s, last_used = CURRENT_TIMESTAMP
                            WHERE original_hash = %s AND value_type = %s
                        """, (original_value, original_hash, value_type))
                    else:
                        # Update last_used
                        cursor.execute("""
                            UPDATE anonymization_mapping
                            SET last_used = CURRENT_TIMESTAMP
                            WHERE original_hash = %s AND value_type = %s
                        """, (original_hash, value_type))
                    
                    # Update cache
                    if self.use_cache:
                        if value_type not in self._cache:
                            self._cache[value_type] = {}
                        if value_type not in self._reverse_cache:
                            self._reverse_cache[value_type] = {}
                        self._cache[value_type][original_value] = anonymized_value
                        self._reverse_cache[value_type][anonymized_value] = original_value
                    
                    return anonymized_value
        except Exception as e:
            self.logger.warning(f"Error reading mapping: {e}")
        
        # Create new mapping
        anonymized_value = self._generate_anonymized_value(original_value, value_type)
        
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO anonymization_mapping 
                        (original_hash, original_value, anonymized_value, value_type, created_at, last_used)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (original_hash, value_type) DO UPDATE
                    SET original_value = COALESCE(anonymization_mapping.original_value, EXCLUDED.original_value),
                        last_used = CURRENT_TIMESTAMP
                """, (original_hash, original_value, anonymized_value, value_type))
            
            # Update cache
            if self.use_cache:
                if value_type not in self._cache:
                    self._cache[value_type] = {}
                if value_type not in self._reverse_cache:
                    self._reverse_cache[value_type] = {}
                self._cache[value_type][original_value] = anonymized_value
                self._reverse_cache[value_type][anonymized_value] = original_value
            
            self.logger.debug(f"Created mapping for {value_type}: {original_value} -> {anonymized_value}")
            
        except Exception as e:
            self.logger.error(f"Error creating mapping: {e}")
            # Fallback: return generated value even if DB write fails
            return anonymized_value
        
        return anonymized_value
    
    def _get_original_value(
        self,
        anonymized_value: str,
        value_type: str
    ) -> Optional[str]:
        """
        Get original value from anonymized value.
        
        Args:
            anonymized_value: Anonymized value
            value_type: Type of value
        
        Returns:
            Original value or None if not found
        """
        # Check cache first
        if self.use_cache:
            if value_type in self._reverse_cache:
                if anonymized_value in self._reverse_cache[value_type]:
                    return self._reverse_cache[value_type][anonymized_value]
        
        # Query database
        try:
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT original_value
                    FROM anonymization_mapping
                    WHERE anonymized_value = %s AND value_type = %s
                """, (anonymized_value, value_type))
                
                result = cursor.fetchone()
                
                if result:
                    original_value = result.get('original_value')
                    
                    if original_value:
                        # Update cache
                        if self.use_cache:
                            if value_type not in self._reverse_cache:
                                self._reverse_cache[value_type] = {}
                            if value_type not in self._cache:
                                self._cache[value_type] = {}
                            self._reverse_cache[value_type][anonymized_value] = original_value
                            self._cache[value_type][original_value] = anonymized_value
                        
                        return original_value
                    else:
                        self.logger.warning(
                            f"Original value not stored for anonymized value: {anonymized_value}"
                        )
                        return None
        except Exception as e:
            self.logger.error(f"Error reading reverse mapping: {e}")
        
        return None
    
    def _load_cache(self) -> None:
        """Load mapping table into cache."""
        if not self.use_cache:
            return
        
        try:
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT original_value, anonymized_value, value_type
                    FROM anonymization_mapping
                    WHERE original_value IS NOT NULL
                    ORDER BY last_used DESC
                    LIMIT 10000
                """)
                
                results = cursor.fetchall()
                for row in results:
                    value_type = row['value_type']
                    original_value = row['original_value']
                    anonymized_value = row['anonymized_value']
                    
                    if value_type not in self._cache:
                        self._cache[value_type] = {}
                    if value_type not in self._reverse_cache:
                        self._reverse_cache[value_type] = {}
                    
                    self._cache[value_type][original_value] = anonymized_value
                    self._reverse_cache[value_type][anonymized_value] = original_value
                
            self.logger.info(f"Loaded {len(results)} mappings into cache")
        except Exception as e:
            self.logger.warning(f"Error loading cache: {e}")
    
    def anonymize(
        self,
        value: str,
        value_type: str = 'generic'
    ) -> str:
        """
        Anonymize a single value deterministically.
        
        Args:
            value: Value to anonymize
            value_type: Type of value (ip, email, username, hostname, generic)
        
        Returns:
            Anonymized value
        """
        if not value or not isinstance(value, str):
            return value
        
        return self._get_or_create_mapping(value, value_type)
    
    def deanonymize(
        self,
        anonymized_value: str,
        value_type: str = 'generic'
    ) -> Optional[str]:
        """
        Deanonymize a value using mapping table.
        
        Args:
            anonymized_value: Anonymized value
            value_type: Type of value
        
        Returns:
            Original value or None if not found
        """
        if not anonymized_value or not isinstance(anonymized_value, str):
            return anonymized_value
        
        return self._get_original_value(anonymized_value, value_type)
    
    def anonymize_record(
        self,
        record: Dict[str, Any],
        fields_to_anonymize: Optional[List[str]] = None,
        field_types: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Anonymize sensitive fields in a record.
        
        Args:
            record: Record to anonymize
            fields_to_anonymize: List of field names to anonymize
            field_types: Optional mapping of field names to value types
        
        Returns:
            Anonymized record
        """
        if fields_to_anonymize is None:
            fields_to_anonymize = ['ip', 'email', 'username', 'user', 'account', 'hostname', 'host']
        
        if field_types is None:
            field_types = {
                'ip': 'ip',
                'email': 'email',
                'username': 'username',
                'user': 'username',
                'account': 'username',
                'hostname': 'hostname',
                'host': 'hostname'
            }
        
        anonymized = record.copy()
        
        for field in fields_to_anonymize:
            if field in anonymized:
                value = anonymized[field]
                if isinstance(value, str) and value.strip():
                    value_type = field_types.get(field, 'generic')
                    anonymized[field] = self.anonymize(value, value_type)
        
        return anonymized
    
    def deanonymize_record(
        self,
        record: Dict[str, Any],
        fields_to_deanonymize: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Deanonymize fields in a record.
        
        Args:
            record: Record to deanonymize
            fields_to_deanonymize: List of field names to deanonymize
        
        Returns:
            Deanonymized record
        """
        if fields_to_deanonymize is None:
            fields_to_deanonymize = ['ip', 'email', 'username', 'user', 'account', 'hostname', 'host']
        
        deanonymized = record.copy()
        
        for field in fields_to_deanonymize:
            if field in deanonymized:
                value = deanonymized[field]
                if isinstance(value, str) and value.strip():
                    # Try to determine value type from field name
                    value_type = 'generic'
                    if field in ['ip']:
                        value_type = 'ip'
                    elif field in ['email']:
                        value_type = 'email'
                    elif field in ['username', 'user', 'account']:
                        value_type = 'username'
                    elif field in ['hostname', 'host']:
                        value_type = 'hostname'
                    
                    original = self.deanonymize(value, value_type)
                    if original:
                        deanonymized[field] = original
        
        return deanonymized
    
    def anonymize_batch(
        self,
        records: List[Dict[str, Any]],
        fields_to_anonymize: Optional[List[str]] = None,
        field_types: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Anonymize a batch of records.
        
        Args:
            records: List of records to anonymize
            fields_to_anonymize: List of field names to anonymize
            field_types: Optional mapping of field names to value types
        
        Returns:
            List of anonymized records
        """
        return [
            self.anonymize_record(record, fields_to_anonymize, field_types)
            for record in records
        ]
    
    def get_mapping_stats(self) -> Dict[str, Any]:
        """
        Get statistics about mapping table.
        
        Returns:
            Dictionary with statistics
        """
        try:
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Total mappings
                cursor.execute("SELECT COUNT(*) as total FROM anonymization_mapping")
                total = cursor.fetchone()['total']
                
                # By type
                cursor.execute("""
                    SELECT value_type, COUNT(*) as count
                    FROM anonymization_mapping
                    GROUP BY value_type
                    ORDER BY count DESC
                """)
                by_type = {row['value_type']: row['count'] for row in cursor.fetchall()}
                
                # Cache stats
                cache_stats = {}
                if self.use_cache:
                    for value_type, mappings in self._cache.items():
                        cache_stats[value_type] = len(mappings)
                
                return {
                    'total_mappings': total,
                    'by_type': by_type,
                    'cache_size': sum(len(m) for m in self._cache.values()),
                    'cache_by_type': cache_stats,
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            self.logger.error(f"Error getting mapping stats: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        self._cache.clear()
        self._reverse_cache.clear()
        self.logger.info("Cache cleared")
    
    def close(self) -> None:
        """Close database connection."""
        if self._own_connection and self.db_connection:
            self.db_connection.close()
            self.logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass

