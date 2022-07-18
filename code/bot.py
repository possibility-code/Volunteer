import discord
from discord.ext import commands
import os
import aiosqlite
import asyncio
import asyncpg
from decimal import *
from reader import TOKEN, DEFAULT_PREFIX, POSTGRESQL_URI_CONNECTION_STRING
from clocking_helpers.shutdown_clock_out import shutdown_clock_out_user

# Check upload info in the config.yml file before putting in production :)

async def initialise():
    bot.db = await aiosqlite.connect("code/database/data.db")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS in_progress (user_id int, date_started, PRIMARY KEY (user_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS workprofile (user_id int, role_id int, guild_id int, UNIQUE (user_id, role_id, guild_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS hr_roles (role_id int, PRIMARY KEY (role_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS on_loa (user_id int, start_date, end_date, reason str, PRIMARY KEY (user_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS need_checkup (user_id int, days, PRIMARY KEY (user_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS times (user_id int, date, time int NOT NULL DEFAULT 0, PRIMARY KEY (user_id, date))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS role_suffix (role_id int, suffix, PRIMARY KEY (role_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS permissions (user_id int, group_name, PRIMARY KEY (user_id, group_name))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS clock_message (guild_id, message_id, PRIMARY KEY (guild_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS statistics_message (guild_id, message_id, PRIMARY KEY (guild_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS hr_message (guild_id, message_id, PRIMARY KEY (guild_id))")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS weekly_completions (user_id, count, PRIMARY KEY (user_id))")
    bot.db.postgres = await asyncpg.connect(POSTGRESQL_URI_CONNECTION_STRING)
    await bot.db.postgres.execute("CREATE TABLE IF NOT EXISTS clocked_in_users (user_id BIGINT, PRIMARY KEY (user_id))")

intents = discord.Intents.default()
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
        command_prefix=DEFAULT_PREFIX,
        intents = intents
    )

    async def setup_hook(self):
        await self.loop.create_task(initialise())
        for ext in os.listdir('./code/functions'):
            if ext.endswith('.py'):
                await self.load_extension(f'functions.{ext[:-3]}')            

bot = MyBot()
bot.current = {}
bot.clocked_in_users = {}
bot.check_up_times = {}
bot.await_to_add = {}
bot.user_nicks = {}
bot.in_progress = {}
bot.remove_command('help')

@bot.command()
@commands.dm_only()
@commands.is_owner()
async def shutdown(ctx):
    """Clock out all users"""
    # Get the clocked channel, and delete the 'clock in' message
    # Then, for every user that is clocked in, clock them out
    vol_conn = await asyncpg.connect(POSTGRESQL_URI_CONNECTION_STRING)
    for user_id in list(bot.clocked_in_users.keys()):
        await shutdown_clock_out_user(bot, user_id)
        user = bot.get_user(user_id)
        await user.send("You have been clocked out as the ` shutdown ` command was used. You will be able to clock in again in a few minutes.")
    # Delete all of the information from the 'clocked_in_users' table
    await vol_conn.execute("DELETE FROM clocked_in_users")
    await vol_conn.close()
    await ctx.author.send("All users have been clocked out!")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


if __name__ == '__main__':
    bot.run(TOKEN)
    asyncio.run(bot.db.close()) 