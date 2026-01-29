-- T1082 System Information Discovery: systeminfo, hostname, whoami, env
-- Required placeholders: {{timestamp_start}}, {{timestamp_end}}
SELECT *
FROM events
WHERE (command_line LIKE '%systeminfo%' OR command_line LIKE '%hostname%'
   OR command_line LIKE '%whoami%' OR command_line LIKE '%ipconfig%'
   OR command_line LIKE '%uname%')
  AND timestamp >= '{{timestamp_start}}'
  AND timestamp <= '{{timestamp_end}}'
ORDER BY timestamp DESC;
