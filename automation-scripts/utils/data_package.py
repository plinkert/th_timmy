"""
Data Package - Standardized structure for threat hunting data.

This module provides a standardized structure for data packages that is
independent of the data source (manual upload, API, file, database, stream).
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from jsonschema import validate, ValidationError, Draft7Validator

from pathlib import Path as PathType


class DataPackageError(Exception):
    """Base exception for DataPackage errors."""
    pass


class DataPackageValidationError(DataPackageError):
    """Exception raised when data package validation fails."""
    pass


class DataPackage:
    """
    Standardized data package structure for threat hunting.
    
    A DataPackage contains:
    - Metadata: Package information, source details, validation status
    - Data: Array of normalized data records
    
    The structure is independent of data source (manual/API/file/database/stream)
    and provides consistent interface for data processing.
    """
    
    SCHEMA_VERSION = "1.0.0"
    
    def __init__(
        self,
        source_type: str,
        source_name: str,
        data: Optional[List[Dict[str, Any]]] = None,
        package_id: Optional[str] = None,
        ingest_mode: str = "manual",
        query_info: Optional[Dict[str, Any]] = None,
        source_config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize DataPackage.
        
        Args:
            source_type: Type of data source ('manual', 'api', 'file', 'database', 'stream')
            source_name: Name/identifier of the data source
            data: Optional list of normalized data records
            package_id: Optional package ID (auto-generated if not provided)
            ingest_mode: Mode of ingestion ('manual' or 'api')
            query_info: Optional information about the query used
            source_config: Optional configuration for the data source
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Generate package ID if not provided
        self.package_id = package_id or self._generate_package_id()
        
        # Metadata
        self.metadata = {
            "package_id": self.package_id,
            "created_at": datetime.utcnow().isoformat(),
            "version": self.SCHEMA_VERSION,
            "source_type": source_type,
            "source_name": source_name,
            "ingest_mode": ingest_mode,
            "source_config": source_config or {},
            "query_info": query_info,
            "anonymization": {
                "is_anonymized": False,
                "anonymization_method": "none"
            },
            "validation": {
                "is_valid": False,
                "validated_at": None,
                "validation_errors": [],
                "validation_warnings": []
            },
            "statistics": {}
        }
        
        # Data
        self.data = data or []
        
        # Load schema
        self._schema = self._load_schema()
        
        # Calculate statistics
        self._update_statistics()
    
    @staticmethod
    def _generate_package_id() -> str:
        """Generate unique package ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"pkg_{timestamp}_{unique_id}"
    
    @staticmethod
    def _load_schema() -> Dict[str, Any]:
        """Load JSON schema for validation."""
        schema_path = Path(__file__).parent.parent / "schemas" / "data_package_schema.json"
        
        if not schema_path.exists():
            raise DataPackageError(f"Schema file not found: {schema_path}")
        
        try:
            with open(schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise DataPackageError(f"Failed to load schema: {e}")
    
    def add_record(self, record: Dict[str, Any]) -> None:
        """
        Add a normalized record to the package.
        
        Args:
            record: Normalized record dictionary
        """
        # Validate record structure
        required_fields = ['timestamp', 'source', 'event_type']
        for field in required_fields:
            if field not in record:
                raise DataPackageError(f"Record missing required field: {field}")
        
        self.data.append(record)
        self._update_statistics()
    
    def add_records(self, records: List[Dict[str, Any]]) -> None:
        """
        Add multiple normalized records to the package.
        
        Args:
            records: List of normalized record dictionaries
        """
        for record in records:
            self.add_record(record)
    
    def validate(self, strict: bool = True) -> bool:
        """
        Validate the data package against JSON schema.
        
        Args:
            strict: If True, raise exception on validation failure
        
        Returns:
            True if valid, False otherwise
        
        Raises:
            DataPackageValidationError: If validation fails and strict=True
        """
        try:
            # Create package dictionary
            package_dict = self.to_dict()
            
            # Validate against schema
            validate(instance=package_dict, schema=self._schema)
            
            # Additional validation
            self._validate_data_records()
            
            # Update validation metadata
            self.metadata["validation"]["is_valid"] = True
            self.metadata["validation"]["validated_at"] = datetime.utcnow().isoformat()
            self.metadata["validation"]["validation_errors"] = []
            self.metadata["validation"]["validation_warnings"] = []
            
            self.logger.info(f"DataPackage {self.package_id} validated successfully")
            return True
            
        except ValidationError as e:
            error_msg = f"Schema validation failed: {e.message}"
            self.logger.error(error_msg)
            
            # Update validation metadata
            self.metadata["validation"]["is_valid"] = False
            self.metadata["validation"]["validated_at"] = datetime.utcnow().isoformat()
            self.metadata["validation"]["validation_errors"] = [error_msg]
            
            if strict:
                raise DataPackageValidationError(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            self.logger.error(error_msg)
            
            self.metadata["validation"]["is_valid"] = False
            self.metadata["validation"]["validated_at"] = datetime.utcnow().isoformat()
            self.metadata["validation"]["validation_errors"] = [error_msg]
            
            if strict:
                raise DataPackageValidationError(error_msg)
            return False
    
    def _validate_data_records(self) -> None:
        """Validate individual data records."""
        warnings = []
        
        for i, record in enumerate(self.data):
            # Check timestamp format
            try:
                datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                warnings.append(f"Record {i}: Invalid timestamp format")
            
            # Check required fields
            if 'raw_data' not in record:
                warnings.append(f"Record {i}: Missing 'raw_data' field")
            
            if 'normalized_fields' not in record:
                warnings.append(f"Record {i}: Missing 'normalized_fields' field")
        
        if warnings:
            self.metadata["validation"]["validation_warnings"].extend(warnings)
    
    def _update_statistics(self) -> None:
        """Update package statistics."""
        if not self.data:
            self.metadata["statistics"] = {
                "total_records": 0,
                "unique_sources": 0,
                "unique_event_types": 0,
                "time_range": None
            }
            return
        
        # Count records
        total_records = len(self.data)
        
        # Count unique sources
        unique_sources = len(set(record.get('source', '') for record in self.data))
        
        # Count unique event types
        unique_event_types = len(set(record.get('event_type', '') for record in self.data))
        
        # Calculate time range
        timestamps = []
        for record in self.data:
            try:
                ts_str = record.get('timestamp', '')
                if ts_str:
                    # Handle ISO format with or without timezone
                    ts_str = ts_str.replace('Z', '+00:00')
                    ts = datetime.fromisoformat(ts_str)
                    timestamps.append(ts)
            except (ValueError, AttributeError):
                continue
        
        time_range = None
        if timestamps:
            time_range = {
                "start": min(timestamps).isoformat(),
                "end": max(timestamps).isoformat()
            }
        
        self.metadata["statistics"] = {
            "total_records": total_records,
            "unique_sources": unique_sources,
            "unique_event_types": unique_event_types,
            "time_range": time_range
        }
    
    def set_anonymization_info(
        self,
        is_anonymized: bool,
        method: str = "deterministic",
        mapping_table_id: Optional[str] = None
    ) -> None:
        """
        Set anonymization information.
        
        Args:
            is_anonymized: Whether data is anonymized
            method: Anonymization method ('deterministic', 'hash', 'tokenization', 'none')
            mapping_table_id: Optional mapping table ID for deanonymization
        """
        self.metadata["anonymization"] = {
            "is_anonymized": is_anonymized,
            "anonymization_method": method,
            "mapping_table_id": mapping_table_id
        }
    
    def set_query_info(self, query_info: Dict[str, Any]) -> None:
        """
        Set query information.
        
        Args:
            query_info: Dictionary with query information
        """
        self.metadata["query_info"] = query_info
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert package to dictionary.
        
        Returns:
            Dictionary representation of the package
        """
        return {
            "metadata": self.metadata,
            "data": self.data
        }
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convert package to JSON string.
        
        Args:
            indent: JSON indentation level
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save(self, file_path: Union[str, PathType]) -> None:
        """
        Save package to JSON file.
        
        Args:
            file_path: Path to save the package
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        
        self.logger.info(f"DataPackage {self.package_id} saved to {file_path}")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], logger: Optional[logging.Logger] = None) -> 'DataPackage':
        """
        Create DataPackage from dictionary.
        
        Args:
            data: Dictionary with 'metadata' and 'data' keys
            logger: Optional logger instance
        
        Returns:
            DataPackage instance
        """
        metadata = data.get('metadata', {})
        package_data = data.get('data', [])
        
        package = cls(
            source_type=metadata.get('source_type', 'unknown'),
            source_name=metadata.get('source_name', 'unknown'),
            data=package_data,
            package_id=metadata.get('package_id'),
            ingest_mode=metadata.get('ingest_mode', 'manual'),
            query_info=metadata.get('query_info'),
            source_config=metadata.get('source_config'),
            logger=logger
        )
        
        # Restore metadata
        package.metadata = metadata
        
        return package
    
    @classmethod
    def from_json(cls, json_str: str, logger: Optional[logging.Logger] = None) -> 'DataPackage':
        """
        Create DataPackage from JSON string.
        
        Args:
            json_str: JSON string representation
            logger: Optional logger instance
        
        Returns:
            DataPackage instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data, logger=logger)
    
    @classmethod
    def from_file(cls, file_path: Union[str, PathType], logger: Optional[logging.Logger] = None) -> 'DataPackage':
        """
        Load DataPackage from JSON file.
        
        Args:
            file_path: Path to JSON file
            logger: Optional logger instance
        
        Returns:
            DataPackage instance
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise DataPackageError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            json_str = f.read()
        
        return cls.from_json(json_str, logger=logger)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get package summary.
        
        Returns:
            Summary dictionary
        """
        return {
            "package_id": self.package_id,
            "created_at": self.metadata["created_at"],
            "source_type": self.metadata["source_type"],
            "source_name": self.metadata["source_name"],
            "ingest_mode": self.metadata["ingest_mode"],
            "total_records": self.metadata["statistics"].get("total_records", 0),
            "is_valid": self.metadata["validation"].get("is_valid", False),
            "is_anonymized": self.metadata["anonymization"].get("is_anonymized", False)
        }
    
    def __len__(self) -> int:
        """Return number of records in package."""
        return len(self.data)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"DataPackage(id={self.package_id}, records={len(self.data)}, source={self.metadata['source_name']})"

