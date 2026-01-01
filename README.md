# Discord_Bots
Repository of different discord bots written with vibe coding

# Discord Application Tracker Setup

## 1. Install Dependencies
Create a **```requirements.txt```** file:
```
discord.py
psutil
supabase
python-dotenv
```
Install with:
```
bashpip install -r requirements.txt
```
## 2. Setup Supabase (Free Database)
1. Go to [supabase.com](#https://supabase.com) and create a free account
2. Create a new project
3. Go to the SQL Editor and run this to create your table:

```
CREATE TABLE app_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    application_name TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_seconds NUMERIC NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_app_name ON app_usage(application_name);
CREATE INDEX idx_start_time ON app_usage(start_time);
```
4. Get your credentials from Settings → API:
    * SUPABASE_URL (Project URL)
    * SUPABASE_KEY (anon/public key)

## 3. Setup Discord Bot

1. Go to [Discord Developer Portal](#https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" section and click "Add Bot"
4. Enable these intents:
    * Message Content Intent
    * Presence Intent (if you want to track Discord usage)
5. Copy your bot token
    1. Go to Discord Developer Portal
    2. Click on your application (the one you created)
    3. Click "**Bot**" in the left sidebar
    4. Under the bot's username, you'll see a section called "**TOKEN**"
    5. Click "**Reset Token**" (if it's your first time) or "**Copy**" if the token is already visible
    6. Copy this token and save it somewhere safe (you'll paste it into your ```.env``` file later) <br/>
        ⚠️ Keep this secret! Don't share it with anyone or post it publicly
6. Invite bot to your server using OAuth2 URL Generator:
    1. Still in the Discord Developer Portal, click "OAuth2" in the left sidebar
    2. Click "URL Generator" (it's a sub-menu under OAuth2)
    3. In the SCOPES section, check the box for: </br>
        ✅ bot </br>
    4. A new **BOT PERMISSIONS** section will appear below
    5. In the BOT **PERMISSIONS** section, check these boxes: </br>
        ✅ Send Messages </br>
        ✅ Read Messages/View Channels (might be called "**View Channels**") </br>
    6. At the very bottom, you'll see a **GENERATED URL**
    7. Copy that URL and paste it into your web browser
    8. Select which server you want to add the bot to (you need to be an admin of that server)
    9. Click "**Authorize**" </br>
    
    Your bot should now appear in your server (it'll be offline until you run the Python script).

## 4. Create .env File
Create a ```.env``` file in your project directory:
```
DISCORD_TOKEN=your_discord_bot_token_here
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here
```
## 5. Run the Bot
```
bashpython bot.py
```
## 6. Using the Bot
Once running, use these Discord commands:

* !stats - View total usage for all applications
* !stats chrome.exe - View usage for a specific app
* !today - View today's usage statistics

## 7. Query Database Directly
You can query your data anytime through Supabase dashboard: </br>
*-- Total time per application*
```
SELECT 
    application_name,
    SUM(duration_seconds) / 3600 as total_hours
FROM app_usage
GROUP BY application_name
ORDER BY total_hours DESC;
```

*-- Usage by date*
```
SELECT 
    DATE(start_time) as date,
    application_name,
    SUM(duration_seconds) / 3600 as hours
FROM app_usage
GROUP BY date, application_name
ORDER BY date DESC, hours DESC;
```
