import asyncio
import collections
import discord
import requests
import base64
import os
import random
import string
import threading
import time
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from flask import Flask, request as flask_req

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
GITHUB_REPO = "pympleHUB/obfuscatedPYMPLE"
KEY_FILE = "pympleKeyBot"
HISTORY_FILE = "pympleKeyHistory"
ROTATION_COUNT_FILE = "pympleKeyCount"
EXEC_COUNT_FILE = "pympleExecCount"
ANNOUNCE_CHANNEL_ID = int(os.environ["ANNOUNCE_CHANNEL_ID"])
EXEC_STATS_CHANNEL_ID = int(os.environ.get("EXEC_STATS_CHANNEL_ID", 0))
REPORTS_CHANNEL_ID = int(os.environ.get("REPORTS_CHANNEL_ID", 0))
LOG_CHANNEL_ID = 1239788452623417405
THUMBNAIL_URL = os.environ.get("THUMBNAIL_URL", "")
ROBLOX_USER_ID = 583572860
OWNER_ID = 431103247478947850

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

last_announce_msg_id = None
bot_start_time = None
last_rotation_time = None
_recent_joins = {}
ROTATION_HOURS = 6.0
total_reports = 0
recent_key_channel_msgs = collections.deque(maxlen=20)

COLORS = [
    0xDC3C3C, 0x3C6EDC, 0x8C3CDC,
    0xDC8C3C, 0x3CDC8C, 0xDC3C8C, 0x3CDCDC,
]

GREETINGS = [
    "Key Drop!",
    "New Key Alert!",
    "Key Update!",
    "Fresh Key Just Dropped!",
    "Key Rotation!",
    "New Key Available!",
    "PYMPLE Key Update!",
    "New Key Just Dropped!",
    "Access Granted — New Key!",
    "The Vault Has Been Unlocked!",
    "Your New Key Awaits!",
    "Key Has Been Refreshed!",
    "Stay Sharp — New Key!",
    "New Key, Who Dis?",
    "The Key Has Changed!",
    "Locked and Loaded — New Key!",
    "Don't Miss This — New Key!",
    "Key Alert — Act Fast!",
    "Fresh Access, Fresh Key!",
    "Time to Update Your Key!",
]


