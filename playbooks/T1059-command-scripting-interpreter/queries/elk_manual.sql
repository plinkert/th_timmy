-- T1059 Command and Scripting Interpreter: suspicious PowerShell/cmd/bash
-- Required placeholders: {{timestamp_start}}, {{timestamp_end}}
SELECT *
FROM events
WHERE (process_name LIKE '%powershell%' OR process_name LIKE '%cmd%' OR process_name LIKE '%bash%')
  AND (command_line LIKE '%EncodedCommand%' OR command_line LIKE '%IEX%' OR command_line LIKE '%Invoke-Expression%')
  AND timestamp >= '{{timestamp_start}}'
  AND timestamp <= '{{timestamp_end}}'
ORDER BY timestamp DESC;
