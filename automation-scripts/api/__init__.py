"""
API endpoints for remote execution service.

This module provides REST API endpoints for remote VM management.
"""

# Lazy import to avoid circular import issues and relative import errors
# remote_api is only needed when explicitly imported, not during package initialization
# This prevents "attempted relative import beyond top-level package" errors

__all__ = ['router', 'create_remote_api_app']


def _lazy_import_remote_api():
    """Lazy import of remote_api to avoid import errors during package initialization."""
    from .remote_api import router, create_remote_api_app
    return router, create_remote_api_app


# Make router and create_remote_api_app available via lazy import
def __getattr__(name):
    """Lazy attribute access for remote_api components."""
    if name in ('router', 'create_remote_api_app'):
        router, create_remote_api_app = _lazy_import_remote_api()
        if name == 'router':
            return router
        elif name == 'create_remote_api_app':
            return create_remote_api_app
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


