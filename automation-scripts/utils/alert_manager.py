"""
Alert Manager - Alert management and notification system.

This module provides functionality for managing alerts, notifications,
and alert history with different severity levels.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertManagerError(Exception):
    """Base exception for alert manager errors."""
    pass


class AlertManager:
    """
    Alert management system.
    
    Provides functionality for:
    - Sending alerts with different severity levels
    - Storing alert history
    - Filtering and querying alerts
    - Alert aggregation and deduplication
    """
    
    def __init__(
        self,
        alert_history_file: Optional[str] = None,
        max_history_size: int = 10000,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Alert Manager.
        
        Args:
            alert_history_file: Path to alert history file
            max_history_size: Maximum number of alerts to keep in history
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Setup alert history file
        if alert_history_file:
            self.alert_history_file = Path(alert_history_file)
        else:
            # Default location
            default_dir = Path(__file__).parent.parent.parent / "logs"
            default_dir.mkdir(parents=True, exist_ok=True)
            self.alert_history_file = default_dir / "alerts_history.json"
        
        self.max_history_size = max_history_size
        
        # Ensure history file exists
        self._ensure_history_file()
        
        self.logger.debug(f"AlertManager initialized with history file: {self.alert_history_file}")
    
    def _ensure_history_file(self) -> None:
        """Ensure alert history file exists."""
        self.alert_history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.alert_history_file.exists():
            with open(self.alert_history_file, 'w') as f:
                json.dump({'alerts': []}, f, indent=2)
    
    def send_alert(
        self,
        level: str,
        message: str,
        vm_id: Optional[str] = None,
        component: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send alert.
        
        Args:
            level: Alert level ('info', 'warning', 'error', 'critical')
            message: Alert message
            vm_id: Optional VM identifier
            component: Optional component name (e.g., 'postgresql', 'jupyterlab')
            metadata: Optional additional metadata
        
        Returns:
            Dictionary with alert information
        """
        try:
            # Validate level
            try:
                alert_level = AlertLevel(level.lower())
            except ValueError:
                raise AlertManagerError(f"Invalid alert level: {level}")
            
            # Create alert
            alert = {
                'id': self._generate_alert_id(),
                'timestamp': datetime.utcnow().isoformat(),
                'level': alert_level.value,
                'message': message,
                'vm_id': vm_id,
                'component': component,
                'metadata': metadata or {},
                'acknowledged': False
            }
            
            # Log alert
            log_level = {
                'info': logging.INFO,
                'warning': logging.WARNING,
                'error': logging.ERROR,
                'critical': logging.CRITICAL
            }.get(alert_level.value, logging.INFO)
            
            log_msg = f"ALERT [{alert_level.value.upper()}]"
            if vm_id:
                log_msg += f" VM: {vm_id}"
            if component:
                log_msg += f" Component: {component}"
            log_msg += f" - {message}"
            
            self.logger.log(log_level, log_msg)
            
            # Save to history
            self._save_alert(alert)
            
            return alert
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
            raise AlertManagerError(f"Failed to send alert: {e}")
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        return f"alert_{timestamp}"
    
    def _save_alert(self, alert: Dict[str, Any]) -> None:
        """Save alert to history file."""
        try:
            # Load existing alerts
            if self.alert_history_file.exists():
                with open(self.alert_history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = {'alerts': []}
            
            # Add new alert
            history['alerts'].append(alert)
            
            # Keep only last max_history_size alerts
            if len(history['alerts']) > self.max_history_size:
                history['alerts'] = history['alerts'][-self.max_history_size:]
            
            # Save history
            with open(self.alert_history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to save alert to history: {e}")
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge alert.
        
        Args:
            alert_id: Alert ID to acknowledge
        
        Returns:
            True if alert was acknowledged, False if not found
        """
        try:
            if not self.alert_history_file.exists():
                return False
            
            with open(self.alert_history_file, 'r') as f:
                history = json.load(f)
            
            # Find and update alert
            for alert in history.get('alerts', []):
                if alert.get('id') == alert_id:
                    alert['acknowledged'] = True
                    alert['acknowledged_at'] = datetime.utcnow().isoformat()
                    
                    # Save updated history
                    with open(self.alert_history_file, 'w') as f:
                        json.dump(history, f, indent=2)
                    
                    self.logger.info(f"Alert acknowledged: {alert_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    def get_alerts(
        self,
        level: Optional[str] = None,
        vm_id: Optional[str] = None,
        component: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alerts matching criteria.
        
        Args:
            level: Filter by alert level
            vm_id: Filter by VM ID
            component: Filter by component
            acknowledged: Filter by acknowledged status
            limit: Maximum number of alerts to return
            since: Return alerts since this datetime
        
        Returns:
            List of matching alerts
        """
        try:
            if not self.alert_history_file.exists():
                return []
            
            with open(self.alert_history_file, 'r') as f:
                history = json.load(f)
            
            alerts = history.get('alerts', [])
            
            # Apply filters
            filtered = []
            for alert in alerts:
                # Level filter
                if level and alert.get('level') != level.lower():
                    continue
                
                # VM ID filter
                if vm_id and alert.get('vm_id') != vm_id:
                    continue
                
                # Component filter
                if component and alert.get('component') != component:
                    continue
                
                # Acknowledged filter
                if acknowledged is not None and alert.get('acknowledged') != acknowledged:
                    continue
                
                # Since filter
                if since:
                    alert_time = datetime.fromisoformat(alert.get('timestamp', ''))
                    if alert_time < since:
                        continue
                
                filtered.append(alert)
            
            # Sort by timestamp (newest first)
            filtered.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Apply limit
            if limit:
                filtered = filtered[:limit]
            
            return filtered
            
        except Exception as e:
            self.logger.error(f"Failed to get alerts: {e}")
            return []
    
    def get_unacknowledged_alerts(
        self,
        level: Optional[str] = None,
        vm_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get unacknowledged alerts.
        
        Args:
            level: Filter by alert level
            vm_id: Filter by VM ID
        
        Returns:
            List of unacknowledged alerts
        """
        return self.get_alerts(
            level=level,
            vm_id=vm_id,
            acknowledged=False
        )
    
    def get_critical_alerts(self, vm_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get critical alerts.
        
        Args:
            vm_id: Optional VM ID filter
        
        Returns:
            List of critical alerts
        """
        return self.get_alerts(
            level='critical',
            vm_id=vm_id,
            acknowledged=False
        )
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get alert summary statistics.
        
        Returns:
            Dictionary with alert statistics
        """
        try:
            if not self.alert_history_file.exists():
                return {
                    'total': 0,
                    'by_level': {},
                    'unacknowledged': 0,
                    'critical': 0
                }
            
            with open(self.alert_history_file, 'r') as f:
                history = json.load(f)
            
            alerts = history.get('alerts', [])
            
            # Count by level
            by_level = {}
            unacknowledged = 0
            critical = 0
            
            for alert in alerts:
                level = alert.get('level', 'info')
                by_level[level] = by_level.get(level, 0) + 1
                
                if not alert.get('acknowledged', False):
                    unacknowledged += 1
                
                if level == 'critical':
                    critical += 1
            
            return {
                'total': len(alerts),
                'by_level': by_level,
                'unacknowledged': unacknowledged,
                'critical': critical,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get alert summary: {e}")
            return {
                'total': 0,
                'by_level': {},
                'unacknowledged': 0,
                'critical': 0,
                'error': str(e)
            }

