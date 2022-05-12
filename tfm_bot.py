import re
import subprocess
import sys
import time
import asyncio
import json
import aiotfm
import random
import pymongo
import requests
from gazpacho import get, Soup
from gazpacho.utils import HTTPError
from math import ceil
from datetime import datetime, timedelta
from discord import Embed
from discord.ext import commands

# Environment Variables
directory = sys.argv[1]

with open(f"{directory}/config/config.json") as f:
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
RECENT_MAPS = []
TRIBE = []
SHOP = []
JOKES = []

with open("/home/ubuntu/mousebot/statics/jokes.json") as f:
    jokes_file = json.load(f)

for key in jokes_file:
    for joke in jokes_file[key]:
        JOKES.append(joke)

del jokes_file

# Init Mongo DB
mongo_client = pymongo.MongoClient()
mousebot_db = mongo_client['mousebot']
mousebot_greetings = mousebot_db['greetings']
mousebot_titles = mousebot_db['titles']
db_titles = list(mousebot_titles.find())
mousebot_maps = mousebot_db['maps']
mousebot_maps.create_index("code", unique=True)
mousebot_map_records = mousebot_db['map_records']
mousebot_enums = mousebot_db['enums']
mousebot_stats = mousebot_db['player_stats']
mousebot_sales = mousebot_db['sales']
mousebot_sales.create_index(([("id", pymongo.ASCENDING), ("category", pymongo.ASCENDING), ("is_shaman", pymongo.ASCENDING)]), unique=True)
mousebot_shop_items = mousebot_db['shop_items']


#######################################################################################################################
################################################## TRANSFORMICE BOT ###################################################
#######################################################################################################################

tfm_bot = aiotfm.Client(bot_role=True)

boot_time = tfm_bot.loop.time()

PREFIX="."


@tfm_bot.event
async def on_login_ready(*a):
    log_message('Logging in..')
    await tfm_bot.login(config['username'], config['password'], config['encrypted'], config['room'])
    log_message('Logging in.. Done')


@tfm_bot.event
async def on_ready():
    log_message(f'Connected to the community platform in {tfm_bot.loop.time() - boot_time:.2f} seconds')

    time.sleep(1)
    last_room = mousebot_enums.find_one({"type": "room"})['data']
    if last_room['is_tribe']:
        await tfm_bot.enterTribe()
    else:
        await tfm_bot.joinRoom(last_room['name'])

    log_message("Getting Tribe data..")
    TRIBE.append(await tfm_bot.getTribe())
    log_message("Getting Tribe data.. Done")

    await get_stats()

    log_message("Getting Shop data..")
    await tfm_bot.requestShopList()
    SHOP.append(await tfm_bot.wait_for('on_shop', timeout=60))
    log_message("Getting Shop data.. Done")


@tfm_bot.event
async def on_whisper(message):
    author = message.author.username
    output = await process_command(message.content, "whisper", message.author)
    if output is not None:
        for item in output:
            await message.reply(item)
            log_message(f"[Whisper] [{author}] {item}")


@tfm_bot.event
async def on_room_message(message):
    author = message.author.username
    # Check if message send by bot
    if author == config['username']:
        return
    member_names = [member.name.capitalize() for member in TRIBE[0].members]
    if author not in member_names:
        return
    channel = discord_bot.get_channel(int(TRIBE_ROOM_CHAT))
    await send_discord_message(channel, f"[TFM] [{author}] {message.content}")
    output = await process_command(message.content, "room", message.author)
    if output is not None:
        for item in output:
            await send_room_message(item)
            await send_discord_message(channel, f"[TFM] [{config['username'].capitalize()}] {item}")


@tfm_bot.event
async def on_tribe_message(author, message):
    author = author.capitalize()
    # Check if message send by bot
    if author == config['username']:
        return
    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    await send_discord_message(channel, f"[TFM] [{author}] {message}")
    output = await process_command(message, "tribe", author)
    if output is not None:
        for item in output:
            await send_tribe_message(item)
            await send_discord_message(channel, f"[TFM] [{config['username'].capitalize()}] {item}")


