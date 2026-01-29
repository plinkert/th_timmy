-- Threat hunt query 2 - adapt for technique
-- Relative time: last 7 days (change INTERVAL for 30 days: INTERVAL '30 days')
SELECT *
FROM events
WHERE timestamp >= NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
