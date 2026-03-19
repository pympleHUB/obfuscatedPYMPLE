import discord
import requests
import base64
import os
import random
import string
from datetime import datetime, timedelta
from discord.ext import commands, tasks

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = "pympleHUB/obfuscatedPYMPLE"
KEY_FILE = "pympleKeyBot"
ANNOUNCE_CHANNEL_ID = int(os.environ["ANNOUNCE_CHANNEL_ID"])

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

last_announce_msg_id = None

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

def generate_key():
    return "PYMPLE-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_file_sha():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{KEY_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()["sha"]
    return None

def update_key(new_key):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{KEY_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    sha = get_file_sha()
    content = base64.b64encode(new_key.encode()).decode()
    data = {"message": "Update key", "content": content}
    if sha:
        data["sha"] = sha
    r = requests.put(url, json=data, headers=headers)
    return r.status_code in (200, 201)

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

    desc = f"# `{new_key}`\n\n"
    if expires_at:
        ts = int(expires_at.timestamp())
        desc += f"Key will be resetting <t:{ts}:R>! Please check out <#1183563684828688446> for all of my projects!\n\nALL script-related videos are found on my YouTube Channel, linked below! Please Subscribe, Comment, and Like;\n📌 https://www.youtube.com/@scriptsHUB/featured"
    else:
        desc += "Key will be resetting soon! Please check out <#1183563684828688446> for all of my projects!\n\nALL script-related videos are found on my YouTube Channel, linked below! Please Subscribe, Comment, and Like;\n📌 https://www.youtube.com/@scriptsHUB/featured"

    today = datetime.now().strftime("%d %B %Y")
    embed = discord.Embed(title=greeting, description=desc, color=color)
    embed.set_footer(text=f"pympleHUB • {today}")

    msg = await channel.send(embed=embed)
    last_announce_msg_id = msg.id

@tasks.loop(hours=12)
async def auto_rotate_key():
    if auto_rotate_key.current_loop == 0:
        return
    new_key = generate_key()
    if update_key(new_key):
        await announce_key(new_key, expires_at=datetime.now() + timedelta(hours=12))

OWNER_ID = 431103247478947850

@bot.command()
async def setkey(ctx, new_key: str):
    if ctx.author.id != OWNER_ID:
        return
    try:
        await ctx.message.delete()
    except:
        pass
    if update_key(new_key):
        auto_rotate_key.restart()
        await announce_key(new_key, expires_at=datetime.now() + timedelta(hours=12))
    else:
        try:
            await ctx.author.send(f"Failed to update key to `{new_key}`.")
        except:
            pass

@bot.command()
async def getkey(ctx):
    if ctx.author.id != OWNER_ID:
        return
    try:
        await ctx.message.delete()
    except:
        pass
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{KEY_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        key = base64.b64decode(r.json()["content"]).decode().strip()
        await ctx.author.send(f"Current key: `{key}`")
    else:
        await ctx.author.send("No key set yet.")

@bot.event
async def on_ready():
    auto_rotate_key.start()
    print(f"Bot is online as {bot.user}")

bot.run(DISCORD_TOKEN)
