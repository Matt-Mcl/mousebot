import sys
import time
import asyncio
import json
import aiotfm
import random
from datetime import datetime
from discord.ext import commands

# Discord Bot

directory = sys.argv[1]

with open(f"{directory}/config.json") as f:
    config = json.load(f)

TOKEN = config['DISCORD_TOKEN']
GUILD = config['DISCORD_GUILD']
PREFIX = config['PREFIX']
TRIBE_CHAT = config['TRIBE_CHAT']
TRIBE_ROOM_CHAT = config['TRIBE_ROOM_CHAT']
LOG_CHAT = config['LOG_CHAT']
CONTROL = config['CONTROL'][:]

GREETINGS = ["Welcome Back!", "Hope you're having a great day!"]


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
        await tfm_bot.sendTribeMessage(f"[Discord] {message.author.display_name}: {message.content}")
    elif message.channel.id == int(TRIBE_ROOM_CHAT):
        await tfm_bot.sendRoomMessage(f"[Discord] {message.author.display_name}: {message.content}")





# TFM Bot

tfm_bot = aiotfm.Client(bot_role=True)

boot_time = tfm_bot.loop.time()

PREFIX="."


@tfm_bot.event
async def on_login_ready(*a):
    print('Logging in ...')
    await tfm_bot.login(config['username'], config['password'], config['encrypted'], config['room'])


@tfm_bot.event
async def on_ready():
    print(f'Connected to the community platform in {tfm_bot.loop.time() - boot_time:.2f} seconds')
    time.sleep(1)
    await tfm_bot.enterTribe()
    


@tfm_bot.event
async def on_whisper(message):
    if message.author.username == config['username']:
        return
    if message.content == f"{PREFIX}help":
        await message.reply("Currently I don't do very much but I'm working on it! Commands: .time")
    elif message.content == f"{PREFIX}time":
        await message.reply(f"{datetime.now()} (UTC)")
    elif message.content == f"{PREFIX}tribe":
        await tfm_bot.enterTribe()
    elif message.content == f"{PREFIX}joke":
        with open(f"{directory}/jokes.txt", "r") as file:
            jokes = file.read().split("\n")
            await tfm_bot.sendRoomMessage(random.choice(jokes))
    else:
        await message.reply(message.content) # echo


@tfm_bot.event
async def on_room_message(message):
    split = message.content.split(" ")
    if message.author.username == config['username']:
        return
    elif message.content.startswith(f"{PREFIX}control"):
        if message.author.username in config['CONTROL']:
            newuser = split[2]
            if newuser in config['CONTROL']:
                await tfm_bot.sendRoomMessage("Cannot modify admin user")
                return
            elif split[1] == "add":
                CONTROL.append(newuser)
                await tfm_bot.sendRoomMessage(f"Added {newuser} to control list")
            elif split[1] == "del":
                try:
                    CONTROL.remove(newuser)
                    await tfm_bot.sendRoomMessage(f"Removed {newuser} from control list")
                except ValueError:
                    await tfm_bot.sendRoomMessage(f"User {newuser} not in control list")
    elif message.content.startswith(f"{PREFIX}selfie"):
        await tfm_bot.playEmote(12)
    elif message.content == f"{PREFIX}joke":
        with open(f"{directory}/jokes.txt", "r") as file:
            jokes = file.read().split("\n")
            await tfm_bot.sendRoomMessage(random.choice(jokes))
    else:
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
    elif message == f"{PREFIX}joke":
        with open(f"{directory}/jokes.txt", "r") as file:
            jokes = file.read().split("\n")
            await tfm_bot.sendTribeMessage(random.choice(jokes))
    else:
        channel = discord_bot.get_channel(int(TRIBE_CHAT))
        await channel.send(f"[TFM] {author.title()}: {message}")


@tfm_bot.event
async def on_member_connected(name):
    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    greeting = random.choice(GREETINGS)
    if name == "tosis#5187":
        greeting = "Can you smell that? Oh, it's just Tosis!"
    
    await channel.send(f"[TFM] {name.title()} has just connected! {greeting}")
    await tfm_bot.sendTribeMessage(greeting)


@tfm_bot.event
async def on_member_disconnected(name):
    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    await channel.send(f"[TFM] {name.title()} has just disconnected!")


@tfm_bot.event
async def on_server_message(message):
    channel = discord_bot.get_channel(int(LOG_CHAT))
    await channel.send(f"[SERVER] {message}")


@tfm_bot.event
async def on_emoji(player, emoji):
    if player.username == config['username']:
        return
    if player.username in CONTROL:
        await tfm_bot.sendSmiley(emoji)


# @tfm_bot.event
# async def on_emote(player, emote, flag):
#     if player.username == config['username']:
#         return
#     if player.username in CONTROL:
#         await tfm_bot.playEmote(emote)


@tfm_bot.event
async def on_joined_room(room):
    print('Joined room:', room)


loop = asyncio.get_event_loop()
loop.create_task(tfm_bot.start())
loop.create_task(discord_bot.run(TOKEN))

loop.run_forever()
