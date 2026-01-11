"""
API endpoints for remote execution service.

This module provides REST API endpoints for remote VM management.
"""

from .remote_api import router, create_remote_api_app

__all__ = ['router', 'create_remote_api_app']


