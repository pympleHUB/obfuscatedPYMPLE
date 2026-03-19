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
    if not last_announce_msg_id:
        return
    try:
        channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
        old_msg = await channel.fetch_message(last_announce_msg_id)
        old_embed = old_msg.embeds[0]
        expired = discord.Embed(
            title=old_embed.title,
            description=old_embed.description.split("\n\n")[0] + "\n\n~~This key has been rotated.~~",
            color=0x555555,
        )
        expired.set_footer(text=old_embed.footer.text + " • Expired")
        await old_msg.edit(embed=expired)
    except:
        pass

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
        desc += f"Key will be resetting <t:{ts}:R>! Please check out <#1183563684828688446> for all of my projects!"
    else:
        desc += "Key will be resetting soon! Please check out <#1183563684828688446> for all of my projects!"

    today = datetime.now().strftime("%d %B %Y")
    embed = discord.Embed(title=greeting, description=desc, color=color)
    embed.set_footer(text=f"PYMPLE • {today}")

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
    if update_key(new_key):
        auto_rotate_key.restart()
        await ctx.send(f"Key updated to: `{new_key}`")
        await announce_key(new_key, expires_at=datetime.now() + timedelta(hours=12))
    else:
        await ctx.send("Failed to update key.")

@bot.command()
async def getkey(ctx):
    if ctx.author.id != OWNER_ID:
        return
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{KEY_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        key = base64.b64decode(r.json()["content"]).decode().strip()
        await ctx.send(f"Current key: `{key}`")
    else:
        await ctx.send("No key set yet.")

@bot.event
async def on_ready():
    auto_rotate_key.start()
    print(f"Bot is online as {bot.user}")

bot.run(DISCORD_TOKEN)
