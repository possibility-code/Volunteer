import sqlite3
import discord
from discord.ext import commands, tasks
import time
import asyncio
from clocking_helpers.send_attention_message import send_attention_message
from reader import CLOCKING_CHANNEL_ID, HR_CHANNEL_ID
from clocking_helpers.clock_view import ClockView
import datetime

class task(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_load(self):
        self.change_status.start()
        self.attention.start()
        self.connect_to_clock.start()
        self.add_weekly_completions.start()

    def get_hours(self, time_in_seconds):
        hours = round(time_in_seconds // 3600, 1)
        return hours

    @tasks.loop(seconds=30)
    async def add_weekly_completions(self):
        totals = {}
        # Get all of the times for every day in the past week for every user
        # Then for each day we add the time of that day to the totals dict (user_id:time)
        for i in range(0, 7):
            async with self.bot.db.execute("SELECT user_id, time FROM times WHERE date = ?", (datetime.date.today() - datetime.timedelta(days=i),)) as cursor:
                async for entry in cursor:
                    user_id, time = entry
                    try:
                        totals[user_id] = totals[user_id] + time
                    except:
                        totals[user_id] = time

        # For every entry in the totals keys, we divide their time by 60 and then 60 again
        # if they have had more than or equal to 8 hours, we add them to the weekly_completions table
        for user_id in list(totals.keys()):
            if totals[user_id]/60 >= 8:
                try:
                    await self.bot.db.execute("INSERT INTO weekly_completions (user_id, count) VALUES (?, ?)", (user_id, 1))
                    await self.bot.db.commit()
                except sqlite3.IntegrityError:
                    await self.bot.db.execute("UPDATE weekly_completions SET count = count + 1 WHERE user_id = ?", (user_id,))
                    await self.bot.db.commit()

    
    #Before the add_weekly_completions loop, sleep until Sunday at 11 pm
    @add_weekly_completions.before_loop
    async def sleep_till_sunday_11pm():
        # Sleep until Sunday at 11 pm
        now = datetime.datetime.now()
        delta = datetime.timedelta(days=6 - now.weekday(), hours=23 - now.hour, minutes=59 - now.minute, seconds=59 - now.second)
        await asyncio.sleep(delta.total_seconds())


    @tasks.loop(minutes=2)
    async def change_status(self):
        await self.bot.wait_until_ready()
        # If there is data, continue
        if self.bot.current:
            # If there is only 1 active volunteer, use the singular 'volunteer'
            if self.bot.current['count'] == 1:
                await self.bot.change_presence(activity=discord.Activity(name=f"1 volunteer", type=discord.ActivityType.watching))
            # Otherwise, the plural will be used 'volunteers'
            else:
                await self.bot.change_presence(activity=discord.Activity(name=f"{self.bot.current['count']} volunteers", type=discord.ActivityType.watching))
        # Else, no data, so show that there are no active volunteers
        else:
            await self.bot.change_presence(activity=discord.Activity(name="0 volunteers", type=discord.ActivityType.watching))


    """Handle Check-Up Messages for Users that are Clocked In"""
    @tasks.loop(seconds=30)
    async def attention(self):
        await self.bot.wait_until_ready()
        i = 0
        # Update the dict 'current' entry 'count' with the amount of current active volunteers
        for user_id in self.bot.clocked_in_users:
            i += 1
        self.bot.current['count'] = i
        # Create a list and iterate through the clocked in users
        for user_id in list(self.bot.check_up_times): 
            # Fetch the user and their time in seconds
            member = self.bot.get_user(user_id)
            user_time = round(time.time() - self.bot.check_up_times[user_id], 0)
            # If the user has been clocked in for more than 15 minutes, we send the attention message         
            if user_time / 60 >= 15 and user_id not in list(self.bot.in_progress.keys()):
                asyncio.create_task(send_attention_message(self, member, user_id))
            # Else, the user hasn't been clocked in for less than 15 minutes, so return
            else:
                return


    @tasks.loop(minutes=30)
    async def connect_to_clock(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(CLOCKING_CHANNEL_ID)
        hr_channel = self.bot.get_channel(HR_CHANNEL_ID)
        # Get all of the message information from the DB
        clock_message = await self.bot.db.execute("SELECT message_id FROM clock_message")
        clock_message_id = await clock_message.fetchone()
        statistics_message = await self.bot.db.execute("SELECT message_id FROM statistics_message")
        statistics_message_id = await statistics_message.fetchone()
        hr_message = await self.bot.db.execute("SELECT message_id FROM hr_message")
        hr_message_id = await hr_message.fetchone()
        # Attempt to get the partial message from their respective channels
        try:
            clock_message = channel.get_partial_message(clock_message_id[0])
        except:
            return print("Clock Message Finding Error")

        try:
            statistics_message = channel.get_partial_message(statistics_message_id[0])
        except:
            return print("Statistics Message Finding Error")

        try:
            hr_message = hr_channel.get_partial_message(hr_message_id[0])
        except:
            return print("HR Message Finding Error")

        # Define variables, and calculate the dates for today, yesteraday, and one week ago
        today = datetime.date.today()
        first_of_week = datetime.date.today().weekday() + 1
        first_of_month = int(datetime.date.today().day)
        # Create the finals dictionary, so that all of the correct date can be pulled
        finals = {}
        # Retrieve all of the necessary data (time, date) from the 'times' table
        async with self.bot.db.execute("SELECT time, date FROM times") as cursor:
            # For every entry in the table, add date:time to the 'finals' dict
            async for entry in cursor:
                time, date = entry
                try:
                    finals[date] = finals[date] + time
                except:
                    finals[date] = time

        # If the user has data, sum all of the time entries and convert it
        total_time = sum(tuple(finals.values()))

        # For every day in the past week (1-7) see if there is an entry, then add it to the embed and send it
        week_time = 0
        for i in range(1, first_of_week):
            day = today - datetime.timedelta(days=i)
            try:
                week_time += int(finals.get(f'{day}'))
            except TypeError:
                pass

        month_time = 0
        for i in range(1, first_of_month):
            day = today - datetime.timedelta(days=i)
            try:
                month_time += int(finals.get(f'{day}'))
            except TypeError:
                pass

        total_time = self.get_hours(total_time)
        week_time = self.get_hours(week_time)
        month_time = self.get_hours(month_time)

        # Edit the statistics embed
        statistics = discord.Embed(
            title="Volunteer Statistics",
            description=f"Numbers are cool, so here are some automatically calculated numbers. This message is updated every 30 minutes.\n\n**Volunteered Hours Below**",
            color=0x0E8EFF
        )
        statistics.add_field(name="Total Hours", value=f"``` {total_time} ```", inline=True)
        statistics.add_field(name="Hours This Month", value=f"``` {month_time} ```", inline=True)
        statistics.add_field(name="Hours This Week", value=f"``` {week_time} ```", inline=True)
        
        await statistics_message.edit(embed=statistics)
        # Edit the clock embed
        clock = discord.Embed(
            title="Possibility Management",
            description=":stopwatch: - Clock In \n\n:alarm_clock: - Clock Out"
        )
        view = ClockView(self.bot)
        await clock_message.edit(embed=clock, view=view)
        # Edit the HR embed
        on_loa = await self.bot.db.execute("SELECT user_id FROM on_loa")
        on_loa = [i[0] for i in await on_loa.fetchall()]

        needing_checkups = await self.bot.db.execute("SELECT user_id FROM need_checkup WHERE days >= 21")
        needing_checkups = [i[0] for i in await needing_checkups.fetchall()]

        hr = discord.Embed(
            title="Human Resources - Current Information",
            description="See how the volunteers are doing at a glance.\n\n**VOLUNTEERS**"
        )
        hr.add_field(name="Clocked-in", value=f"``` {len(self.bot.clocked_in_users)} ```", inline=True)
        hr.add_field(name="On LOA", value=f"``` {len(on_loa)} ```", inline=True)
        hr.add_field(name="Needing Checkup", value=f"``` {len(needing_checkups)} ```", inline=True)

        members = ""
        for user_id in needing_checkups:
            members += f"\n- <@{user_id}>"

        hr.add_field(name="\n\nList of volunteers needing a checkup?", value=members, inline=False)
        hr.set_footer(text=f"Updated every 30 minutes | Last Updated: {datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')} UTC")

        await hr_message.edit(embed=hr)

async def setup(bot):
	await bot.add_cog(task(bot))