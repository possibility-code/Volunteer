import discord
from discord.ext import commands
from reader import CLOCKING_CHANNEL_ID, TEAM_SERVER, HR_CHANNEL_ID
from clocking_helpers.clock_view import ClockView
import datetime

class setup_cmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    def get_hours(self, time_in_seconds):
        hours = round(time_in_seconds // 3600, 1)
        return hours


    @commands.command()
    @commands.is_owner()
    @commands.dm_only()
    async def setup(self, ctx):
        channel = self.bot.get_channel(CLOCKING_CHANNEL_ID)
        # Define variables, and calculate the dates for today, the beginning of the week, and the
        # beginning of the month
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
        # Sum all of the entries to get the total time
        total_time = sum(tuple(finals.values()))

        # For every entry in this week, add it to 'week_time'
        week_time = 0
        for i in range(1, first_of_week):
            day = today - datetime.timedelta(days=i)
            try:
                week_time += int(finals.get(f'{day}'))
            except TypeError:
                pass
        # For every entry in this month, add it to 'month_time'
        month_time = 0
        for i in range(1, first_of_month):
            day = today - datetime.timedelta(days=i)
            try:
                month_time += int(finals.get(f'{day}'))
            except TypeError:
                pass
        # Convert all of the times to hours
        total_time = self.get_hours(total_time)
        week_time = self.get_hours(week_time)
        month_time = self.get_hours(month_time)
        # Paragraph embed
        paragraph = discord.Embed(
            description="You empower our movement to create change. We might not significantly impact the world today, but we do have a considerable affect on a family that could have had a very different tomorrow. Let's show that this would is still worth living for, even those in the darkness, by providing an environment built with empathy.",
            color=0x0E8EFF
        )
        paragraph.set_footer(text="Founder - Keegan Barnum")
        # Statistics embed
        statistics = discord.Embed(
            title="Volunteer Statistics",
            description=f"Numbers are cool, so here are some automatically calculated numbers. This message is updated every 30 minutes.\n\n**Volunteered Hours Below**",
            color=0x0E8EFF
        )
        statistics.add_field(name="Total Hours", value=f"``` {total_time} ```", inline=True)
        statistics.add_field(name="Hours This Month", value=f"``` {month_time} ```", inline=True)
        statistics.add_field(name="Hours This Week", value=f"``` {week_time} ```", inline=True)
        # Clock embed
        clock = discord.Embed(
            title="Possibility Management",
            description=":stopwatch: - Clock In \n\n:alarm_clock: - Clock Out"
        )
        view = ClockView(self.bot)

        # HR Embed
        hr_channel = self.bot.get_channel(HR_CHANNEL_ID)

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

        hr.description += "\n\nList of volunteers needing a checkup?"
        for user_id in needing_checkups:
            hr.description += f"\n- <@{user_id}>"

        hr.set_footer(text=f"Updated every 30 minutes | Last Updated: {datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')} UTC")

        # Clear the 2 channels in case they have something in them
        await channel.purge(limit=5)
        await hr_channel.purge(limit=5)

        await channel.send(embed=paragraph) # Send paragraph
        statistics_msg = await channel.send(embed=statistics) # Send and assign statistics message
        clock_msg = await channel.send(embed=clock, view=view) # Send and assign clock message
        hr_msg = await hr_channel.send(embed=hr) # Send and assign hr message

        # Add or update the statistics, clock message, and HR message IDs in the database
        try:
            await self.bot.db.execute("INSERT INTO clock_message (guild_id, message_id) VALUES (?,?)", (TEAM_SERVER, clock_msg.id))
            await self.bot.db.commit()
        except:
            await self.bot.db.execute("UPDATE clock_message SET message_id = ? WHERE guild_id = ?", (clock_msg.id, TEAM_SERVER))
            await self.bot.db.commit()

        try:
            await self.bot.db.execute("INSERT INTO statistics_message (guild_id, message_id) VALUES (?,?)", (TEAM_SERVER, statistics_msg.id,))
            await self.bot.db.commit()
        except:
            await self.bot.db.execute("UPDATE statistics_message SET message_id = ? WHERE guild_id = ?", (statistics_msg.id, TEAM_SERVER))
            await self.bot.db.commit()

        try:
            await self.bot.db.execute("INSERT INTO hr_message (guild_id, message_id) VALUES (?,?)", (TEAM_SERVER, hr_msg.id,))
            await self.bot.db.commit()
        except:
            await self.bot.db.execute("UPDATE hr_message SET message_id = ? WHERE guild_id = ?", (hr_msg.id, TEAM_SERVER))
            await self.bot.db.commit()

        await ctx.author.send("Setup complete!")


async def setup(bot):
	await bot.add_cog(setup_cmd(bot))