import subprocess
import sys
import time
import asyncio
import json
import aiotfm
import random
import pymongo
from datetime import datetime
from discord.ext import commands

# Environment Variables
directory = sys.argv[1]

with open(f"{directory}/config.json") as f:
    config = json.load(f)

TOKEN = config['DISCORD_TOKEN']
GUILD = config['DISCORD_GUILD']
PREFIX = config['PREFIX']
TRIBE_CHAT = config['TRIBE_CHAT']
TRIBE_ROOM_CHAT = config['TRIBE_ROOM_CHAT']
LOG_CHAT = config['LOG_CHAT']
OWNER = config['OWNER']
CONTROL = config['CONTROL'][:]

GREETINGS = ["Howdy, partner!", "Hey, howdy, hi!", "Put that Coffee Cup down!", "Ahoy, matey!", "Hiya! Welcome back!", "This Message may be recorded for training purposes- I.. I mean Welcome back!", "Yo!", "What's up?", "Sup?", "Take a deep breath in.. Namaste! SHIT I DIDN'T NOTICE YOU THERE!! I mean.. Welcome back, creep!", "New phone, who dis?"]


# Init Mongo DB
mongo_client = pymongo.MongoClient()
mousebot_db = mongo_client['mousebot']
mousebot_greetings = mousebot_db['greetings']
mousebot_titles = mousebot_db['titles']


#######################################################################################################################
################################################## TRANSFORMICE BOT ###################################################
#######################################################################################################################

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
    output = await process_command(message.content, "whisper", message.author)
    if output is not None:
        await message.reply(output)
        print(f"[Whisper] [{author}] {output}")


@tfm_bot.event
async def on_room_message(message):
    author = message.author.username
    if author == config['username']:
        return
    channel = discord_bot.get_channel(int(TRIBE_ROOM_CHAT))
    await send_discord_message(channel, f"[TFM] [{author}] {message.content}")
    output = await process_command(message.content, "room", message.author)
    if output is not None:
        await send_room_message(output)
        await send_discord_message(channel, f"[TFM] [{config['username'].title()}] {output}")


@tfm_bot.event
async def on_tribe_message(author, message):
    author = author.title()
    if author == config['username']:
        return
    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    await send_discord_message(channel, f"[TFM] [{author}] {message}")
    output = await process_command(message, "tribe", author)
    if output is not None:
        await send_tribe_message(output)
        await send_discord_message(channel, f"[TFM] [{config['username'].title()}] {output}")


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
    
    await send_discord_message(channel, f"[TFM] {name.title()} has just connected! {greeting}")
    await send_tribe_message(greeting)


@tfm_bot.event
async def on_member_disconnected(name):
    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    await send_discord_message(channel, f"[TFM] {name.title()} has just disconnected!")


@tfm_bot.event
async def on_server_message(message):
    channel = discord_bot.get_channel(int(LOG_CHAT))
    print(f"[SERVER] {message}")
    await send_discord_message(channel, f"[SERVER] {message}")


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


async def process_command(message, origin, author, discord=False):
    author_name = author

    if origin != "tribe" and not discord:
        author_name = author.username

    split_message = message.split(" ")

    # General commands
    if message == f"{PREFIX}help": # .help
        return f"Commands: .time, .joke, .titles"
    elif message == f"{PREFIX}time": # .time
        return f"{datetime.now()} (UTC)"
    elif message == f"{PREFIX}joke": # .joke
        with open(f"{directory}/jokes.txt", "r") as file:
            jokes = file.read().split("\n")
            return random.choice(jokes)
    elif message == f"{PREFIX}titles": # .titles
        pass
        # print(author.profile.stats)
        # cheese_totals = mousebot_titles.find({"type": "cheese_total"}, { "_id": 0, "type": 0})
        # for item in cheese_totals:
        #     if item['number'] > 0:
        #         pass ## FINISH ##
    

    # Admin commands
    if author_name.title() in CONTROL:
        if message.startswith(f"{PREFIX}greetings"):
            # .greetings add/clear/list <name> <greeting>
            if split_message[1] == "add":
                mousebot_greetings.insert_one({"name": split_message[2].title(), "greeting": " ".join(split_message[3:])})
                return f"Added greeting to {split_message[2].title()}"
            elif split_message[1] == "clear":
                mousebot_greetings.delete_many({"name": split_message[2].title()})
                return f"Cleared greetings of {split_message[2].title()}"
            elif split_message[1] == "list":
                greetings_list = [g['greeting'] for g in mousebot_greetings.find({"name": split_message[2].title()}, { "_id": 0, "name": 0})]
                return f"Greetings for {split_message[2].title()}: {greetings_list}"
        elif message.startswith(f"{PREFIX}control"):
            # .control add/del <username>
            newuser = split_message[2]
            if newuser in config['CONTROL']:
                return "Cannot modify admin user"
            elif split_message[1] == "add":
                CONTROL.append(newuser)
                return f"Added {newuser} to control list"
            elif split_message[1] == "del":
                try:
                    CONTROL.remove(newuser)
                    return f"Removed {newuser} from control list"
                except ValueError:
                    return f"User {newuser} not in control list"

    # Owner Commands
    if author_name.title() in OWNER:
        if message.startswith(f"{PREFIX}exec"): # .exec <command>
            return subprocess.check_output(split_message[1:]).decode("utf-8").strip()
        elif message == f"{PREFIX}restart":
            subprocess.check_output(["sudo", "systemctl", "reset-failed", "mousebot.service"])
            return subprocess.check_output(["sudo", "systemctl", "restart", "mousebot.service"]).decode("utf-8").strip()
        elif message == f"{PREFIX}status":
            status = subprocess.Popen(["systemctl", "status", "mousebot.service"], stdout=subprocess.PIPE)
            output = subprocess.check_output(["grep", "active"], stdin=status.stdout).decode("utf-8").rsplit(" ", 3)[0].strip()
            return output

    # Room specific commands
    if origin == "room":
        if message == f"{PREFIX}selfie": # .selfie
            await tfm_bot.playEmote(12)

#######################################################################################################################
################################################## TRANSFORMICE BOT ###################################################
#######################################################################################################################


#######################################################################################################################
##################################################### DISCORD BOT #####################################################
#######################################################################################################################

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
        await send_tribe_message(f"[Discord] [{message.author.display_name}] {message.content}")
        if message.content.startswith(PREFIX):
            output = await process_command(message.content, "tribe", f"{message.author.id}", True)
            if output is not None:
                await send_tribe_message(output)
                await send_discord_message(message.channel, f"[TFM] [{config['username'].title()}] {output}")
    elif message.channel.id == int(TRIBE_ROOM_CHAT):
        await send_room_message(f"[Discord] [{message.author.display_name}] {message.content}")
        if message.content.startswith(PREFIX):
            output = await process_command(message.content, "room", f"{message.author.id}", True)
            if output is not None:
                await send_room_message(output)
                await send_discord_message(message.channel, f"[TFM] [{config['username'].title()}] {output}")

#######################################################################################################################
##################################################### DISCORD BOT #####################################################
#######################################################################################################################


# Helper functions
async def send_tribe_message(message):
    await tfm_bot.sendTribeMessage(message)
    print(f"[tribe-chat] {message}")


async def send_room_message(message):
    await tfm_bot.sendRoomMessage(message)
    print(f"[tribe-room-chat] {message}")


async def send_discord_message(channel, message):
    await channel.send(message)
    print(f"[{channel}] {message}")


# Main bot loops
loop = asyncio.get_event_loop()
loop.create_task(tfm_bot.start())
loop.create_task(discord_bot.run(TOKEN))

loop.run_forever()