@tfm_bot.event
async def on_member_connected(name):
    await update_tribe()

    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    db_greetings = list(mousebot_greetings.aggregate([
        { "$match": {"name": name.capitalize()} },
        { "$sample": { "size": 1 } }
    ]))
    greeting = random.choice(GREETINGS)
    if len(db_greetings) > 0:
        greeting = db_greetings[0]['greeting']
    
    await send_discord_message(channel, f"[TFM] {name.capitalize()} has connected! {greeting}")
    await send_tribe_message(greeting)

    await get_stats()


@tfm_bot.event
async def on_member_disconnected(name):
    await update_tribe()

    channel = discord_bot.get_channel(int(TRIBE_CHAT))
    await send_discord_message(channel, f"[TFM] {name.capitalize()} has disconnected.")


# @tfm_bot.event
# async def on_server_message(message):
#     channel = discord_bot.get_channel(int(LOG_CHAT))
#     log_message(f"[SERVER] {message}")
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
    log_message(f"Joined room {room.name}")
    if room.name != config['room']:
        mousebot_enums.update_one({"type": "room"}, {"$set": {"data.name": room.name, "data.is_tribe": room.is_tribe}})


# @tfm_bot.event
# async def on_raw_socket(connection, packet):
#     CCC = packet.readCode()
#     # exclude = [(4, 3), (4, 4), (60, 3), (28, 6)]
#     # if CCC not in exclude:
#     #     log_message(packet, CCC)
#     if CCC == (8, 20):
#         log_message(packet, CCC)


@tfm_bot.event
async def on_connection_error(connection, exception):
    sys.exit(1)


@tfm_bot.event
async def on_new_member(name):
    await tribe_status_message(f"{name.capitalize()} has joined the tribe! Welcome!!")
    await get_stats()


@tfm_bot.event
async def on_left_member(name):
    await tribe_status_message(f"{name.capitalize()} has left the tribe. Sad.")


@tfm_bot.event
async def on_kicked_member(name):
    await tribe_status_message(f"{name.capitalize()} has been kicked from the tribe! Later bitch!!")


@tfm_bot.event
async def on_map_load(map_data):
    records = await get_records(map_data['code'])

    if len(map_data['author']) == 0 or str(map_data['category']) == "87":
        RECENT_MAPS.insert(0, (f"(@{map_data['code']} - Vanilla)", records))
        return
    else:
        category_name = mousebot_enums.find_one({"type": "map_category", "data.id": str(map_data['category'])})['data']
        try:
            RECENT_MAPS.insert(0, (f"({map_data['author']} - @{map_data['code']} - {category_name['name']})", records))
            mousebot_maps.insert_one(map_data)
        except pymongo.errors.DuplicateKeyError:
            pass
    if len(RECENT_MAPS) > 50:
        del RECENT_MAPS[-1]


@tfm_bot.event
async def on_player_won(player, order, player_time):
    username = player.username.capitalize()
    member_names = [member.name.capitalize() for member in TRIBE[0].members]

    if username not in member_names:
        return

    if order == 1:
        await tfm_bot.sendCommand(f"profile {username}")
        profile = await tfm_bot.wait_for('on_profile', lambda p: p.username == username, timeout=5)
        firsts = profile.stats.firsts
        title = ""
        for item in db_titles:
            if item['type'] == "cheese_first" and item['number'] > firsts:
                title = f"You need {item['number'] - firsts} more firsts for «{'/'.join(item['titles'])}»"
                break

        await tfm_bot.whisper(username, f"You came in first in {player_time} seconds. {title}")
        log_message(f"[Whisper] [{username}] You came first in {player_time} seconds. {title}")

    player_record = mousebot_enums.find_one({"type": "opt", "data.name": username, "data.optin": True})

    if player_record is not None:
        records = RECENT_MAPS[0][1]

        if records is None:
            return

        first_record = records[0][0]
        normal_time = float(first_record.split(' ')[2][:-1]) + 3

        await tfm_bot.whisper(username, f"The record for this map is {first_record} ({normal_time}s)")
        log_message(f"[Whisper] [{username}] The record for this map is {first_record} ({normal_time}s)")
        


@tfm_bot.event
async def on_sale(item_data):
    try:
        mousebot_sales.insert_one(item_data)
    except pymongo.errors.DuplicateKeyError:
        pass


