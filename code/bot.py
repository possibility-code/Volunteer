import discord
from discord.ext import commands
import os
import aiosqlite
import asyncio
from decimal import *
from reader import TOKEN, DEFAULT_PREFIX

async def initialise():
    bot.db = await aiosqlite.connect("code/database/data.db")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS in_progress (user_id int, date_started, PRIMARY KEY (user_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS nonworkprofile (user_id int, role_id int, UNIQUE (user_id, role_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS workprofile (user_id int, role_id int, UNIQUE (user_id, role_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS hr_roles (role_id int, PRIMARY KEY (role_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS on_loa (user_id int, start_date, end_date, reason str, PRIMARY KEY (user_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS need_checkup (user_id int, days, PRIMARY KEY (user_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS times (user_id int, date, time int NOT NULL DEFAULT 0, PRIMARY KEY (user_id, date))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS role_suffix (role_id int, suffix, PRIMARY KEY (role_id))")

intents = discord.Intents.default()
intents.members = True

#CHECK UP NEEDS TO BE DONE, AND THE /GIVEPERMISSIONS COMMAND

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
        command_prefix=DEFAULT_PREFIX,
        activity = discord.Game(name="Ping Me For Help!"),
        intents = intents
    )

    async def setup_hook(self):
        await self.loop.create_task(initialise())
        for ext in os.listdir('./code/functions'):
            if ext.endswith('.py'):
                await self.load_extension(f'functions.{ext[:-3]}')

bot = MyBot()
bot.remove_command('help')

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


bot.run(TOKEN)
asyncio.run(bot.db.close())