import discord
import requests
import base64
import os
from discord.ext import commands

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = "pympleHUB/obfuscatedPYMPLE"
KEY_FILE = "pympleKeyBot"
ANNOUNCE_CHANNEL_ID = int(os.environ["ANNOUNCE_CHANNEL_ID"])

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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

@bot.command()
async def setkey(ctx, new_key: str):
    if update_key(new_key):
        await ctx.send(f"Key updated to: `{new_key}`")
        channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
        if channel:
            from datetime import datetime
            today = datetime.now().strftime("%B %d, %Y")
            await channel.send(f"{new_key} is the key as of {today}!")
    else:
        await ctx.send("Failed to update key.")

@bot.command()
async def getkey(ctx):
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
    print(f"Bot is online as {bot.user}")

bot.run(DISCORD_TOKEN)