async def process_command(message, origin, author, discord_channel=None):
    author_name = author

    if origin != "tribe" and discord_channel is None:
        author_name = author.username

    split_message = message.split(" ")

    # General commands
    if message == f"{PREFIX}help": # .help
        commands = ["I'm a bot for the tribe Coffee Corner! Commands: .time, .mom, .joke, .title [player#tag], .online, .8ball <message>, .funcorp/fc, .selfie, .maps [page], .sales, .stats [day/week/month/all] [player], .discord, .optin, .optout"]
        if author_name.capitalize() in CONTROL:
            commands.append("Control Commands: .greetings add/clear/list <name> <greeting>, .control add/del <username>, .tribe, .room <room>, .lua <pastebin>, .restart, .status")
        return commands

    elif message == f"{PREFIX}time": # .time
        await tfm_bot.sendCommand("time")
        time_string = await tfm_bot.wait_for('on_time', timeout=5)
        return [time_string]

    elif message.startswith(f"{PREFIX}mom"): # .mom
        joke = random.choice(JOKES)
        
        if len(split_message) > 1:
            regex = re.compile(re.escape("Yo"), re.IGNORECASE)
            joke = regex.sub(f"{' '.join(split_message[1:])}'s", joke)

        return [joke]
        

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
            profile = await tfm_bot.wait_for('on_profile', lambda p: p.username == author_name.capitalize(), timeout=5)
            cheese = profile.stats.gatheredCheese
            firsts = profile.stats.firsts
            bootcamps = profile.stats.bootcamps
            normalModeSaves = profile.stats.normalModeSaves
            hardModeSaves = profile.stats.hardModeSaves
            divineModeSaves = profile.stats.divineModeSaves
            withoutSkillSaves = profile.stats.withoutSkillSaves
        except asyncio.exceptions.TimeoutError:
            json = requests.get(f"https://cheese.formice.com/api/players/{author_name.capitalize().replace('#', '-')}").json()
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
            title_items.append(f"{offline}{author_name.capitalize()}, {', '.join(list(main_titles.values()))}")
        if len(shaman_titles) > 0:
            title_items.append(f"{offline}{author_name.capitalize()}, {', '.join(list(shaman_titles.values()))}")

        return title_items

    elif message == f"{PREFIX}online": # .online
        tribe = await tfm_bot.getTribe()
        members = tribe.members
        online = []
        for member in members:
            if member.online and member.name.capitalize() != config['username']:
                online.append(member.name.capitalize())
        if len(online) > 0:
            return [f"Online Players: {', '.join(online)}"]
        else:
            return ["No one is online."]

    elif message == f"{PREFIX}sales": # .sales
        if discord_channel is None:
            return ["Command only usable in discord"]

        # Remove old sales if any
        sales = mousebot_sales.find({})

        now = int(time.time())

        for item in sales:
            if item['expire_time'] < now:
                mousebot_sales.delete_one({'_id': item['_id']})

        # Print sales
        shop = SHOP[0]
        output = []
        sales = mousebot_sales.find({})

        now = datetime.now()
        expiry_date = datetime.utcfromtimestamp(sales[0]['expire_time'])
        duration = expiry_date - now
        seconds = duration.total_seconds()

        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)

        expire_time = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

        for item1 in sales:
            image_url = mousebot_shop_items.find_one({'item_id': item1['id'], 'category': item1['category'], 'is_shaman': item1['is_shaman']})['img']

            if item1['is_shaman']:
                for item2 in shop.shaman_objects:
                    if item1['uid'] == item2.id:
                        output.append((f"**{item2.cheese}** {config['CHEESE_EMOJI']} or ~~{item2.fraise}~~ **{ceil((1 - item1['discount']/100) * item2.fraise)}** {config['FRAISE_EMOJI']} (-{item1['discount']}%)\n`Ends in {expire_time}`", image_url))
                        break
            else:
                for item2 in shop.items:
                    if item1['id'] == item2.id and item1['category'] == item2.category:
                        output.append((f"**{item2.cheese}** {config['CHEESE_EMOJI']} or ~~{item2.fraise}~~ **{ceil((1 - item1['discount']/100) * item2.fraise)}** {config['FRAISE_EMOJI']} (-{item1['discount']}%)\n`Ends in {expire_time}`", image_url))
                        break

        for item, url in output:
            embed = Embed(title=item)
            embed.set_image(url=str(url))
            await discord_channel.send(embed=embed)

    elif message.startswith(f"{PREFIX}8ball"):
        if len(split_message) == 1:
            return ["Please ask a question."]
        return [random.choice(EIGHT_BALL)]
    
    elif message in [f"{PREFIX}funcorp", f"{PREFIX}fc"]: # .funcorp            
        with open(f"{directory}/statics/funcorp_lua.lua", 'r') as f:
            code = f.read()
            code = f"admin = {{\"{author_name.capitalize()}\"}}\n" + code
            await tfm_bot.loadLua(code)

    elif message.startswith(f"{PREFIX}maps"): # .maps [page]
        page = 1
        if len(split_message) > 1:
            page = int(split_message[1])
        offset = (page - 1) * 5
        # Picks out just maps from tuples for maps, records
        return [", ".join([item[0] for item in RECENT_MAPS[0 + offset:5 + offset]])]
    
    elif message.startswith(f"{PREFIX}record"): #.record <map>
        if len(split_message) == 1:
            return ["Please specify map code"]

        map_code = split_message[1]
        if map_code[0] == "@":
            map_code = map_code[1:]

        records = await get_records(map_code)

        if records is None:
            return ["No records found"]

        if len(split_message) == 3 and split_message[2] == "all":
                
            return [f"Records: {', '.join(records[0])}. (@{map_code} - {records[1]})"]

        return [f"{records[0][0]}. ({map_code} - {records[1]})"]

    elif message.startswith(f"{PREFIX}stats"): # .stats [day/week/month/all] [player]
        today = datetime.now().strftime("%Y/%m/%d")
        search_date = datetime.now()
        player = author_name.capitalize()

        if len(split_message) > 1:
            if split_message[1] == "week":
                search_date = search_date - timedelta(days=7)
            elif split_message[1] == "month":
                search_date = search_date - timedelta(days=30)
            elif split_message[1] == "all":
                search_date = search_date - timedelta(days=10000)
            elif split_message[1] != "day":
                return ["Invalid time frame: .stats [day/week/month/all] [player]"]

        if len(split_message) > 2:
            player = split_message[2].capitalize()

        stats = mousebot_stats.find_one({"name": player, "time": { "$gte": search_date.strftime("%Y/%m/%d"), "$lte": today } })

        if stats is None:
            return ["No stats found for player today"]

        await tfm_bot.sendCommand(f"profile {player}")
        try:
            profile = await tfm_bot.wait_for('on_profile', lambda p: p.username == player, timeout=5)
        except asyncio.exceptions.TimeoutError:
            return ["Player not online or not found"]
        
        stats_differences = {
            "cheese": int(profile.stats.gatheredCheese - stats["cheese"]),
            "firsts": int(profile.stats.firsts - stats["firsts"]),
            "bootcamps": int(profile.stats.bootcamps - stats["bootcamps"]),
            "normalModeSaves": int(profile.stats.normalModeSaves - stats["normalModeSaves"]),
            "hardModeSaves": int(profile.stats.hardModeSaves - stats["hardModeSaves"]),
            "divineModeSaves": int(profile.stats.divineModeSaves - stats["divineModeSaves"]),
            "withoutSkillSaves": int(profile.stats.withoutSkillSaves - stats["withoutSkillSaves"])
        }

        return [f"{player} stat gains from {stats['time']}: {stats_differences['cheese']} cheese, {stats_differences['firsts']} first(s), {stats_differences['bootcamps']} bootcamp(s), {stats_differences['normalModeSaves']} normal save(s), {stats_differences['hardModeSaves']} hard save(s), {stats_differences['divineModeSaves']} divine save(s), {stats_differences['withoutSkillSaves']} without skill save(s)."]

    elif message.startswith(f"{PREFIX}discord"): # .discord
        return ["Join the Discord here: https://discord.gg/hjuXYvUFBd"]

    elif message.startswith(f"{PREFIX}optin"): # .optin
        player = mousebot_enums.find_one({"type": "opt", "data.name": author_name.capitalize()})
        print(player['data']['optin'], type(player['data']['optin']))
        if player == None:
            mousebot_enums.insert_one({"type": "opt", "data" : {"name": author_name.capitalize(), "optin": True}})
        elif not player['data']['optin']:
            mousebot_enums.update_one({"type": "opt", "data.name": author_name.capitalize()}, {"$set": {"data.optin": True}})
            return [f"Optted {author_name.capitalize()} in."]
        else:
            return [f"{author_name.capitalize()} you are already optted in."]

    elif message.startswith(f"{PREFIX}optout"): # .optout
        player = mousebot_enums.find_one({"type": "opt", "data.name": author_name.capitalize()})
        print(player['data']['optin'], type(player['data']['optin']))
        if player == None:
            mousebot_enums.insert_one({"type": "opt", "data" : {"name": author_name.capitalize(), "optin": False}})
        elif player['data']['optin']:
            mousebot_enums.update_one({"type": "opt", "data.name": author_name.capitalize()}, {"$set": {"data.optin": False}})
            return [f"Optted {author_name.capitalize()} out."]
        else:
            return [f"{author_name.capitalize()} you are already optted out."]        

    # Admin commands
    if author_name.capitalize() in CONTROL:
        if message.startswith(f"{PREFIX}greetings"):
            # .greetings add/clear/list <name> <greeting>
            if split_message[1] == "add":
                mousebot_greetings.insert_one({"name": split_message[2].capitalize(), "greeting": " ".join(split_message[3:])})
                return [f"Added greeting to {split_message[2].capitalize()}"]
            elif split_message[1] == "clear":
                mousebot_greetings.delete_many({"name": split_message[2].capitalize()})
                return [f"Cleared greetings of {split_message[2].capitalize()}"]
            elif split_message[1] == "list":
                greetings_list = [g['greeting'] for g in mousebot_greetings.find({"name": split_message[2].capitalize()}, { "_id": 0, "name": 0})]
                return [f"Greetings for {split_message[2].capitalize()}: {greetings_list}"]

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
            try:
                room = await tfm_bot.wait_for('on_joined_room', timeout=5)
            except asyncio.exceptions.TimeoutError:
                return ["Room join failed, try again"]
            return [f"Joined tribe house"]

        elif message.startswith(f"{PREFIX}room"): # .room <room>
            await tfm_bot.joinRoom(" ".join(split_message[1:]))
            try:
                room = await tfm_bot.wait_for('on_joined_room', timeout=5)
            except asyncio.exceptions.TimeoutError:
                return ["Room join failed, try again"]
            return [f"Joined room {room.name}"]


        elif message.startswith(f"{PREFIX}lua"): # .lua <pastebin>
            if len(split_message) == 1:
                return ["Please add pastebin URL"]
            url = "https://pastebin.com/raw/" + split_message[1].split('/')[3]
            code = requests.get(url)
            if code.status_code != 200:
                return ["Invalid pastebin URL"]

            await tfm_bot.loadLua(code.text)
        
        elif message == f"{PREFIX}restart": # .restart
            subprocess.run(["sudo", "systemctl", "reset-failed", "mousebot.service"])
            subprocess.run(["sudo", "systemctl", "restart", "mousebot.service"])

        elif message == f"{PREFIX}status": # .status
            status = subprocess.check_output(["systemctl", "status", "mousebot.service"])
            return [status.decode('utf-8').split("\n")[2].strip()]


    # Owner Commands
    if author_name.capitalize() in OWNER:
        if message.startswith(f"{PREFIX}exec"): # .exec <command>
            return [subprocess.check_output(split_message[1:]).decode("utf-8").strip()]
        
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

    # log_message(
    #     f'{discord_bot.user} is connected to the following guild:\n'
    #     f'{guild.name}(id: {guild.id})'
    # )


