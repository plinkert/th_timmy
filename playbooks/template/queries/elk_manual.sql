-- Threat hunt: suspicious PowerShell execution
-- Required placeholders: {{timestamp_start}}, {{timestamp_end}}
SELECT *
FROM events
WHERE process_name LIKE '%powershell%'
  AND timestamp >= '{{timestamp_start}}'
  AND timestamp <= '{{timestamp_end}}'
ORDER BY timestamp DESC;