class ReportModal(discord.ui.Modal, title="Report an Issue"):
    description = discord.ui.TextInput(
        label="Describe the issue",
        placeholder="Tell us what went wrong...",
        style=discord.TextStyle.long,
        max_length=1000,
        required=True
    )

    def __init__(self, key: str):
        super().__init__()
        self.key = key

    async def on_submit(self, interaction: discord.Interaction):
        global total_reports
        total_reports += 1
        embed = discord.Embed(title="🚨 Issue Report", color=0xE74C3C, timestamp=datetime.now())
        embed.add_field(name="Reported By", value=f"{interaction.user} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="Description", value=self.description.value, inline=False)
        embed.add_field(name="Key at Report", value=f"`{self.key}`", inline=True)
        embed.add_field(name="Total Reports", value=str(total_reports), inline=True)
        embed.set_footer(text="pympleHUB • Reports")
        if REPORTS_CHANNEL_ID:
            channel = bot.get_channel(REPORTS_CHANNEL_ID)
            if channel:
                await channel.send(embed=embed)
        await log("🚨 Issue Reported", 0xE74C3C, [
            ("Reported By", f"{interaction.user} (`{interaction.user.id}`)", False),
            ("Description", self.description.value[:1024], False),
            ("Key at Report", f"`{self.key}`", True),
        ])
        await interaction.response.send_message("Your report has been submitted. Thank you!", ephemeral=True)


class CopyKeyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        loadstring_btn = discord.ui.Button(label="Script", style=discord.ButtonStyle.success, emoji="📜", custom_id="pymple_loadstring")
        loadstring_btn.callback = self._loadstring
        self.add_item(loadstring_btn)

        copy_btn = discord.ui.Button(label="Copy Key", style=discord.ButtonStyle.primary, emoji="📋", custom_id="pymple_copy_key")
        copy_btn.callback = self._copy_key
        self.add_item(copy_btn)

        self.add_item(discord.ui.Button(
            label="Watch on YouTube",
            style=discord.ButtonStyle.link,
            url="https://www.youtube.com/@scriptsHUB/featured",
            emoji="📌"
        ))

        report_btn = discord.ui.Button(label="Report Issue", style=discord.ButtonStyle.danger, emoji="🚨", custom_id="pymple_report_issue")
        report_btn.callback = self._report_issue
        self.add_item(report_btn)

    async def _copy_key(self, interaction: discord.Interaction):
        key = "Key not found"
        if interaction.message and interaction.message.embeds:
            first_line = (interaction.message.embeds[0].description or "").split("\n")[0]
            key = first_line.replace("# ", "").replace("`", "").strip()
        announcement_color = 0x2b2d31
        if interaction.message and interaction.message.embeds:
            c = interaction.message.embeds[0].color
            if c:
                announcement_color = c.value
        embed = discord.Embed(
            description=f"```\n{key}\n```",
            color=announcement_color
        )
        embed.set_footer(text="Select all and copy the text above")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _loadstring(self, interaction: discord.Interaction):
        announcement_color = 0x2b2d31
        if interaction.message and interaction.message.embeds:
            c = interaction.message.embeds[0].color
            if c:
                announcement_color = c.value
        ls = 'loadstring(game:HttpGet("https://raw.githubusercontent.com/pympleHUB/obfuscatedPYMPLE/refs/heads/main/MainLoaderUI"))()'
        embed = discord.Embed(
            description=f"```\n{ls}\n```",
            color=announcement_color
        )
        embed.set_footer(text="Select all and copy the text above")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _report_issue(self, interaction: discord.Interaction):
        key = "Unknown"
        if interaction.message and interaction.message.embeds:
            first_line = (interaction.message.embeds[0].description or "").split("\n")[0]
            key = first_line.replace("# ", "").replace("`", "").strip()
        modal = ReportModal(key)
        await interaction.response.send_modal(modal)


# --- GitHub helpers ---

def gh_get(filename):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        return base64.b64decode(data["content"]).decode().strip(), data["sha"]
    return None, None

def gh_put(filename, content_str, commit_msg="Update"):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    _, sha = gh_get(filename)
    data = {
        "message": commit_msg,
        "content": base64.b64encode(content_str.encode()).decode()
    }
    if sha:
        data["sha"] = sha
    r = requests.put(url, json=data, headers=headers)
    return r.status_code in (200, 201)

def gh_delete(filename):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    _, sha = gh_get(filename)
    if sha:
        requests.delete(url, json={"message": "Delete file", "sha": sha}, headers=headers)

def get_roblox_avatar():
    try:
        r = requests.get(
            f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
            f"?userIds={ROBLOX_USER_ID}&size=420x420&format=Png&isCircular=false"
        )
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                return data[0].get("imageUrl", "")
    except:
        pass
    return ""

def get_cat_gif():
    try:
        r = requests.get("https://api.thecatapi.com/v1/images/search?mime_types=gif", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data:
                return data[0].get("url", "")
    except:
        pass
    return ""

def generate_key():
    return "PYMPLE-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def update_key(new_key):
    return gh_put(KEY_FILE, new_key, "Update key")

def add_to_history(new_key):
    existing, _ = gh_get(HISTORY_FILE)
    lines = [l for l in (existing or "").split("\n") if l.strip()]
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    lines.insert(0, f"{timestamp}|{new_key}")
    gh_put(HISTORY_FILE, "\n".join(lines[:10]), "Update key history")

def increment_rotation_count():
    content, sha = gh_get(ROTATION_COUNT_FILE)
    try:
        count = int(content or 0) + 1
    except:
        count = 1
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ROTATION_COUNT_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    data = {
        "message": "Update rotation count",
        "content": base64.b64encode(str(count).encode()).decode()
    }
    if sha:
        data["sha"] = sha
    requests.put(url, json=data, headers=headers)
    return count

def get_rotation_count():
    content, _ = gh_get(ROTATION_COUNT_FILE)
    try:
        return int(content or 0)
    except:
        return 0

def get_exec_count():
    content, _ = gh_get(EXEC_COUNT_FILE)
    try:
        return int(content or 0)
    except:
        return 0

def increment_exec_count():
    content, sha = gh_get(EXEC_COUNT_FILE)
    try:
        count = int(content or 0) + 1
    except:
        count = 1
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{EXEC_COUNT_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    data = {
        "message": "Update exec count",
        "content": base64.b64encode(str(count).encode()).decode()
    }
    if sha:
        data["sha"] = sha
    requests.put(url, json=data, headers=headers)
    return count

async def update_exec_channel(count):
    if not EXEC_STATS_CHANNEL_ID:
        return
    channel = bot.get_channel(EXEC_STATS_CHANNEL_ID)
    if channel:
        try:
            await channel.edit(name=f"Executes: {count:,}")
        except:
            pass


# --- Logging ---

async def log(title, color, fields: list):
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            return
        embed = discord.Embed(title=title, color=color, timestamp=datetime.now())
        for name, value, inline in fields:
            embed.add_field(name=name, value=str(value)[:1024], inline=inline)
        embed.set_footer(text="pympleHUB logs")
        await log_channel.send(embed=embed)
    except:
        pass

async def log_rotation(new_key, triggered_by="Auto-rotation"):
    global last_rotation_time
    last_rotation_time = datetime.now()
    fields = [
        ("New Key", f"`{new_key}`", False),
        ("Triggered By", triggered_by, True),
    ]
    next_run = auto_rotate_key.next_iteration
    if next_run:
        fields.append(("Next Rotation", f"<t:{int(next_run.timestamp())}:R>", True))
    await log("🔑 Key Rotated", 0x2ECC71, fields)


# --- Core logic ---

async def expire_last_message():
    global last_announce_msg_id
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return
    msg_id = last_announce_msg_id
    if not msg_id:
        async for m in channel.history(limit=10):
            if m.author == bot.user and m.embeds:
                msg_id = m.id
                break
    if not msg_id:
        return
    try:
        old_msg = await channel.fetch_message(msg_id)
        await old_msg.delete()
    except:
        pass
    finally:
        last_announce_msg_id = None

async def announce_key(new_key, expires_at=None):
    global last_announce_msg_id
    await expire_last_message()

    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return

    color = random.choice(COLORS)
    greeting = random.choice(GREETINGS)
    rotation_count, cat_gif = await asyncio.gather(
        asyncio.to_thread(get_rotation_count),
        asyncio.to_thread(get_cat_gif),
    )

    desc = f"# `{new_key}`\n\n"
    if expires_at:
        ts = int(expires_at.timestamp())
        desc += f"Key will be resetting <t:{ts}:R>! Please check out <#1183563684828688446> for all of my projects!\n\nALL script-related videos are found on my YouTube Channel, linked below! Please Subscribe, Comment, and Like!"
    else:
        desc += "Key will be resetting soon! Please check out <#1183563684828688446> for all of my projects!\n\nALL script-related videos are found on my YouTube Channel, linked below! Please Subscribe, Comment, and Like!"

    today = datetime.now().strftime("%B %d, %Y")
    embed = discord.Embed(title=greeting, description=desc, color=color)
    embed.set_footer(text=f"pympleHUB • Key #{rotation_count} • {today}")

    thumb = THUMBNAIL_URL or bot.user.display_avatar.url
    embed.set_thumbnail(url=thumb)
    if cat_gif:
        embed.set_image(url=cat_gif)

    msg = await channel.send(embed=embed, view=CopyKeyView())
    last_announce_msg_id = msg.id


# --- Owner check helpers ---

def owner_only(ctx):
    return ctx.author.id == OWNER_ID

async def delete_cmd(ctx):
    try:
        await ctx.message.delete()
    except:
        pass

async def log_cmd(ctx):
    await log("⌨️ Command Used", 0x3C6EDC, [
        ("Command", f"`{ctx.message.content}`", False),
        ("User", f"{ctx.author} (`{ctx.author.id}`)", True),
        ("Channel", f"<#{ctx.channel.id}>", True),
    ])

async def log_unauthorized(ctx):
    await log("🚫 Unauthorized Attempt", 0xE67E22, [
        ("Command", f"`{ctx.message.content}`", False),
        ("User", f"{ctx.author} (`{ctx.author.id}`)", True),
        ("Channel", f"<#{ctx.channel.id}>", True),
    ])


# --- Tasks ---

@tasks.loop(hours=6)
async def auto_rotate_key():
    if auto_rotate_key.current_loop == 0:
        return
    new_key = generate_key()
    if await asyncio.to_thread(update_key, new_key):
        await asyncio.to_thread(add_to_history, new_key)
        await asyncio.to_thread(increment_rotation_count)
        await log_rotation(new_key, triggered_by="Auto-rotation")
        await announce_key(new_key, expires_at=datetime.now() + timedelta(hours=ROTATION_HOURS))

@tasks.loop(minutes=30)
async def clean_key_channel():
    if clean_key_channel.current_loop == 0:
        return
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return
    try:
        deleted = await channel.purge(limit=50, check=lambda m: m.id != last_announce_msg_id)
        if deleted:
            await log("🧹 Channel Cleaned", 0x95A5A6, [
                ("Messages Deleted", str(len(deleted)), True),
                ("Channel", f"<#{ANNOUNCE_CHANNEL_ID}>", True),
            ])
    except:
        pass

@tasks.loop(hours=1)
async def missed_rotation_check():
    if missed_rotation_check.current_loop == 0:
        return
    if not last_rotation_time:
        return
    hours_since = (datetime.now() - last_rotation_time).total_seconds() / 3600
    if hours_since >= ROTATION_HOURS + 1:
        try:
            owner = await bot.fetch_user(OWNER_ID)
            ts = int(last_rotation_time.timestamp())
            await owner.send(
                f"⚠️ **Missed Rotation Alert**\n"
                f"Last rotation was <t:{ts}:R> — over `{ROTATION_HOURS}h` ago.\n"
                f"Auto-rotation may have failed. Use `!rotatenow` to fix it."
            )
        except:
            pass


# --- Commands ---

@bot.command()
async def addnote(ctx, *, text: str):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    await log("📝 Note", 0xF39C12, [
        ("Note", text, False),
        ("Added By", str(ctx.author), True),
    ])
    await ctx.author.send("Note logged to the log channel.")

@bot.command()
async def announce(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    key, _ = await asyncio.to_thread(gh_get, KEY_FILE)
    if not key:
        await ctx.author.send("No key set yet.")
        return
    next_run = auto_rotate_key.next_iteration
    expires_at = next_run.replace(tzinfo=None) if next_run else datetime.now() + timedelta(hours=ROTATION_HOURS)
    await announce_key(key, expires_at=expires_at)

@bot.command(name="bothelp")
async def bothelp(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    embed = discord.Embed(title="pympleHUB Commands", color=0xDC3C3C)
    embed.add_field(name="!addnote <text>", value="Log a timestamped note to the log channel", inline=False)
    embed.add_field(name="!announce", value="Re-post the current key without rotating", inline=False)
    embed.add_field(name="!bothelp", value="Shows this message", inline=False)
    embed.add_field(name="!broadcast <message>", value="Post a custom announcement embed to the key channel", inline=False)
    embed.add_field(name="!clearhistory", value="Wipe the key history", inline=False)
    embed.add_field(name="!getkey", value="Get the current key via DM", inline=False)
    embed.add_field(name="!keyhistory", value="View last 5 keys with timestamps via DM", inline=False)
    embed.add_field(name="!lockdown [seconds]", value="Enable slow mode on the key channel (default 30s)", inline=False)
    embed.add_field(name="!pauserotation", value="Pause auto-rotation", inline=False)
    embed.add_field(name="!ping", value="Check bot latency via DM", inline=False)
    embed.add_field(name="!resumerotation", value="Resume auto-rotation", inline=False)
    embed.add_field(name="!rotatenow", value="Instantly rotate to a new generated key", inline=False)
    embed.add_field(name="!setinterval <hours>", value="Change the auto-rotation interval", inline=False)
    embed.add_field(name="!setkey <key>", value="Set a specific key manually", inline=False)
    embed.add_field(name="!stats", value="Total rotations, reports, member count via DM", inline=False)
    embed.add_field(name="!status", value="Bot uptime, key, rotation state, latency via DM", inline=False)
    embed.add_field(name="!unlock", value="Remove slow mode from the key channel", inline=False)
    embed.set_footer(text="All commands auto-delete and respond via DM")
    await ctx.author.send(embed=embed)

@bot.command()
async def broadcast(ctx, *, message: str):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return
    thumb = THUMBNAIL_URL or bot.user.display_avatar.url
    today = datetime.now().strftime("%B %d, %Y")
    embed = discord.Embed(description=message, color=random.choice(COLORS), timestamp=datetime.now())
    embed.set_author(name="pympleHUB Announcement", icon_url=thumb)
    embed.set_footer(text=f"pympleHUB • {today}")
    await channel.send(embed=embed)

@bot.command()
async def clearhistory(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    await asyncio.to_thread(gh_delete, HISTORY_FILE)
    await ctx.author.send("Key history cleared.")

@bot.command()
async def getkey(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    key, _ = await asyncio.to_thread(gh_get, KEY_FILE)
    if key:
        await ctx.author.send(f"Current key: `{key}`")
    else:
        await ctx.author.send("No key set yet.")

@bot.command()
async def keyhistory(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    history, _ = await asyncio.to_thread(gh_get, HISTORY_FILE)
    if not history:
        await ctx.author.send("No key history yet.")
        return
    lines = [l for l in history.split("\n") if l.strip()][:5]
    embed = discord.Embed(title="Key History", color=0x8C3CDC)
    for i, line in enumerate(lines, 1):
        parts = line.split("|")
        if len(parts) == 2:
            ts_str, key = parts
            try:
                ts = int(datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S").timestamp())
                embed.add_field(name=f"#{i}", value=f"`{key}` — <t:{ts}:f>", inline=False)
            except:
                embed.add_field(name=f"#{i}", value=f"`{key}`", inline=False)
    embed.set_footer(text="pympleHUB • Last 5 keys")
    await ctx.author.send(embed=embed)

@bot.command()
async def lockdown(ctx, seconds: int = 30):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel:
        await channel.edit(slowmode_delay=seconds)
        await log("🔒 Channel Locked", 0xE74C3C, [
            ("Channel", f"<#{ANNOUNCE_CHANNEL_ID}>", True),
            ("Slow Mode", f"{seconds}s", True),
            ("By", str(ctx.author), True),
        ])
        await ctx.author.send(f"Slow mode set to `{seconds}s` in <#{ANNOUNCE_CHANNEL_ID}>.")

@bot.command()
async def pauserotation(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    if auto_rotate_key.is_running():
        auto_rotate_key.stop()
        await ctx.author.send("Auto-rotation paused.")
    else:
        await ctx.author.send("Auto-rotation is already paused.")

@bot.command()
async def ping(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    await ctx.author.send(f"Pong! `{round(bot.latency * 1000)}ms`")

@bot.command()
async def resumerotation(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    if not auto_rotate_key.is_running():
        auto_rotate_key.start()
        next_ts = int((datetime.now() + timedelta(hours=ROTATION_HOURS)).timestamp())
        await ctx.author.send(f"Auto-rotation resumed. Next rotation <t:{next_ts}:R>.")
    else:
        await ctx.author.send("Auto-rotation is already running.")

@bot.command()
async def rotatenow(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    new_key = generate_key()
    if await asyncio.to_thread(update_key, new_key):
        await asyncio.to_thread(add_to_history, new_key)
        await asyncio.to_thread(increment_rotation_count)
        auto_rotate_key.restart()
        await log_rotation(new_key, triggered_by=f"Manual — {ctx.author}")
        await announce_key(new_key, expires_at=datetime.now() + timedelta(hours=ROTATION_HOURS))
    else:
        try:
            await ctx.author.send("Failed to rotate key.")
        except:
            pass

@bot.command()
async def setinterval(ctx, hours: float):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    global ROTATION_HOURS
    ROTATION_HOURS = max(1.0, hours)
    try:
        if auto_rotate_key.is_running():
            auto_rotate_key.change_interval(hours=ROTATION_HOURS)
        else:
            auto_rotate_key.start()
            auto_rotate_key.change_interval(hours=ROTATION_HOURS)
    except:
        pass
    next_ts = int((datetime.now() + timedelta(hours=ROTATION_HOURS)).timestamp())
    await ctx.author.send(f"Rotation interval set to `{ROTATION_HOURS}h`. Next rotation <t:{next_ts}:R>.")

@bot.command()
async def setkey(ctx, new_key: str):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    if await asyncio.to_thread(update_key, new_key):
        await asyncio.to_thread(add_to_history, new_key)
        await asyncio.to_thread(increment_rotation_count)
        auto_rotate_key.restart()
        await log_rotation(new_key, triggered_by=f"Manual — {ctx.author}")
        await announce_key(new_key, expires_at=datetime.now() + timedelta(hours=ROTATION_HOURS))
    else:
        try:
            await ctx.author.send(f"Failed to update key to `{new_key}`.")
        except:
            pass

@bot.command()
async def stats(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    count = await asyncio.to_thread(get_rotation_count)
    uptime = datetime.now() - bot_start_time
    hours, rem = divmod(int(uptime.total_seconds()), 3600)
    minutes = rem // 60
    embed = discord.Embed(title="pympleHUB Stats", color=0x8C3CDC)
    embed.add_field(name="Total Rotations", value=str(count), inline=True)
    embed.add_field(name="Reports This Session", value=str(total_reports), inline=True)
    embed.add_field(name="Uptime", value=f"{hours}h {minutes}m", inline=True)
    if ctx.guild:
        embed.add_field(name="Server Members", value=f"{ctx.guild.member_count:,}", inline=True)
    embed.set_footer(text=f"pympleHUB • {datetime.now().strftime('%d %B %Y')}")
    await ctx.author.send(embed=embed)

@bot.command()
async def status(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    key, _ = await asyncio.to_thread(gh_get, KEY_FILE)
    uptime = datetime.now() - bot_start_time
    hours, rem = divmod(int(uptime.total_seconds()), 3600)
    minutes = rem // 60
    embed = discord.Embed(title="pympleHUB Bot Status", color=0x3C6EDC)
    embed.add_field(name="Current Key", value=f"`{key or 'Unknown'}`", inline=False)
    embed.add_field(name="Uptime", value=f"{hours}h {minutes}m", inline=True)
    embed.add_field(name="Rotation Interval", value=f"{ROTATION_HOURS}h", inline=True)
    rotation_state = "Running" if auto_rotate_key.is_running() else "Paused"
    embed.add_field(name="Auto-Rotation", value=rotation_state, inline=True)
    next_run = auto_rotate_key.next_iteration
    if next_run:
        ts = int(next_run.timestamp())
        embed.add_field(name="Next Rotation", value=f"<t:{ts}:R>", inline=True)
    if last_rotation_time:
        ts = int(last_rotation_time.timestamp())
        embed.add_field(name="Last Rotation", value=f"<t:{ts}:R>", inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.set_footer(text=f"pympleHUB • {datetime.now().strftime('%d %B %Y')}")
    await ctx.author.send(embed=embed)

@bot.command()
async def unlock(ctx):
    if not owner_only(ctx):
        await log_unauthorized(ctx)
        return
    await log_cmd(ctx)
    await delete_cmd(ctx)
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel:
        await channel.edit(slowmode_delay=0)
        await log("🔓 Channel Unlocked", 0x2ECC71, [
            ("Channel", f"<#{ANNOUNCE_CHANNEL_ID}>", True),
            ("By", str(ctx.author), True),
        ])
        await ctx.author.send(f"Slow mode removed from <#{ANNOUNCE_CHANNEL_ID}>.")


# --- Events ---

@bot.event
async def on_member_join(member: discord.Member):
    key = (member.guild.id, member.id)
    now = datetime.now()
    if key in _recent_joins and (now - _recent_joins[key]).total_seconds() < 10:
        return
    _recent_joins[key] = now

    account_age = datetime.now() - member.created_at.replace(tzinfo=None)
    is_new = account_age.days < 30
    fields = [
        ("User", f"{member} (`{member.id}`)", False),
        ("Account Created", f"<t:{int(member.created_at.timestamp())}:R>", True),
        ("Account Age", f"{account_age.days} days old", True),
    ]
    if is_new:
        fields.append(("⚠️ Warning", "Account is less than 30 days old", False))
    title = "⚠️ Suspicious Member Joined" if is_new else "👋 Member Joined"
    color = 0xE74C3C if is_new else 0x2ECC71
    await log(title, color, fields)
    try:
        thumb = THUMBNAIL_URL or bot.user.display_avatar.url
        embed = discord.Embed(
            title=f"Welcome to pympleHUB, {member.name}!",
            description=(
                f"Hey {member.mention}! Thanks for joining.\n\n"
                f"Head over to <#{ANNOUNCE_CHANNEL_ID}> to grab the latest key for our scripts.\n\n"
                f"ALL script-related videos are on my YouTube Channel — please Subscribe, Comment, and Like!\n"
                f"📌 https://www.youtube.com/@scriptsHUB/featured"
            ),
            color=random.choice(COLORS)
        )
        embed.set_thumbnail(url=thumb)
        embed.set_footer(text=f"pympleHUB • {datetime.now().strftime('%d %B %Y')}")
        await member.send(embed=embed)
    except:
        pass

@bot.event
async def on_member_remove(member: discord.Member):
    joined_at = member.joined_at
    if joined_at:
        duration = datetime.now() - joined_at.replace(tzinfo=None)
        days = duration.days
        duration_str = f"{days} day{'s' if days != 1 else ''}" if days > 0 else "Less than a day"
    else:
        duration_str = "Unknown"
    await log("🚪 Member Left", 0x95A5A6, [
        ("User", f"{member} (`{member.id}`)", False),
        ("Time in Server", duration_str, True),
        ("Joined At", f"<t:{int(joined_at.timestamp())}:f>" if joined_at else "Unknown", True),
    ])

@bot.event
async def on_message_delete(message: discord.Message):
    if message.channel.id != ANNOUNCE_CHANNEL_ID or message.author.bot:
        return
    await log("🗑️ Message Deleted", 0xE74C3C, [
        ("Author", f"{message.author} (`{message.author.id}`)", False),
        ("Content", message.content[:900] or "*[no text content]*", False),
    ])

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.channel.id != ANNOUNCE_CHANNEL_ID or before.author.bot:
        return
    if before.content == after.content:
        return
    await log("✏️ Message Edited", 0xF39C12, [
        ("Author", f"{before.author} (`{before.author.id}`)", False),
        ("Before", before.content[:400] or "*[no content]*", False),
        ("After", after.content[:400] or "*[no content]*", False),
    ])

KEY_TRIGGERS = [
    "how to get key", "how do i get", "where is the key", "where's the key",
    "wheres the key", "what is the key", "what's the key", "whats the key",
    "give key", "get key", "key pls", "key please", "how to get a key",
    "where do i get", "how do i get the key", "where can i get",
]

@bot.event
async def on_message(message: discord.Message):
    if message.webhook_id and message.channel.id == LOG_CHANNEL_ID:
        if message.embeds and message.embeds[0].title == "pympleHUB Executed":
            count = await asyncio.to_thread(increment_exec_count)
            await update_exec_channel(count)
        return
    if not message.author.bot:
        content = message.content.lower()
        if any(t in content for t in KEY_TRIGGERS):
            embed = discord.Embed(
                description=f"The current key is available in <#{ANNOUNCE_CHANNEL_ID}>.\nKeys rotate every **6 hours** — make sure you have the latest one before executing.",
                color=0xDC3C3C
            )
            embed.set_footer(text="pympleHUB • Key System")
            await message.reply(embed=embed, delete_after=15, mention_author=False)
    if message.author.bot or message.channel.id != ANNOUNCE_CHANNEL_ID:
        await bot.process_commands(message)
        return
    now = datetime.now()
    recent_key_channel_msgs.append(now)
    cutoff = now - timedelta(seconds=30)
    recent_in_window = [t for t in recent_key_channel_msgs if t > cutoff]
    if len(recent_in_window) >= 5:
        try:
            await message.channel.edit(slowmode_delay=60)
            await log("⚡ Auto Slow-Mode Triggered", 0xE67E22, [
                ("Reason", "5+ messages in 30 seconds", False),
                ("Channel", f"<#{ANNOUNCE_CHANNEL_ID}>", True),
                ("Slow Mode Applied", "60s", True),
            ])
        except:
            pass
    await bot.process_commands(message)

@bot.event
async def on_ready():
    global bot_start_time, THUMBNAIL_URL, last_announce_msg_id
    bot_start_time = datetime.now()
    if not THUMBNAIL_URL:
        THUMBNAIL_URL = await asyncio.to_thread(get_roblox_avatar)
    bot.add_view(CopyKeyView())
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel and not last_announce_msg_id:
        async for m in channel.history(limit=10):
            if m.author == bot.user and m.embeds:
                last_announce_msg_id = m.id
                break
    auto_rotate_key.start()
    clean_key_channel.start()
    missed_rotation_check.start()
    exec_count = await asyncio.to_thread(get_exec_count)
    await update_exec_channel(exec_count)
    await log("✅ Bot Online", 0x2ECC71, [
        ("Bot", str(bot.user), True),
        ("Started At", f"<t:{int(bot_start_time.timestamp())}:F>", True),
    ])
    print(f"Bot is online as {bot.user}")

_flask_app = Flask(__name__)
_wh_rate: dict = {}

@_flask_app.route("/webhook/<secret>", methods=["POST"])
def _proxy_webhook(secret):
    if not WEBHOOK_SECRET or secret != WEBHOOK_SECRET:
        return "", 403
    if not DISCORD_WEBHOOK_URL:
        return "", 500
    ip = flask_req.remote_addr
    now = time.time()
    bucket = [t for t in _wh_rate.get(ip, []) if now - t < 60]
    if len(bucket) >= 20:
        return "", 429
    bucket.append(now)
    _wh_rate[ip] = bucket
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=flask_req.get_json(force=True, silent=True))
        return "", r.status_code
    except:
        return "", 500

def _run_flask():
    port = int(os.environ.get("PORT", 5000))
    _flask_app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

threading.Thread(target=_run_flask, daemon=True).start()

import sys

MAX_RETRIES = 5
for attempt in range(1, MAX_RETRIES + 1):
    try:
        bot.run(DISCORD_TOKEN)
        break
    except discord.errors.HTTPException as e:
        if e.status == 429 and attempt < MAX_RETRIES:
            wait = 60 * attempt
            print(f"[Rate limited on login] Attempt {attempt}/{MAX_RETRIES}. Waiting {wait}s...", flush=True)
            time.sleep(wait)
        else:
            raise
