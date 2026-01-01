# Discord_Bots
Repository of different discord bots written with vibe coding

PACKAGE INSTALLATIONS
pip install -r requirements.txt

QUERIES
-- Total time per application
SELECT 
    application_name,
    SUM(duration_seconds) / 3600 as total_hours
FROM app_usage
GROUP BY application_name
ORDER BY total_hours DESC;

-- Usage by date
SELECT 
    DATE(start_time) as date,
    application_name,
    SUM(duration_seconds) / 3600 as hours
FROM app_usage
GROUP BY date, application_name
ORDER BY date DESC, hours DESC;
