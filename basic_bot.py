import asyncio
import aiotfm
import json
from datetime import datetime

tfm_bot = aiotfm.Client(bot_role=True)

boot_time = tfm_bot.loop.time()

with open(f"config/config.json") as f:
    config = json.load(f)


@tfm_bot.event
async def on_login_ready(*a):
    log_message('Logging in..')
    await tfm_bot.login(config['username'], config['password'], config['encrypted'], config['room'])
    log_message('Logging in.. Done')


@tfm_bot.event
async def on_ready():
    log_message(f'Connected to the community platform in {tfm_bot.loop.time() - boot_time:.2f} seconds')


def log_message(message, end="\n"):
    now = datetime.now().strftime("%Y/%m/%d, %H:%M:%S")
    print(f"[{now}] {message}", end=end)

async def check_connected(time):
    await asyncio.sleep(time)
    # Checks if the bot is connected by seeing if it's in a room
    if tfm_bot.room is None:
        log_message(f"TFM Bot failed to connect in {time} seconds")
        await check_connected(time + 30)

# Main bot loops
loop = asyncio.get_event_loop()


loop.create_task(check_connected(30))

loop.create_task(tfm_bot.start())

loop.run_forever()
