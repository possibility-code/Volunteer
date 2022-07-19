from discord.ext import commands, tasks
import time
import asyncio
import datetime
import sqlite3
from clocking_helpers.send_attention_message import send_attention_message

class midnight_tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_load(self):
        self.midnight_tasks.start()


    """
    This function is used to clock out users at midnight (which would be temporarily)
    No messages are sent, no roles or nicknames are changed
    """
    async def midnight_clock_out(self, user_id):
    # PERFORM CLOCK OUT ACTIVITIES, BECAUSE ITS MIDNIGHT
        try:
            if not self.bot.clocked_in_users[user_id]:
                return
        except KeyError:
            return
        # Calc the time that the user has been clocked in for (in seconds)
        add_time = round(time.time() - self.bot.clocked_in_users[user_id], 0)
        # Add the time to the DB 
        try:
            await self.bot.db.execute("INSERT INTO times (user_id, date, time) VALUES (?,?,?)", (user_id, datetime.date.today(), add_time))
            await self.bot.db.commit()
        except sqlite3.IntegrityError:
            await self.bot.db.execute("UPDATE times SET time = time + ? WHERE user_id = ?", (add_time, user_id))
            await self.bot.db.commit()  
        # Delete the clock out time for the user
        del self.bot.clocked_in_users[user_id]
        del self.bot.check_up_times[user_id]
        try:
            del self.bot.in_progress[user_id]
        except KeyError:
            return


    """
    This function is used to clock in a user at midnight
    No messages are sent, no roles or nicknames are changed
    """
    async def midnight_clock_in(self, user_id):
        # Check that the user is not already clocked in, if they are, return
        if user_id in self.bot.clocked_in_users:
            return
        # Make sure the user is not on LOA
        async with self.bot.db.execute("SELECT user_id FROM on_loa WHERE user_id = ?", (user_id,)) as cursor:
            data = await cursor.fetchone()
            if data:
                return
            else:
                pass
        # Grab the users 'days' data to make sure they are not overdue for a checkup
        async with self.bot.db.execute("SELECT days FROM need_checkup WHERE user_id = ?", (user_id,)) as cursor:
            days = await cursor.fetchone()
            try:
                days = days[0]
                # If they are over 21 days without a checkup, return
                if int(days) >= 21:
                    return
            except TypeError:
                pass
        # Grab the 'in_progress' data
        async with self.bot.db.execute("SELECT user_id FROM in_progress") as cursor:
            data = [row[0] for row in await cursor.fetchall()]
        # If the member is in the middle of a checkup, return
        if user_id in data:
            return
        # Store the time in the dict in order to keep track of how long someone has been clocked in
        self.bot.clocked_in_users[user_id] = time.time()
        self.bot.check_up_times[user_id] = time.time()


    """
    This function is used to add a day to the users checkup counter
    at midnight. If the users days reach 21 or above, they will no longer be allowed to clock in
    """
    async def add_checkup(self):
        # Grab all of the users that currently have a checkup in progress
        async with self.bot.db.execute("SELECT user_id FROM in_progress") as cursor:
            in_progress = [row[0] for row in await cursor.fetchall()]
        # Grab all of the users from the workprofile table
        async with self.bot.db.execute("SELECT user_id FROM times") as cursor:
            users = [row[0] for row in await cursor.fetchall()]   
        # Remove repeat entries from the `users` list
        users = list(set(users))
        # For each user in the table, continue
        for user_id in users:
            # If the user_id matches on that is in the in_progress table, return
            if user_id in in_progress:
                return

            on_loa = await self.bot.db.execute("SELECT user_id FROM on_loa WHERE user_id = ?", (user_id,))
            on_loa = await on_loa.fetchone()
            if on_loa:
                return

            # Else, go ahead and commit the changes which will add 1 day to the users curernt time
            try:
                await self.bot.db.execute("INSERT INTO need_checkup (user_id, days) VALUES (?,?)", (user_id, 1))
                await self.bot.db.commit()
            except sqlite3.IntegrityError:
                await self.bot.db.execute("UPDATE need_checkup SET days = days + 1 WHERE user_id = ?", (user_id,))
                await self.bot.db.commit()


    async def midnight_clocking(self):
        for user_id in list(set(self.bot.clocked_in_users.keys())):
            await self.midnight_clock_out(user_id)
            await self.midnight_clock_in(user_id)

    """
    Task loop to start the scheduled tasks
    """
    @tasks.loop(hours=24)
    async def midnight_tasks(self):
        await self.midnight_clocking()
        await self.add_checkup()

    """
    Wait until midnight to start the tasks
    """
    @midnight_tasks.before_loop
    async def before_midnight_tasks(self):
        hour = 0
        minute = 0
        now = datetime.datetime.now()
        future = datetime.datetime(now.year, now.month, now.day, hour, minute)
        if now.hour >= hour and now.minute > minute:
            future += datetime.timedelta(days=1)
        await asyncio.sleep((future-now).seconds)


async def setup(bot):
	await bot.add_cog(midnight_tasks(bot))