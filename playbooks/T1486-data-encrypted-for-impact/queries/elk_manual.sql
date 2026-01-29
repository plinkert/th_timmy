-- T1486 Data Encrypted for Impact: ransomware indicators
-- Required placeholders: {{timestamp_start}}, {{timestamp_end}}
SELECT *
FROM events
WHERE (command_line LIKE '%vssadmin%delete%' OR command_line LIKE '%bcdedit%'
   OR command_line LIKE '%wbadmin%' OR command_line LIKE '%shadow%'
   OR event_type = 'FileCreate' AND file_extension IN ('.encrypted', '.locked', '.crypto'))
  AND timestamp >= '{{timestamp_start}}'
  AND timestamp <= '{{timestamp_end}}'
ORDER BY timestamp DESC;
