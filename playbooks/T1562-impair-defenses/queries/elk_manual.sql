-- T1562 Impair Defenses: disable AV, EDR, logs
-- Required placeholders: {{timestamp_start}}, {{timestamp_end}}
SELECT *
FROM events
WHERE (command_line LIKE '%Disable-WindowsDefender%' OR command_line LIKE '%Set-MpPreference%'
   OR command_line LIKE '%auditpol%' OR command_line LIKE '%reg delete%'
   OR command_line LIKE '%DisableRealtimeMonitoring%')
  AND timestamp >= '{{timestamp_start}}'
  AND timestamp <= '{{timestamp_end}}'
ORDER BY timestamp DESC;
