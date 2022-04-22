import subprocess
import sys
import time
import asyncio
import json
import aiotfm
import random
import pymongo
import requests
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
EIGHT_BALL = ["It is certain.", "It is decidedly so.", "Without a doubt.", "Yes definitely.", "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.", "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."]

# Init Mongo DB
mongo_client = pymongo.MongoClient()
mousebot_db = mongo_client['mousebot']
mousebot_greetings = mousebot_db['greetings']
mousebot_titles = mousebot_db['titles']
db_titles = list(mousebot_titles.find())


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
        for item in output:
            await message.reply(item)
            print(f"[Whisper] [{author}] {item}")


@tfm_bot.event
async def on_room_message(message):
    author = message.author.username
    # Check if message send by bot
    if author == config['username']:
        return
    # Check if message send by tribe member
    try:
        tribe = await tfm_bot.getTribe()
    except:
        return
    member_names = [member.name.title() for member in tribe.members]
    if author not in member_names:
        return
    channel = discord_bot.get_channel(int(TRIBE_ROOM_CHAT))
    await send_discord_message(channel, f"[TFM] [{author}] {message.content}")
    output = await process_command(message.content, "room", message.author)
    if output is not None:
        for item in output:
            await send_room_message(item)
            await send_discord_message(channel, f"[TFM] [{config['username'].title()}] {item}")


@tfm_bot.event
async def on_tribe_message(author, message):
    author = author.title()
    # Check if message send by bot
    if author == config['username']:
        return
    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    await send_discord_message(channel, f"[TFM] [{author}] {message}")
    output = await process_command(message, "tribe", author)
    if output is not None:
        for item in output:
            await send_tribe_message(item)
            await send_discord_message(channel, f"[TFM] [{config['username'].title()}] {item}")


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
    
    await send_discord_message(channel, f"[TFM] {name.title()} has connected! {greeting}")
    await send_tribe_message(greeting)


@tfm_bot.event
async def on_member_disconnected(name):
    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    await send_discord_message(channel, f"[TFM] {name.title()} has disconnected.")


# @tfm_bot.event
# async def on_server_message(message):
#     channel = discord_bot.get_channel(int(LOG_CHAT))
#     print(f"[SERVER] {message}")
#     await send_discord_message(channel, f"[SERVER] {message}")


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


# @tfm_bot.event
# async def on_raw_socket(connection, packet):
#     CCC = packet.readCode()
#     exclude = [(4, 3), (4, 4), (60, 3), (28, 6)]
#     if CCC not in exclude:
#         print(packet, CCC)


@tfm_bot.event
async def on_player_won(player, order, player_time):
    username = player.username.title()
    try:
        tribe = await tfm_bot.getTribe()
    except:
        return
    member_names = [member.name.title() for member in tribe.members]
    if username not in member_names:
        return
    if order == 1:
        await tfm_bot.sendCommand(f"profile {username}")
        profile = await tfm_bot.wait_for('on_profile', lambda p: p.username == username, timeout=3)
        firsts = profile.stats.firsts
        title = ""
        for item in db_titles:
            if item['type'] == "cheese_first" and item['number'] > firsts:
                title = f" You need {item['number'] - firsts} more firsts for «{'/'.join(item['titles'])}»"
                break

        print(f"[Whisper] {username}, You came first in {player_time} seconds.{title}")
        await tfm_bot.whisper(username, f"You came in first in {player_time} seconds.{title}")