@discord_bot.event
async def on_message(message):
    if message.author == discord_bot.user:
        return

    elif message.channel.id == int(TRIBE_CHAT):
        await send_tribe_message(f"[Discord] [{message.author.display_name}] {message.content}")
        if message.content.startswith(PREFIX):
            output = await process_command(message.content, "tribe", f"{message.author.id}", message.channel)
            if output is not None:
                for item in output:
                    await send_tribe_message(item)
                    await send_discord_message(message.channel, f"[TFM] [{config['username'].capitalize()}] {item}")

    elif message.channel.id == int(TRIBE_ROOM_CHAT):
        try:
            is_tribe = tfm_bot.room.is_tribe
        except AttributeError:
            return log_message(f"[NOT ONLINE] [Discord] [{message.author.display_name}] {message.content}")

        if is_tribe:
            await send_room_message(f"[Discord] [{message.author.display_name}] {message.content}")

        if message.content.startswith(PREFIX):
            output = await process_command(message.content, "room", f"{message.author.id}", message.channel)
            if output is not None:
                for item in output:
                    if is_tribe:
                        await send_room_message(item)
                    await send_discord_message(message.channel, f"[TFM] [{config['username'].capitalize()}] {item}")
        elif not is_tribe:
            return await send_discord_message(message.channel, "Not in tribe house. Please use tribe-chat instead for non commands.")

