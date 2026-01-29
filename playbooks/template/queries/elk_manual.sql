-- Threat hunt: suspicious PowerShell execution
-- Relative time: last 7 days (change INTERVAL for 30 days: INTERVAL '30 days')
SELECT *
FROM events
WHERE process_name LIKE '%powershell%'
  AND timestamp >= NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