async def process_command(message, origin, author, discord=False):
    author_name = author

    if origin != "tribe" and not discord:
        author_name = author.username

    split_message = message.split(" ")

    # General commands
    if message == f"{PREFIX}help": # .help
        return [f"I'm a bot for the tribe Coffee Corner! Commands: .time, .mom, .joke, .title [player#tag], .online, .8ball <message>"]

    elif message == f"{PREFIX}time": # .time
        await tfm_bot.sendCommand("time")
        time = await tfm_bot.wait_for('on_time', timeout=3)
        return [time]

    elif message == f"{PREFIX}mom": # .mom
        with open(f"{directory}/jokes.txt", "r") as file:
            jokes = file.read().split("\n")
            return [random.choice(jokes)]

    elif message == f"{PREFIX}joke": # .joke
        choice = random.randint(1, 2)
        if choice == 1:
            json = requests.get("https://v2.jokeapi.dev/joke/Miscellaneous,Dark,Pun,Spooky,Christmas?blacklistFlags=racist").json()
            if json['type'] == "twopart":
                return [f"{json['setup']} {json['delivery']}"]
            else:
                return [json['joke']]
        elif choice == 2:
            json = requests.get("https://icanhazdadjoke.com", headers={"Accept": "application/json"}).json()
            return [json['joke']]

    elif message.startswith(f"{PREFIX}title"): # .title <player>
        offline = ""
        if len(split_message) > 1:
            author_name = split_message[1]
        await tfm_bot.sendCommand(f"profile {author_name}")
        try:
            profile = await tfm_bot.wait_for('on_profile', lambda p: p.username == author_name.title(), timeout=3)
            cheese = profile.stats.gatheredCheese
            firsts = profile.stats.firsts
            bootcamps = profile.stats.bootcamps
            normalModeSaves = profile.stats.normalModeSaves
            hardModeSaves = profile.stats.hardModeSaves
            divineModeSaves = profile.stats.divineModeSaves
            withoutSkillSaves = profile.stats.withoutSkillSaves
        except asyncio.exceptions.TimeoutError:
            json = requests.get(f"https://cheese.formice.com/api/players/{author_name.title().replace('#', '-')}").json()
            if "error" in json:
                return [json['message']]
            cheese = json['stats']['mouse']['cheese']
            firsts = json['stats']['mouse']['first']
            bootcamps = json['stats']['mouse']['bootcamp']
            normalModeSaves = json['stats']['shaman']['saves_normal']
            hardModeSaves = json['stats']['shaman']['saves_hard']
            divineModeSaves = json['stats']['shaman']['saves_divine']
            offline = "(Offline) "
        except:
            pass

        main_titles = {"cheese_title": "", "first_title": "", "bootcamp_title": ""}
        shaman_titles = {"normal_title": "", "hard_title": "", "divine_title": "", "without_title": ""}

        for item in db_titles:
            if item['type'] == "cheese_total" and item['number'] > cheese and len(main_titles['cheese_title']) == 0:
                main_titles['cheese_title'] = f"{item['number'] - cheese} cheese for «{'/'.join(item['titles'])}»"
            elif item['type'] == "cheese_first" and item['number'] > firsts and len(main_titles['first_title']) == 0:
                main_titles['first_title'] = f"{item['number'] - firsts} firsts for «{'/'.join(item['titles'])}»"
            elif item['type'] == "bootcamp" and item['number'] > bootcamps and len(main_titles['bootcamp_title']) == 0:
                main_titles['bootcamp_title'] = f"{item['number'] - bootcamps} bootcamps for «{'/'.join(item['titles'])}»"
            elif item['type'] == "normal_saves" and item['number'] > normalModeSaves and len(shaman_titles['normal_title']) == 0:
                shaman_titles['normal_title'] = f"{item['number'] - normalModeSaves} saves for «{'/'.join(item['titles'])}»"
            elif item['type'] == "hard_saves" and item['number'] > hardModeSaves and len(shaman_titles['hard_title']) == 0:
                shaman_titles['hard_title'] = f"{item['number'] - hardModeSaves} hard saves for «{'/'.join(item['titles'])}»"
            elif item['type'] == "divine_saves" and item['number'] > divineModeSaves and len(shaman_titles['divine_title']) == 0:
                shaman_titles['divine_title'] = f"{item['number'] - divineModeSaves} divine saves for «{'/'.join(item['titles'])}»"
            if offline == "":
                if item['type'] == "without_skill_saves" and item['number'] > withoutSkillSaves and len(shaman_titles['without_title']) == 0:
                    shaman_titles['without_title'] = f"{item['number'] - withoutSkillSaves} w/o skills for «{'/'.join(item['titles'])}»"
        
        # Remove Blanks
        main_titles = {k: v for k, v in main_titles.items() if v}
        shaman_titles = {k: v for k, v in shaman_titles.items() if v}

        title_items = []

        if len(main_titles) > 0:
            title_items.append(f"{offline}{author_name.title()}, {', '.join(list(main_titles.values()))}")
        if len(shaman_titles) > 0:
            title_items.append(f"{offline}{author_name.title()}, {', '.join(list(shaman_titles.values()))}")

        return title_items
    elif message == f"{PREFIX}online": # .online
        tribe = await tfm_bot.getTribe()
        members = tribe.members
        online = []
        for member in members:
            if member.online and member.name.title() != config['username']:
                online.append(member.name.title())
        if len(online) > 0:
            return [f"Online Players: {', '.join(online)}"]
        else:
            return ["No one is online."]
    elif message == f"{PREFIX}sales": # .sales
        await tfm_bot.requestShopList()
        # datas = [
        #     b'\x01\x01\x00\x03\x82\xd4\x01bb\x1a\x002', 
        #     b"\x01\x01\x00\x00'\xd4\x01bb\x1a\x00#",
        #     b'\x01\x01\x00\x00\x02\xeb\x01bb\x1a\x00(',
        #     b'\x01\x00\x00\x00\x00t\x01bb\x1a\x00\x1e',
        #     b'\x01\x00\x00\x00\x00\xdb\x01bb\x1a\x00#'
        # ]
        # await tfm_bot.requestShopList()
        # shop = await tfm_bot.wait_for('on_shop', timeout=10)

        # for data in datas:
        #     print('-----------------')
        #     packet = aiotfm.Packet.new(20, 3).writeBytes(data)

        #     packet.readCode()

        #     print(packet.readBool())
        #     print(packet.readBool())
        #     id = packet.read32()
        #     print(id)
        #     print(packet.readBool())
        #     print(packet.read32() * 1000)
        #     discount = packet.read8()
        #     print(discount)

        #     for item in shop.items:
        #         # print(item.uid)
        #         if int(item.uid) == int(id):
        #             print('FOUND1')
        #             print(item.cheese, item.fraise, item.fraise * (1 - (discount / 100)))

        #     for item in shop.shaman_objects:
        #         # print(item.uid)
        #         if int(item.id) == int(id):
        #             print('FOUND2')
        #             print(item.cheese, item.fraise, item.fraise * (1 - (discount / 100)))

        #     print('-----------------')

        # print(shop)
        # _, shop_packet = await tfm_bot.wait_for('on_raw_socket', lambda _, p: p.readCode() == (20, 3), timeout=30)
        # print(shop_packet)
        # for item in shop.items:
        #     if item.is_new:
        #         print(item.id, item.category, item.cheese, item.fraise, item.special)
        #     if item.fraise == 65:
        #         print(item.id, item.category, item.cheese, item.fraise, item.special)
        #     print(item.id, item.category, item.cheese, item.fraise, item.special)
        # print("done")
    elif message.startswith(f"{PREFIX}8ball"):
        if len(split_message) == 1:
            return ["Please ask a question."]
        return [random.choice(EIGHT_BALL)]
    elif message == f"{PREFIX}ping":
        await tfm_bot.sendCommand("ping")
        # ping = await tfm_bot.wait_for('on_ping', timeout=10)
        # print(ping)
        # return ping
    
    elif message in [f"{PREFIX}funcorp", f"{PREFIX}fc"]: # .funcorp            
        with open(f"{directory}/Funcorp_Lua.lua", 'r') as f:
            code = f.read()
            code = f"admin = {{\"{author_name.title()}\"}}\n" + code
            await tfm_bot.loadLua(code)


    # Admin commands
    if author_name.title() in CONTROL:
        if message.startswith(f"{PREFIX}greetings"):
            # .greetings add/clear/list <name> <greeting>
            if split_message[1] == "add":
                mousebot_greetings.insert_one({"name": split_message[2].title(), "greeting": " ".join(split_message[3:])})
                return [f"Added greeting to {split_message[2].title()}"]
            elif split_message[1] == "clear":
                mousebot_greetings.delete_many({"name": split_message[2].title()})
                return [f"Cleared greetings of {split_message[2].title()}"]
            elif split_message[1] == "list":
                greetings_list = [g['greeting'] for g in mousebot_greetings.find({"name": split_message[2].title()}, { "_id": 0, "name": 0})]
                return [f"Greetings for {split_message[2].title()}: {greetings_list}"]

        elif message.startswith(f"{PREFIX}control"):
            # .control add/del <username>
            newuser = split_message[2]
            if newuser in config['CONTROL']:
                return ["Cannot modify admin user"]
            elif split_message[1] == "add":
                CONTROL.append(newuser)
                return [f"Added {newuser} to control list"]
            elif split_message[1] == "del":
                try:
                    CONTROL.remove(newuser)
                    return [f"Removed {newuser} from control list"]
                except ValueError:
                    return [f"User {newuser} not in control list"]

        elif message == f"{PREFIX}tribe": # .tribe
            await tfm_bot.enterTribe()

        elif message.startswith(f"{PREFIX}room"): # .room <room> [password]
            await tfm_bot.joinRoom(" ".join(split_message[1:]))

        elif message.startswith(f"{PREFIX}lua"): # .lua <pastebin>
            if len(split_message) == 1:
                return ["Please add pastebin URL"]
            url = "https://pastebin.com/raw/" + split_message[1].split('/')[3]
            code = requests.get(url)
            if code.status_code != 200:
                return ["Invalid pastebin URL"]

            await tfm_bot.loadLua(code.text)


    # Owner Commands
    if author_name.title() in OWNER:
        if message.startswith(f"{PREFIX}exec"): # .exec <command>
            return [subprocess.check_output(split_message[1:]).decode("utf-8").strip()]

        elif message == f"{PREFIX}restart": # .restart
            subprocess.run(["sudo", "systemctl", "reset-failed", "mousebot.service"])
            subprocess.run(["sudo", "systemctl", "restart", "mousebot.service"])

        elif message == f"{PREFIX}status": # .status
            status = subprocess.Popen(["systemctl", "status", "mousebot.service"], stdout=subprocess.PIPE)
            output = subprocess.check_output(["grep", "active"], stdin=status.stdout).decode("utf-8").rsplit(" ", 3)[0].strip()
            return [output]

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
                for item in output:
                    await send_tribe_message(item)
                    await send_discord_message(message.channel, f"[TFM] [{config['username'].title()}] {item}")
    elif message.channel.id == int(TRIBE_ROOM_CHAT):
        is_tribe = tfm_bot.room.is_tribe
        if is_tribe:
            await send_room_message(f"[Discord] [{message.author.display_name}] {message.content}")
        if message.content.startswith(PREFIX):
            output = await process_command(message.content, "room", f"{message.author.id}", True)
            if output is not None:
                for item in output:
                    if is_tribe:
                        await send_room_message(item)
                    await send_discord_message(message.channel, f"[TFM] [{config['username'].title()}] {item}")
        elif not is_tribe:
            return await send_discord_message(message.channel, "Not in tribe house. Please use tribe-chat instead for non commands.")

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
