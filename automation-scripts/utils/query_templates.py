"""
Query Templates - Base query templates for different SIEM/EDR tools.

This module provides base query templates that can be used as fallbacks
or starting points when playbook-specific queries are not available.
"""

from typing import Dict, Any, Optional
from enum import Enum


class QueryTool(Enum):
    """Supported query tools."""
    MICROSOFT_DEFENDER = "microsoft_defender"
    MICROSOFT_SENTINEL = "microsoft_sentinel"
    SPLUNK = "splunk"
    ELASTICSEARCH = "elasticsearch"
    GENERIC_SIEM = "generic_siem"


class QueryMode(Enum):
    """Query execution modes."""
    MANUAL = "manual"
    API = "api"


class QueryTemplates:
    """
    Base query templates for different SIEM/EDR tools.
    
    These templates serve as fallbacks when playbook-specific queries
    are not available, or as starting points for custom queries.
    """
    
    @staticmethod
    def get_template(
        tool: QueryTool,
        mode: QueryMode,
        technique_id: Optional[str] = None,
        technique_name: Optional[str] = None
    ) -> str:
        """
        Get base query template for a tool and mode.
        
        Args:
            tool: Query tool (Microsoft Defender, Splunk, etc.)
            mode: Query mode (manual or API)
            technique_id: Optional MITRE technique ID (e.g., "T1566")
            technique_name: Optional MITRE technique name
        
        Returns:
            Query template string
        """
        if tool == QueryTool.MICROSOFT_DEFENDER:
            return QueryTemplates._get_defender_template(mode, technique_id, technique_name)
        elif tool == QueryTool.MICROSOFT_SENTINEL:
            return QueryTemplates._get_sentinel_template(mode, technique_id, technique_name)
        elif tool == QueryTool.SPLUNK:
            return QueryTemplates._get_splunk_template(mode, technique_id, technique_name)
        elif tool == QueryTool.ELASTICSEARCH:
            return QueryTemplates._get_elasticsearch_template(mode, technique_id, technique_name)
        elif tool == QueryTool.GENERIC_SIEM:
            return QueryTemplates._get_generic_template(mode, technique_id, technique_name)
        else:
            raise ValueError(f"Unsupported tool: {tool}")
    
    @staticmethod
    def _get_defender_template(
        mode: QueryMode,
        technique_id: Optional[str] = None,
        technique_name: Optional[str] = None
    ) -> str:
        """Get Microsoft Defender query template."""
        comment = f"// Microsoft Defender for Endpoint - {mode.value.upper()} Query"
        if technique_id:
            comment += f"\n// MITRE Technique: {technique_id}"
        if technique_name:
            comment += f" ({technique_name})"
        
        if mode == QueryMode.MANUAL:
            return f"""{comment}
// Description: Detects suspicious process execution patterns
// Usage: Copy this query to Microsoft Defender Advanced Hunting and execute manually
// Time Range: Adjust the ago() parameter to change the time range (default: 7 days)

DeviceProcessEvents
| where TimeGenerated >= ago(7d)
| where ProcessCommandLine contains "suspicious_pattern"
    or ProcessCommandLine contains "powershell -enc"
    or ProcessCommandLine contains "cmd /c"
| project TimeGenerated, DeviceName, ProcessName, ProcessCommandLine, AccountName, InitiatingProcessName
| order by TimeGenerated desc

// Instructions:
// 1. Replace "suspicious_pattern" with the actual pattern you're looking for
// 2. Adjust the time range by changing "7d" to your desired range (e.g., "1d", "30d")
// 3. Add additional filters as needed
// 4. Review the results and export to CSV
"""
        else:  # API mode
            return f"""{comment}
// Description: Detects suspicious process execution patterns (for automated execution)
// Usage: This query is designed for automated execution via Microsoft Defender API
// Parameters: time_range (default: 7d), severity (default: high)

DeviceProcessEvents
| where TimeGenerated >= ago({{{{time_range}}}})
| where ProcessCommandLine contains "suspicious_pattern"
    or ProcessCommandLine contains "powershell -enc"
    or ProcessCommandLine contains "cmd /c"
| where Severity == "{{{{severity}}}}"
| project TimeGenerated, DeviceName, ProcessName, ProcessCommandLine, AccountName, InitiatingProcessName, Severity
| order by TimeGenerated desc

// Note: This query uses placeholders {{{{time_range}}}} and {{{{severity}}}} that will be replaced
// by the query_generator service when executing via API.
"""
    
    @staticmethod
    def _get_sentinel_template(
        mode: QueryMode,
        technique_id: Optional[str] = None,
        technique_name: Optional[str] = None
    ) -> str:
        """Get Microsoft Sentinel query template."""
        comment = f"// Microsoft Sentinel - {mode.value.upper()} Query"
        if technique_id:
            comment += f"\n// MITRE Technique: {technique_id}"
        if technique_name:
            comment += f" ({technique_name})"
        
        if mode == QueryMode.MANUAL:
            return f"""{comment}
// Description: Searches for suspicious activities in Microsoft Sentinel logs
// Usage: Copy this query to Azure Log Analytics workspace and execute manually
// Time Range: Adjust the ago() parameter to change the time range (default: 7 days)

SecurityEvent
| where TimeGenerated >= ago(7d)
| where EventID == 4624 or EventID == 4625
| where AccountType == "User"
| where IpAddress != "127.0.0.1"
| project TimeGenerated, Computer, EventID, Account, IpAddress, LogonType
| order by TimeGenerated desc

// Instructions:
// 1. Replace EventID values with the events you're looking for
// 2. Adjust the time range by changing "7d" to your desired range
// 3. Add additional filters as needed
// 4. Review the results and export to CSV
"""
        else:  # API mode
            return f"""{comment}
// Description: Searches for suspicious activities (for automated execution)
// Usage: This query is designed for automated execution via Azure Log Analytics API
// Parameters: time_range (default: 7d), workspace (your workspace name)

SecurityEvent
| where TimeGenerated >= ago({{{{time_range}}}})
| where EventID == 4624 or EventID == 4625
| where AccountType == "User"
| where IpAddress != "127.0.0.1"
| project TimeGenerated, Computer, EventID, Account, IpAddress, LogonType
| order by TimeGenerated desc

// Note: This query uses placeholder {{{{time_range}}}} that will be replaced
// by the query_generator service when executing via API.
"""
    
    @staticmethod
    def _get_splunk_template(
        mode: QueryMode,
        technique_id: Optional[str] = None,
        technique_name: Optional[str] = None
    ) -> str:
        """Get Splunk query template."""
        comment = f"# Splunk - {mode.value.upper()} Query"
        if technique_id:
            comment += f"\n# MITRE Technique: {technique_id}"
        if technique_name:
            comment += f" ({technique_name})"
        
        if mode == QueryMode.MANUAL:
            return f"""{comment}
# Description: Searches for suspicious activities in Splunk
# Usage: Copy this query to Splunk Search & Reporting and execute manually
# Time Range: Adjust using the time picker (default: Last 7 days)

index=security earliest=-7d@d latest=now
| search "suspicious_pattern" OR "powershell -enc" OR "cmd /c"
| stats count by host, user, action
| sort -count

# Instructions:
# 1. Replace "suspicious_pattern" with the actual pattern you're looking for
# 2. Adjust the time range using the time picker (default: Last 7 days)
# 3. Replace "security" with your actual index name
# 4. Add additional filters as needed
# 5. Review the results and export to CSV
"""
        else:  # API mode
            return f"""{comment}
# Description: Searches for suspicious activities (for automated execution)
# Usage: This query is designed for automated execution via Splunk REST API
# Parameters: time_range (default: 7d), index (default: security)

index={{{{index}}}} earliest=-{{{{time_range}}}}@d latest=now
| search "suspicious_pattern" OR "powershell -enc" OR "cmd /c"
| stats count by host, user, action
| sort -count

# Note: This query uses placeholders {{{{time_range}}}} and {{{{index}}}} that will be replaced
# by the query_generator service when executing via API.
"""
    
    @staticmethod
    def _get_elasticsearch_template(
        mode: QueryMode,
        technique_id: Optional[str] = None,
        technique_name: Optional[str] = None
    ) -> str:
        """Get Elasticsearch query template."""
        comment = f"// Elasticsearch - {mode.value.upper()} Query"
        if technique_id:
            comment += f"\n// MITRE Technique: {technique_id}"
        if technique_name:
            comment += f" ({technique_name})"
        
        if mode == QueryMode.MANUAL:
            return f"""{comment}
{{
  "query": {{
    "bool": {{
      "must": [
        {{
          "range": {{
            "@timestamp": {{
              "gte": "now-7d/d",
              "lte": "now"
            }}
          }}
        }},
        {{
          "match": {{
            "event.action": "suspicious_pattern"
          }}
        }}
      ]
    }}
  }},
  "sort": [
    {{
      "@timestamp": {{
        "order": "desc"
      }}
    }}
  ],
  "size": 1000
}}

// Instructions:
// 1. Replace "suspicious_pattern" with the actual pattern you're looking for
// 2. Adjust the time range by changing "now-7d/d" (e.g., "now-1d/d", "now-30d/d")
// 3. Replace "event.action" with the field you want to search
// 4. Adjust the "size" parameter to change the number of results (max: 10000)
// 5. Execute in Kibana Dev Tools or Elasticsearch API
// 6. Export results as JSON or CSV
"""
        else:  # API mode
            return f"""{comment}
{{
  "query": {{
    "bool": {{
      "must": [
        {{
          "range": {{
            "@timestamp": {{
              "gte": "now-{{{{time_range}}}}/d",
              "lte": "now"
            }}
          }}
        }},
        {{
          "match": {{
            "event.action": "suspicious_pattern"
          }}
        }}
      ]
    }}
  }},
  "sort": [
    {{
      "@timestamp": {{
        "order": "desc"
      }}
    }}
  ],
  "size": 1000
}}

// Note: This query uses placeholder {{{{time_range}}}} that will be replaced
// by the query_generator service when executing via API.
// The query_generator will also replace "suspicious_pattern" with actual values.
"""
    
    @staticmethod
    def _get_generic_template(
        mode: QueryMode,
        technique_id: Optional[str] = None,
        technique_name: Optional[str] = None
    ) -> str:
        """Get generic SIEM query template."""
        comment = f"Generic SIEM Query - {mode.value.upper()} Execution"
        if technique_id:
            comment += f"\nMITRE Technique: {technique_id}"
        if technique_name:
            comment += f" ({technique_name})"
        
        return f"""{comment}
=====================================

Description: Generic query template for SIEM tools that are not specifically supported.
Adapt this query to match your SIEM tool's query language.

Query Template:
--------------
Search for events where:
- Time range: Last 7 days
- Field: action contains "suspicious_pattern"
- Field: user is not empty
- Field: host is not empty

Sort by: timestamp (descending)
Limit: 1000 results

Example Adaptations:
-------------------

For QRadar:
SELECT * FROM events WHERE action LIKE '%suspicious_pattern%' 
AND startTime >= NOW() - INTERVAL '7' DAY
ORDER BY startTime DESC
LIMIT 1000

For ArcSight:
action contains "suspicious_pattern" AND startTime >= NOW() - 7d
| sort startTime desc
| head 1000

For LogRhythm:
SELECT * FROM Log WHERE Action LIKE '%suspicious_pattern%'
AND DateOccurred >= DATEADD(day, -7, GETDATE())
ORDER BY DateOccurred DESC
LIMIT 1000

Instructions:
-------------
1. Identify your SIEM tool's query language
2. Adapt the query template above to match your tool's syntax
3. Replace "suspicious_pattern" with the actual pattern you're looking for
4. Adjust the time range (default: 7 days)
5. Execute the query in your SIEM tool
6. Export results as CSV or JSON
7. Save the file with a descriptive name
"""
    
    @staticmethod
    def get_tool_from_name(tool_name: str) -> Optional[QueryTool]:
        """
        Convert tool name string to QueryTool enum.
        
        Args:
            tool_name: Tool name (case-insensitive)
        
        Returns:
            QueryTool enum or None if not found
        """
        tool_name_lower = tool_name.lower().strip()
        
        mapping = {
            "microsoft defender": QueryTool.MICROSOFT_DEFENDER,
            "microsoft defender for endpoint": QueryTool.MICROSOFT_DEFENDER,
            "defender": QueryTool.MICROSOFT_DEFENDER,
            "microsoft sentinel": QueryTool.MICROSOFT_SENTINEL,
            "sentinel": QueryTool.MICROSOFT_SENTINEL,
            "splunk": QueryTool.SPLUNK,
            "elasticsearch": QueryTool.ELASTICSEARCH,
            "elastic": QueryTool.ELASTICSEARCH,
            "generic siem": QueryTool.GENERIC_SIEM,
            "generic": QueryTool.GENERIC_SIEM,
        }
        
        return mapping.get(tool_name_lower)

