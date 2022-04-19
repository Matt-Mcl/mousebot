import sys
import time
import asyncio
import json
import aiotfm
import random
import pymongo
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

GREETINGS = ["Welcome Back!"]

# Init Mongo DB
mongo_client = pymongo.MongoClient()
mousebot_db = mongo_client['mousebot']
mousebot_greetings = mousebot_db['greetings']


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


@discord_bot.event
async def on_message(message):
    if message.author == discord_bot.user:
        return
    elif message.channel.id == int(TRIBE_CHAT):
        await tfm_bot.sendTribeMessage(f"[Discord] [{message.author.display_name}] {message.content}")
        if message.content.startswith(PREFIX):
            output = await process_command(message.content, "tribe", message.author.display_name)
            if output is not None:
                await tfm_bot.sendTribeMessage(output)
                await message.channel.send(f"[TFM] [{config['username'].title()}] {output}")
    elif message.channel.id == int(TRIBE_ROOM_CHAT):
        await tfm_bot.sendRoomMessage(f"[Discord] [{message.author.display_name}] {message.content}")
        if message.content.startswith(PREFIX):
            output = await process_command(message.content, "room", message.author.display_name)
            if output is not None:
                await tfm_bot.sendRoomMessage(output)
                await message.channel.send(f"[TFM] [{config['username'].title()}] {output}")




# Transformice Bot

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
    author = message.author.username
    output = await process_command(message.content, "whisper", author)
    if output is not None:
        await message.reply(output)


@tfm_bot.event
async def on_room_message(message):
    author = message.author.username
    if author == config['username']:
        return
    channel = discord_bot.get_channel(int(TRIBE_ROOM_CHAT))
    await channel.send(f"[TFM] [{author}] {message.content}")
    output = await process_command(message.content, "room", author)
    if output is not None:
        await tfm_bot.sendRoomMessage(output)
        await channel.send(f"[TFM] [{config['username'].title()}] {output}")


@tfm_bot.event
async def on_tribe_message(author, message):
    author = author.title()
    if author == config['username']:
        return
    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    await channel.send(f"[TFM] [{author}] {message}")
    output = await process_command(message, "tribe", author)
    if output is not None:
        await tfm_bot.sendTribeMessage(output)
        await channel.send(f"[TFM] [{config['username'].title()}] {output}")


@tfm_bot.event
async def on_member_connected(name):
    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    db_greetings = list(mousebot_greetings.aggregate([
        { "$match": {"name": name.title()} },
        { "$sample": { "size": 1 } }
    ]))
    greeting = random.choice(GREETINGS)
    if len(db_greetings) > 0:
        greeting = db_greetings[0]['greeting']
    
    await channel.send(f"[TFM] {name.title()} has just connected! {greeting}")
    await tfm_bot.sendTribeMessage(greeting)


@tfm_bot.event
async def on_member_disconnected(name):
    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    await channel.send(f"[TFM] {name.title()} has just disconnected!")


@tfm_bot.event
async def on_server_message(message):
    channel = discord_bot.get_channel(int(LOG_CHAT))
    print(f"[SERVER] {message}")
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


async def process_command(message, origin, author):
    output = None

    split_message = message.split(" ")

    # General commands
    if message == f"{PREFIX}help": # .help
        output = f"Commands: .time, .joke"
    elif message == f"{PREFIX}time": # .time
        output = f"{datetime.now()} (UTC)"
    elif message == f"{PREFIX}joke": # .joke
        with open(f"{directory}/jokes.txt", "r") as file:
            jokes = file.read().split("\n")
            output = random.choice(jokes)

    # Admin commands
    if author.title() in CONTROL:
        if message.startswith(f"{PREFIX}greetings"):
            # .greetings add/clear/list <name> <greeting>
            if split_message[1] == "add":
                mousebot_greetings.insert_one({"name": split_message[2].title(), "greeting": " ".join(split_message[3:])})
                output = f"Added greeting to {split_message[2].title()}"
            elif split_message[1] == "clear":
                mousebot_greetings.delete_many({"name": split_message[2].title()})
                output = f"Cleared greetings of {split_message[2].title()}"
            elif split_message[1] == "list":
                greetings_list = [g['greeting'] for g in mousebot_greetings.find({"name": split_message[2].title()}, { "_id": 0, "name": 0})]
                output = f"Greetings for {split_message[2].title()}: {greetings_list}"

    # Room specific commands
    if origin == "room":
        if message == f"{PREFIX}selfie": # .selfie
            await tfm_bot.playEmote(12)

    # Tribe and whisper specific commands
    elif origin == "tribe" or origin == "whisper":
        # .control add/del <username>
        if message.startswith(f"{PREFIX}control"):
            if author in config['CONTROL']:
                newuser = split_message[2]
                if newuser in config['CONTROL']:
                    output = "Cannot modify admin user"
                    return
                elif split_message[1] == "add":
                    CONTROL.append(newuser)
                    output = f"Added {newuser} to control list"
                elif split_message[1] == "del":
                    try:
                        CONTROL.remove(newuser)
                        output = f"Removed {newuser} from control list"
                    except ValueError:
                        output = f"User {newuser} not in control list"

    return output


loop = asyncio.get_event_loop()
loop.create_task(tfm_bot.start())
loop.create_task(discord_bot.run(TOKEN))

loop.run_forever()
