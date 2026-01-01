import discord
from discord.ext import commands, tasks
import datetime
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import platform

# Platform-specific imports for getting active window
if platform.system() == "Windows":
    import win32gui
    import win32process
    import psutil
elif platform.system() == "Darwin":  # macOS
    from AppKit import NSWorkspace
elif platform.system() == "Linux":
    import subprocess

load_dotenv()

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Track current active app
current_app = None
session_start = None
previous_app = None  # Track what we were on before
grace_period_start = None  # When did we switch away
MIN_SESSION_DURATION = 180  # Only log sessions longer than this (in seconds)
GRACE_PERIOD = 120  # If we return within this time, continue the session (in seconds)

# Applications to track - add your apps here!
TRACKED_APPS = {
    "chrome.exe",
    "Code.exe",
    "Discord.exe",
    # Add more applications you want to track
}


def get_active_window_name():
    """Get the name of the currently active/focused window"""
    try:
        if platform.system() == "Windows":
            # Windows
            window = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(window)
            process = psutil.Process(pid)
            return process.name()

        elif platform.system() == "Darwin":
            # macOS
            active_app = NSWorkspace.sharedWorkspace().activeApplication()
            return active_app['NSApplicationName'] + ".app"

        elif platform.system() == "Linux":
            # Linux (requires xdotool)
            result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowname'],
                                    capture_output=True, text=True)
            return result.stdout.strip()
    except Exception as e:
        print(f"Error getting active window: {e}")
        return None


def should_track(app_name):
    """Check if app should be tracked (case-insensitive)"""
    if not app_name:
        return False

    # Check against Steam games
    if 'steam' in app_name.lower() and 'steamapps' in app_name.lower():
        return True

    # Check against tracked apps (case-insensitive)
    tracked_lower = {app.lower() for app in TRACKED_APPS}
    return app_name.lower() in tracked_lower


@bot.event
async def on_ready():
    print(f'{bot.user} is now tracking active windows!')
    track_active_window.start()


@tasks.loop(seconds=30)  # Check every 30 seconds for reasonable accuracy
async def track_active_window():
    """Monitor active window and log when it changes"""
    global current_app, session_start, previous_app, grace_period_start

    active_app = get_active_window_name()

    # Only track if it's in our list
    if not should_track(active_app):
        # If we were tracking something, start grace period
        if current_app and not grace_period_start:
            previous_app = current_app
            grace_period_start = datetime.datetime.now()
            print(f"Grace period started for {previous_app}")

        # Check if grace period expired
        if grace_period_start:
            elapsed = (datetime.datetime.now() - grace_period_start).total_seconds()
            if elapsed > GRACE_PERIOD:
                # Grace period expired, log the session
                if previous_app:
                    log_session(previous_app, session_start, grace_period_start)
                current_app = None
                session_start = None
                previous_app = None
                grace_period_start = None
        return

    # We're back on a tracked app
    # Check if we returned to the previous app within grace period
    if grace_period_start and active_app == previous_app:
        # Returned within grace period! Continue the session
        print(f"Returned to {active_app} within grace period - continuing session")
        current_app = previous_app
        previous_app = None
        grace_period_start = None
        # session_start stays the same - we're continuing!
        return

    # Grace period ended or different app
    if grace_period_start:
        # We switched to a different app after grace period or switched to new tracked app
        log_session(previous_app, session_start, grace_period_start)
        previous_app = None
        grace_period_start = None

    # Check if app changed (and wasn't covered by grace period)
    if active_app != current_app:
        # Log previous session if exists
        if current_app:
            log_session(current_app, session_start, datetime.datetime.now())

        # Start new session
        current_app = active_app
        session_start = datetime.datetime.now()
        print(f"Now tracking: {current_app}")


def log_session(app, start_time, end_time):
    """Log completed session to database"""
    duration = (end_time - start_time).total_seconds()

    # Only log if session lasted longer than minimum duration
    if duration > MIN_SESSION_DURATION:
        try:
            # Format date and times
            session_date = start_time.strftime("%Y-%m-%d")
            start_formatted = start_time.strftime("%H:%M:%S")
            end_formatted = end_time.strftime("%H:%M:%S")

            # Format duration as HH:MM:SS
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            data = {
                "user_id": str(bot.user.id),
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


@bot.command()
async def stats(ctx, app_name: str = None):
    """Get usage statistics for an application"""
    try:
        if app_name:
            response = supabase.table("app_usage").select("*").eq("application_name", app_name).execute()
            total_seconds = sum(
                sum(int(x) * 60 ** i for i, x in enumerate(reversed(row['duration'].split(':'))))
                for row in response.data
            )
            hours = total_seconds / 3600
            await ctx.send(f"**{app_name}**: {hours:.2f} hours total")
        else:
            response = supabase.table("app_usage").select("*").execute()

            app_totals = {}
            for row in response.data:
                app = row['application_name']
                h, m, s = map(int, row['duration'].split(':'))
                seconds = h * 3600 + m * 60 + s
                app_totals[app] = app_totals.get(app, 0) + seconds

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

        response = supabase.table("app_usage").select("*").eq("session_date",
                                                              today_start.strftime("%Y-%m-%d")).execute()

        app_totals = {}
        for row in response.data:
            app = row['application_name']
            h, m, s = map(int, row['duration'].split(':'))
            seconds = h * 3600 + m * 60 + s
            app_totals[app] = app_totals.get(app, 0) + seconds

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