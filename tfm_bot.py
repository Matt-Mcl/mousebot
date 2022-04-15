import os
import sys
import asyncio
import json
import aiotfm
from datetime import datetime
from discord.ext import commands
from dotenv import load_dotenv

# Discord Bot

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
PREFIX = os.getenv('PREFIX')
TRIBE_CHAT = os.getenv('TRIBE_CHAT')
TRIBE_ROOM_CHAT = os.getenv('TRIBE_ROOM_CHAT')

discord_bot = commands.Bot(command_prefix='.')


@discord_bot.event
async def on_ready():
    for guild in discord_bot.guilds:
        if guild.name == GUILD:
            break

    print(
        f'{discord_bot.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )


@discord_bot.command()
async def test(ctx):
    await ctx.send('test')


@discord_bot.event
async def on_message(message):
    if message.author == discord_bot.user:
        return
    elif message.channel.id == int(TRIBE_CHAT):
        await tfm_bot.sendTribeMessage(f"[Discord] {message.author}: {message.content}")
    elif message.channel.id == int(TRIBE_ROOM_CHAT):
        await tfm_bot.sendRoomMessage(f"[Discord] {message.author}: {message.content}")





# TFM Bot

directory = sys.argv[1]

with open(f"{directory}/config.json") as f:
    config = json.load(f)

tfm_bot = aiotfm.Client(bot_role=True)

boot_time = tfm_bot.loop.time()

PREFIX="."


@tfm_bot.event
async def on_login_ready(*a):
    print('Logging in ...')
    await tfm_bot.login(**config)


@tfm_bot.event
async def on_ready():
    print(f'Connected to the community platform in {tfm_bot.loop.time() - boot_time:.2f} seconds')
    await tfm_bot.enterTribe()
    


@tfm_bot.event
async def on_whisper(message):
    if message.author.username == config['username']:
        return
    if message.content == f"{PREFIX}help":
        await message.reply("Currently I don't do very much but I'm working on it! Commands: .time")
    elif message.content == f"{PREFIX}time":
        await message.reply(f"{datetime.now()} (UTC)")
    else:
        await message.reply(message.content) # echo


@tfm_bot.event
async def on_room_message(message):
    if message.author.username == config['username']:
        return
    channel = discord_bot.get_channel(int(TRIBE_ROOM_CHAT))
    await channel.send(f"[TFM] {message.author.username}: {message.content}")


@tfm_bot.event
async def on_tribe_message(author, message):
    if author == config['username'].lower():
        return
    elif message == f"{PREFIX}help":
        await tfm_bot.sendTribeMessage("Currently I don't do very much but I'm working on it! Commands: .time")
    elif message == f"{PREFIX}time":
        await tfm_bot.sendTribeMessage(f"{datetime.now()} (UTC)")
    else:
        channel = discord_bot.get_channel(int(TRIBE_CHAT))
        await channel.send(f"[TFM] {author.title()}: {message}")


@tfm_bot.event
async def on_joined_room(room):
    print('Joined room:', room)


loop = asyncio.get_event_loop()
loop.create_task(tfm_bot.start())
loop.create_task(discord_bot.run(TOKEN))

loop.run_forever()
