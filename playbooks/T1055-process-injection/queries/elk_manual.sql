-- T1055 Process Injection: detect VirtualAllocEx, WriteProcessMemory, CreateRemoteThread
-- Required placeholders: {{timestamp_start}}, {{timestamp_end}}
SELECT *
FROM sysmon_events
WHERE event_type IN ('VirtualAllocEx', 'WriteProcessMemory', 'CreateRemoteThread')
  AND timestamp >= '{{timestamp_start}}'
  AND timestamp <= '{{timestamp_end}}'
ORDER BY timestamp DESC;
