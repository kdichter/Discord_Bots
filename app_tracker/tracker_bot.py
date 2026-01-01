import discord
from discord.ext import commands, tasks
import psutil
import datetime
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Track current sessions
current_sessions = {}

# Applications to track - add your apps here!
TRACKED_APPS = {
    # Browsers
    "chrome.exe",
    "firefox.exe",
    "steam.exe",

    # Development
    "Code.exe",           # VS Code
    "idea64.exe"
    "pycharm64.exe",
    "notepad++.exe",

    # Communication
    "Discord.exe",
    "Teams.exe",

    # Media
    "spotify.exe",
    "stremio-shell-ng.exe"
}


def get_active_applications():
    """Get list of currently running applications (filtered by TRACKED_APPS)"""
    apps = set()
    # Create lowercase version of tracked apps for case-insensitive matching
    tracked_lower = {app.lower(): app for app in TRACKED_APPS}

    for proc in psutil.process_iter(['name', 'exe']):
        try:
            proc_name = proc.info['name']

            # Check if in tracked apps (case-insensitive)
            if proc_name.lower() in tracked_lower:
                apps.add(proc_name)
            # Auto-detect Steam games (check if launched from Steam directory)
            elif proc.info['exe'] and 'steam' in proc.info['exe'].lower() and 'steamapps' in proc.info['exe'].lower():
                apps.add(proc_name)
                print(f"Detected Steam game: {proc_name}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
            pass
    return apps


@bot.event
async def on_ready():
    print(f'{bot.user} is now tracking applications!')
    track_applications.start()


@tasks.loop(seconds=30)  # Check every 30 seconds
async def track_applications():
    """Monitor running applications and log changes"""
    current_apps = get_active_applications()
    user_id = str(bot.user.id)  # You can customize this per user

    # Check for newly started apps
    for app in current_apps:
        if app not in current_sessions:
            # App started
            current_sessions[app] = datetime.datetime.now()
            print(f"Started: {app}")

    # Check for closed apps
    closed_apps = set(current_sessions.keys()) - current_apps
    for app in closed_apps:
        # App closed - log to database
        start_time = current_sessions[app]
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Only log if session lasted longer than 180 seconds (filters out quick alt-tabs)
        if duration > 180:
            try:
                # Format date and times separately
                session_date = start_time.strftime("%Y-%m-%d")
                start_formatted = start_time.strftime("%H:%M:%S")
                end_formatted = end_time.strftime("%H:%M:%S")

                # Format duration as HH:MM:SS
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                seconds = int(duration % 60)
                duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                data = {
                    "user_id": user_id,
                    "application_name": app,
                    "session_date": session_date,
                    "start_time": start_formatted,
                    "end_time": end_formatted,
                    "duration": duration_formatted
                }
                supabase.table("app_usage").insert(data).execute()
                print(f"Logged: {app} - {duration_formatted}")
            except Exception as e:
                print(f"Error logging {app}: {e}")
        else:
            print(f"Skipped (too short): {app} - {duration:.0f}s")

        del current_sessions[app]


@bot.command()
async def stats(ctx, app_name: str = None):
    """Get usage statistics for an application"""
    try:
        if app_name:
            # Get stats for specific app
            response = supabase.table("app_usage").select("*").eq("application_name", app_name).execute()
            total_time = sum(row['duration_seconds'] for row in response.data)
            hours = total_time / 3600
            await ctx.send(f"**{app_name}**: {hours:.2f} hours total")
        else:
            # Get stats for all apps
            response = supabase.table("app_usage").select("*").execute()

            # Aggregate by app
            app_totals = {}
            for row in response.data:
                app = row['application_name']
                app_totals[app] = app_totals.get(app, 0) + row['duration_seconds']

            # Sort by time
            sorted_apps = sorted(app_totals.items(), key=lambda x: x[1], reverse=True)[:10]

            message = "**Top 10 Applications:**\n"
            for app, seconds in sorted_apps:
                hours = seconds / 3600
                message += f"• {app}: {hours:.2f} hours\n"

            await ctx.send(message)
    except Exception as e:
        await ctx.send(f"Error fetching stats: {e}")


@bot.command()
async def today(ctx):
    """Get today's usage statistics"""
    try:
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        response = supabase.table("app_usage").select("*").gte("start_time", today_start.isoformat()).execute()

        app_totals = {}
        for row in response.data:
            app = row['application_name']
            app_totals[app] = app_totals.get(app, 0) + row['duration_seconds']

        sorted_apps = sorted(app_totals.items(), key=lambda x: x[1], reverse=True)[:10]

        message = "**Today's Top Applications:**\n"
        for app, seconds in sorted_apps:
            hours = seconds / 3600
            message += f"• {app}: {hours:.2f} hours\n"

        await ctx.send(message)
    except Exception as e:
        await ctx.send(f"Error fetching today's stats: {e}")


# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))