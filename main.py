import asyncio
import json
from datetime import datetime

from aiotfm.client import Client

with open('config.json') as f:
	config = json.load(f)

bot = Client(bot_role=True)

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
	print(message)
	if message.content == 'tribe':
		await bot.enterTribeHouse()
	await message.reply(message.content) # echo


@bot.event
async def on_room_message(message):
	print(message)
	if message.content == 'tribe':
		await bot.enterTribeHouse()

@bot.event
async def on_tribe_message(author, message):
    if message == f"{PREFIX}time":
        await bot.sendTribeMessage(f"{datetime.now()} (UTC)")
    else: 
        print(f"[Tribe Chat] {author}: {message}")

@bot.event
async def on_joined_room(room):
	print('Joined room:', room)


loop = asyncio.get_event_loop()
loop.create_task(bot.start())

loop.run_forever()
