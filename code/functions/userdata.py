import discord
from discord.ext import commands
from discord import app_commands
import datetime
from functions.permission import permission

class userdata(commands.GroupCog, name="userdata"):
    def __init__(self, bot):
        self.bot = bot
        self.perms = permission(self.bot)
        super().__init__()

    # Convert the seconds to the correct format, then return the new format time
    def convert(self, sec):
        res = datetime.timedelta(seconds = sec)
        return res


    @app_commands.command()
    @app_commands.describe(member="Member whose all-time data you would like to see")
    async def alltime(self, interaction: discord.Interaction, member: discord.Member):
        "Retrieves the alltime data for the specified user"
        # Check that the user has permission to view the alltime data
        if await self.perms.check_perms(interaction.user.id, "userdata"):
            # Define variables, and calculate the dates for today, yesteraday, and one week ago
            user_id = member.id
            today = datetime.date.today()
            yesterday = today - datetime.timedelta(days=1)
            last_week = today - datetime.timedelta(days=7)
            # Create the finals dictionary, so that all of the correct date can be pulled
            finals = {}
            # Retrieve all of the necessary data (time, date) from the 'times' table
            async with self.bot.db.execute("SELECT time, date FROM times WHERE user_id = ?", (user_id,)) as cursor:
                # For every entry in the table, add date:time to the 'finals' dict
                async for entry in cursor:
                    time, date = entry
                    finals[date] = time

            # If the sum of all of the values in the dict (times) is 0, then tell the 
            # author that the user has no data
            if sum(tuple(finals.values())) == 0:
                embed = discord.Embed(
                    title=f"All-Time Data For {member}",
                    description="This member has no data!",
                    color = member.color
                )
                return await interaction.response.send_message(embed=embed)
            # If the user has data, sum all of the time entries and convert it
            else:
                user_time = self.convert(sum(tuple(finals.values())))
            # Try to convert the time for today
            try:
                today_time = self.convert(finals.get(f'{today}'))
            # If there is no entry, we get TypeError, so set today_time to show that there is no entry
            except TypeError:
                today_time = f"No time"
            # Try to convert the time for yesterday
            try:
                yesterday_time = self.convert(finals.get(f'{yesterday}'))
            # If there is no entry, we get TypeError, so set yesterday_tim to show that there is no entry
            except TypeError:
                yesterday_time = f"No time"
            # Create the embed and add in the information we just calculated
            embed = discord.Embed(
                title = f"All-Time Data For {member}",
                description= "",
                color = member.color
            )
            embed.description += (f"Total Time: {user_time}\n\n")
            embed.description += (f"Today {today}: {today_time}\n\n")
            embed.description += (f"Yesterdays Time: {yesterday_time}\n\n")
            embed.description += (f"Week of {last_week} to {today}:\n\n")
            # For every day in the past week (1-7) see if there is an entry, then add it to the embed and send it
            for i in range(1, 8):
                day = today - datetime.timedelta(days=i)
                try:
                    day_time = self.convert(finals.get(f'{day}'))
                except TypeError:
                    day_time = "No time"

                embed.description += (f"{day}: {day_time}\n")

            await interaction.response.send_message(embed=embed)
        # Else, send a message letting the user know they do not have permission
        else:
            embed = discord.Embed(
                title = "Missing Permissions",
                description = "You do not have permission to use the `userdata` group of commands! An administrator must give you permission using the `/permission` command.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.describe(member="Member whose data you would like to view")
    @app_commands.describe(date="Specific date of data - year, month, day -  EX: 2022-04-15")
    async def daily(self, interaction: discord.Interaction, member: discord.Member, date: str):
        "Retrieves all of the data for everyone in the server for a specific date"
        # Check that the user has permission to view the daily data
        if await self.perms.check_perms(interaction.user.id, "userdata"):
            user_id = member.id
            # Retrieve the needed information (just the time) from the times table
            async with self.bot.db.execute("SELECT time FROM times WHERE user_id = ? AND date = ?", (user_id, date)) as cursor:
                data = await cursor.fetchone()
            if not data:
            # If there is no time entry for that user, alert the author
                embed = discord.Embed(
                    title = f"No Time Data",
                    description = f"{member.mention} does not have any time entry for {date}",
                    color = discord.Color.red()
                )

                return await interaction.response.send_message(embed=embed, ephemeral=True)
            # Else, there is a time entry, so send the embed that shows how much time was posted by that user
            else:
                time = data
                date_time = self.convert(time[0])
                embed = discord.Embed(
                    title = f"Data For {member} on {date}",
                    description = f"{date}: {date_time}",
                    color = member.color
                )

                await interaction.response.send_message(embed=embed)
        # Else, send a message letting the user know they do not have permission
        else:
            embed = discord.Embed(
                title = "Missing Permissions",
                description = "You do not have permission to use the `userdata` group of commands! An administrator must give you permission using the `/permission` command.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(userdata(bot))