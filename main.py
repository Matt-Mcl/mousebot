import sys
import asyncio
import json
from datetime import datetime

import aiotfm

directory = sys.argv[1]

with open(f"{directory}/config.json") as f:
	config = json.load(f)

bot = aiotfm.Client(bot_role=True)

boot_time = bot.loop.time()

PREFIX="."


@bot.event
async def on_login_ready(*a):
	print('Logging in ...')
	await bot.login(**config)


@bot.event
async def on_ready():
	print(f'Connected to the community platform in {bot.loop.time() - boot_time:.2f} seconds')
	await bot.enterTribe()


@bot.event
async def on_whisper(message):
    if message.author.username != config['username']:
        if message.content == f"{PREFIX}help":
            await message.reply("Currently I don't do very much but I'm working on it! Commands: .time")
        elif message.content == f"{PREFIX}time":
            await message.reply(f"{datetime.now()} (UTC)")
        else:
            await message.reply(message.content) # echo


@bot.event
async def on_room_message(message):
	print(message)


@bot.event
async def on_tribe_message(author, message):
    if message == f"{PREFIX}help":
        await bot.sendTribeMessage("Currently I don't do very much but I'm working on it! Commands: .time")
    elif message == f"{PREFIX}time":
        await bot.sendTribeMessage(f"{datetime.now()} (UTC)")
    else: 
        print(f"[Tribe Chat] {author}: {message}")


@bot.event
async def on_joined_room(room):
	print('Joined room:', room)


loop = asyncio.get_event_loop()
loop.create_task(bot.start())

loop.run_forever()