#######################################################################################################################
##################################################### DISCORD BOT #####################################################
#######################################################################################################################


# Helper functions
async def send_tribe_message(message):
    await tfm_bot.sendTribeMessage(message)
    log_message(f"[tribe-chat] {message}")


async def send_room_message(message):
    await tfm_bot.sendRoomMessage(message)
    log_message(f"[tribe-room-chat] {message}")


async def send_discord_message(channel, message):
    await channel.send(message)
    log_message(f"[{channel}] {message}")


async def tribe_status_message(message):
    await update_tribe()
    await send_tribe_message(message)
    log_message(f"[Tribe Status] {message}")
    channel = discord_bot.get_channel(int(LOG_CHAT))
    await send_discord_message(channel, f"[Tribe Status] {message}")


def log_message(message, end="\n"):
    now = datetime.now().strftime("%Y/%m/%d, %H:%M:%S")
    print(f"[{now}] {message}", end=end)


async def update_tribe():
    TRIBE[0] = await tfm_bot.getTribe()


async def get_stats():
    log_message("Getting Stats..")
    online_members = [member.name.capitalize() for member in TRIBE[0].members if member.online]

    today = datetime.now().strftime("%Y/%m/%d")

    for name in online_members:
        player_row = mousebot_stats.find_one({"name": name.capitalize(), "time": today})
        if player_row is None:
            await tfm_bot.sendCommand(f"profile {name.capitalize()}")
            try:
                profile = await tfm_bot.wait_for('on_profile', lambda p: p.username == name.capitalize(), timeout=10)
                stats_dict = {
                    "name": name.capitalize(),
                    "cheese": profile.stats.gatheredCheese,
                    "firsts": profile.stats.firsts,
                    "bootcamps": profile.stats.bootcamps,
                    "normalModeSaves": profile.stats.normalModeSaves,
                    "hardModeSaves": profile.stats.hardModeSaves,
                    "divineModeSaves": profile.stats.divineModeSaves,
                    "withoutSkillSaves": profile.stats.withoutSkillSaves,
                    "time": today
                }

                mousebot_stats.insert_one(stats_dict)
            except Exception as e:
                print(f"ERROR Occured while getting stats for {name.capitalize()} ({e})")

    log_message("Getting Stats.. Done")


async def get_records(map_code):
    url = f"https://tfmrecords.tk/maps/{map_code}/"

    try:
        html = get(url)
    except HTTPError:
        return None
    
    soup = Soup(html)

    category = soup.find("sup")[-1].text

    records_table = soup.find("table")[0]

    if not isinstance(records_table.find("tr"), list):
        return None

    records = []

    for item in records_table.find("tr")[1:]:
        data = item.find("td")
        records.append(f"{data[1].text} - {data[2].text}s")

    return (records, category)


# Main bot loops
loop = asyncio.get_event_loop()

try:
    loop.create_task(tfm_bot.start())
except aiotfm.errors.AiotfmException:
    log_message("Server Unreachable, sleeping 2 mins..")
    time.sleep("120")
    sys.exit(0)

try:
    loop.create_task(discord_bot.run(TOKEN))

    loop.run_forever()
except RuntimeError:
    log_message("Bot Restarting..")
    sys.exit(0)
