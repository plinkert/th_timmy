-- Fixture query 2 - relative time (last 7 days)
SELECT * FROM events WHERE timestamp >= NOW() - INTERVAL '7 days';
