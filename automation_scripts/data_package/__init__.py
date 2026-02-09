"""
Data Package (Step 1.5) – standard format for threat hunting pipeline data.

Provides DataPackage class with validate(), to_dict(), from_dict().
"""

from .data_package import DataPackage, DataPackageValidationError

__all__ = ["DataPackage", "DataPackageValidationError"]
