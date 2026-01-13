# Normalizers Module

This directory is reserved for data normalization modules that will standardize data from different sources into a common format.

## Overview

Normalizers will provide functionality for normalizing security data from various sources into a standardized format that can be processed uniformly regardless of the original source.

## Planned Functionality

This module is planned for future implementation and will include:

### Normalization Tasks
- Field name standardization
- Data type normalization
- Timestamp format standardization
- IP address format normalization
- Event type mapping
- Severity level mapping
- Source-specific field mapping

### Features
- Multi-source normalization
- Configurable field mappings
- Data validation during normalization
- Error handling for unmappable data
- Performance optimization

## Current Status

This module is currently empty and reserved for future Phase 2+ implementation.

## Future Integration

Normalizers will integrate with:
- **Parsers**: For normalizing parsed data
- **DataPackage**: For standardized data structure
- **Pipeline Orchestrator**: For end-to-end pipeline coordination
- **Database**: For storing normalized data

## Usage (Planned)

```python
from automation_scripts.normalizers.security_normalizer import SecurityNormalizer

normalizer = SecurityNormalizer()
normalized_data = normalizer.normalize(parsed_data, source_type="splunk")
```

