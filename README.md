# Discord_Bots
Repository of different discord bots written with vibe coding

PACKAGE INSTALLATIONS <br/>
```
pip install -r requirements.txt
```

RUN THE BOT <br/>
```
python bot.py
```

USING THE BOT <br/>
```
Once running, use these Discord commands:

!stats - View total usage for all applications
!stats chrome.exe - View usage for a specific app
!today - View today's usage statistics
```

QUERY DATABASE DIRECTLY <br/>
1. **Total time per application**
```
SELECT 
    application_name,
    SUM(duration_seconds) / 3600 as total_hours
FROM app_usage
GROUP BY application_name
ORDER BY total_hours DESC;
```
2. **Usage by date**
```
SELECT 
    DATE(start_time) as date,
    application_name,
    SUM(duration_seconds) / 3600 as hours
FROM app_usage
GROUP BY date, application_name
ORDER BY date DESC, hours DESC;
```
