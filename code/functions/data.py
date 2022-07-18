import discord
from discord.ext import commands
from discord import NotFound, app_commands
import datetime

class data(commands.GroupCog, name="data"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()


    def convert(self, sec):
        res = datetime.timedelta(seconds = sec)
        return res


    @app_commands.command()
    async def alltime(self, interaction: discord.Interaction):
        "Retrieves the alltime data for everyone in the server"
        # Create and send the basic embed while the data gets pulled
        embed = discord.Embed(
            title = "All-Time Data For Top 25",
            description = "Just a moment"
        )
        await interaction.response.send_message(embed=embed)
        # Create the original message so the message can be edited
        msg = await interaction.original_message()

        # Grab all of the required data from the database
        async with self.bot.db.execute("SELECT user_id FROM times") as cursor:
            ids = [row[0] for row in await cursor.fetchall()]

        # Turn `ids` into a set then a list in order to create a list of ONLY unique ids
        unique_ids = list(set(ids))

        finals = {}

        # For each unique id, pull all of their times
        for uniq_id in unique_ids:
            async with self.bot.db.execute("SELECT time FROM times WHERE user_id = ?", (uniq_id,)) as cursor:
                times = [row[0] for row in await cursor.fetchall()]

                # Create an int called user_time in order to add more time to it
                user_time = 0

                # For every time pulled from the DB, add it to user_time
                for time in times:
                    user_time = user_time + time

                finals[uniq_id] = user_time
        # Reverse the time in `finals` so that the times go from most to least
        finals_sorted = dict(sorted(finals.items(), key=lambda x: x[1], reverse=True))

        embed.description = ""

        for i in range(0, 24):
            try:
                # Pull the user_id
                uniq_id = list(finals_sorted.items())[i][0]
                # Get and calculate the users time in hrs/min/sec
                user_time = finals_sorted.get(uniq_id)
                user_time = self.convert(user_time)

                try:
                    # Grab the user and add the information into the description
                    member = self.bot.get_user(uniq_id)
                    embed.description += f"\n**{member.mention} : {user_time}**\n"

                # If the user isn't found, we get a NotFound error
                except NotFound:
                    # Still add the info into the description, but show that the user can't be found
                    member = f"Unknown Member (ID: {uniq_id})"
                    embed.description += f"\n**{member} : {user_time}**\n"

            except IndexError:
                await msg.edit(embed=embed)
        await msg.edit(embed=embed)


    @app_commands.command()
    @app_commands.describe(date="Specific date of data - year, month, day -  EX: 2022-04-15")
    async def daily(self, interaction: discord.Interaction, date: str):
        "Retrieves all of the data for everyone in the server for a specific date"
        # Grab all of the dates that have entries from the database
        async with self.bot.db.execute("SELECT date FROM times") as cursor:
            dates = [row[0] for row in await cursor.fetchall()]

        # If the date entered by the user has no entries, alert the user and return
        if date not in dates:
            embed = discord.Embed(
                title = "No Entries",
                description = f"There are no time entries for {date}.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Else if the date entered has an entry, continue
        elif date in dates:
            # Create the embed in order to get ready to add the descriptions for each entry
            embed = discord.Embed(
                title = f"Top 25 Entries For {date}",
                description = ""
            )
            await interaction.response.send_message(embed=embed)
            # Define the original message so that the message can be edited with the new embed
            msg = await interaction.original_message()

            # Grab all of the required data from the database
            async with self.bot.db.execute("SELECT user_id, time FROM times WHERE date = ? ORDER BY time DESC", (date,)) as cursor:
                async for entry in cursor:
                    # For each entry add to the index and calculate the amount of time in hrs/min/sec
                    user_id, time = entry
                    user_time = self.convert(time)
                    try:
                        # Grab the user and add the information into the description
                        member = self.bot.get_user(user_id)
                        embed.description += f"\n**{member.mention} : {user_time}**\n"

                    # If the user isn't found, we get a NotFound error
                    except NotFound:
                        # Still add the info into the description, but show that the user can't be found
                        member = f"Unknown Member (ID: {user_id})"
                        embed.description += f"\n**{member} : {user_time}**\n"
        
            # Edit the message with the new embed material
            await msg.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(data(bot))