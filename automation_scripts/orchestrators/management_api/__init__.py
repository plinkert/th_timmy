"""
Management API – dashboard endpoints for n8n (Step 0.5).

Provides GET /api/v1/dashboard/status, POST sync-repo, backup-config, refresh.
"""

from .dashboard import router as dashboard_router

__all__ = ["dashboard_router"]
