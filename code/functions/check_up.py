import discord
from discord.ext import commands
from discord import app_commands, NotFound
import sqlite3
from discord.ext import tasks
import datetime

class check_up(commands.Cog, app_commands.Group, name="checkup"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    async def cog_load(self):
        self.add_checkup.start()


    async def check_hr_roles(self, interaction):
        #Retrieve all of the role IDs from the hr_roles table
        async with self.bot.db.execute("SELECT role_id FROM hr_roles") as cursor:
            roles = [row[0] for row in await cursor.fetchall()]

        #Define the authors roles 
        author_roles = interaction.user.roles

        #Check the ids from the author to the DB ids and return True is they have one of the roles else return False
        for role in author_roles:
            if role.id in roles:
                return True
        
        else:
            return False


    @tasks.loop(hours=24)
    async def add_checkup(self):
        await self.bot.wait_until_ready()
        #Grab all of the users that currently have a checkup in progress
        async with self.bot.db.execute("SELECT user_id FROM in_progress") as cursor:
            in_progress = [row[0] for row in await cursor.fetchall()]
        #Grab all of the users from the workprofile table
        async with self.bot.db.execute("SELECT user_id FROM times") as cursor:
            users = [row[0] for row in await cursor.fetchall()]   
        #For each user in the table, continue
        for user_id in users:
                #If the user_id matches on that is in the in_progress table, return
                if user_id in in_progress:
                    return
                #Else, go ahead and commit the changes which will add 1 day to the users curernt time
                try:
                    await self.bot.db.execute("INSERT INTO need_checkup (user_id, days) VALUES (?,?)", (user_id, 1))
                    await self.bot.db.commit()

                except sqlite3.IntegrityError:
                    await self.bot.db.execute("UPDATE need_checkup SET days = days + 1 WHERE user_id = ?", (user_id,))
                    await self.bot.db.commit()
        

    @app_commands.command()
    async def view(self, interaction: discord.Interaction):
        "View the checkup information for all users"
        if await self.check_hr_roles(interaction):
            #Create blank embed, set color to the member color
            embed = discord.Embed(
                title = "Checkup Data",
                description = "Just a moment"
            )
            await interaction.response.send_message(embed=embed)
            #Define the original message so that it can be edited
            msg = await interaction.original_message()
            #Create an embed with a blank description, then add one of the description we want
            embed.description = ""
            embed.description += "Below is a list of user who either currently need a checkup, or will soon need a checkup\n\n"

            #Grab the amount of days for all users
            async with self.bot.db.execute("SELECT user_id, days FROM need_checkup ORDER BY days DESC LIMIT ?", (20,)) as cursor:
                #For every days and user_id entry, do this -
                async for entry in cursor:
                    user_id, days = entry
                    #Only show members who need, or will soon need a checkup, so only users that have at least 15 days
                    if int(days) >= 15: 
                        try:
                            #Try to find the user and and then add the description to the embed
                            member = await self.bot.fetch_user(user_id)
                            embed.description += f"{member.mention}: Last Checkup - {days} days ago\n\n"
                        #If the user is deleted or not in the server, we get NotFound, so just pass it
                        except NotFound:
                            pass

            #Add the description to show in progress checkups
            embed.description += "**In Progress Checkups Shown Below:**\n\n"
            #Grab all of the user_id, and date_started from the in_progress table
            async with self.bot.db.execute("SELECT user_id, date_started FROM in_progress ORDER BY date_started DESC LIMIT ?", (20,)) as cursor:
                async for entry in cursor:
                    user_id, date_started = entry
                    #Try to grab the user and add it to the embed
                    try:
                        member = await self.bot.fetch_user(user_id)
                        embed.description += f"{member.mention}: Date Started - {date_started}\n\n"
                    #If the user is deleted or left the server, go ahead and delete their in_progress records
                    except NotFound:
                        await self.bot.db.execute("DELETE FROM in_progress WHERE user_id = ?", (member.id))
                        await self.bot.db.commit()

                #Edit the message with all of the new information
                await msg.edit(embed=embed)
            
        else:
            embed = discord.Embed(
                title = "Needed Roles Missing",
                description = "You are missing one of the required HR roles as defined by the database! If you believe this is an error, please make sure that all HR roles have been added using the `/hrrole add` command.",
                color = discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.describe(member="The member whose checkup you want to start")
    async def start(self, interaction: discord.Interaction, member: discord.Member):
        "Start a checkup for a user, and mark it as `in_progress`"
        if await self.check_hr_roles(interaction):
            #Get the days entry from the need_checkup table where the user_id = the member mentioned by the author
            async with self.bot.db.execute("SELECT days FROM need_checkup WHERE user_id = ?", (member.id,)) as cursor:
                data = await cursor.fetchone()
            #If there is an entry continue
            if data:
                #If the user has at least 15 days, continue
                if data[0] >= 15:
                    #Get the current date and convert it to day, month, year, hour, min
                    now = datetime.datetime.now()
                    date = now.strftime("%d/%m/%Y %H:%M")
                    try:
                        #Insert all of the info into the in_progress table
                        await self.bot.db.execute("INSERT INTO in_progress (user_id, date_started) VALUES (?,?)", (member.id, date))
                        await self.bot.db.commit()
                    #If an entry already exists, we get IntegrityError, so alert the author that the user is has a in progress checkup already
                    except sqlite3.IntegrityError:
                        embed = discord.Embed(
                            title = "Checkup Already in Progress",
                            description = f"{member.mention} already has their checkup marked as `in_progress`. To finish this checkup, you can use `/checkup finish`.",
                            color = discord.Color.red()
                        )
                        return await interaction.response.send_message(embed=embed, ephemeral=True)

                    #Delete the users info from the need_checkup table - just resets the amount of days the user has
                    await self.bot.db.execute("DELETE FROM need_checkup WHERE user_id = ?", (member.id,))
                    await self.bot.db.commit()
                    #Create the embed to show the user that the checkup has been marked as `in_progress`
                    embed = discord.Embed(
                        title = f"{member}'s Checkup has been marked as `in-progress`",
                        description = "When you have finished the checkup, end it using `/checkup finish`",
                        color = member.color
                    )

                    await interaction.response.send_message(embed=embed)
            #If there isnt an entry, alert the user
            else: 
                embed = discord.Embed(
                    title = "User Not in Need of Checkup",
                    description = f"{member.mention} does not currently need a checkup, come back later.",
                    color = discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            embed = discord.Embed(
                title = "Needed Roles Missing",
                description = "You are missing one of the required HR roles as defined by the database! If you believe this is an error, please make sure that all HR roles have been added using the `/hrrole add` command.",
                color = discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.describe(member="The member whose checkup you want to finish")
    async def finish(self, interaction: discord.Interaction, member: discord.Member):
        "Mark a users checkup as completed, and reset their 3 week time period"
        if await self.check_hr_roles(interaction):
            #Get all of the user_id from the checkups marked as `in_progress`
            async with self.bot.db.execute("SELECT user_id FROM in_progress") as cursor:
                data = await cursor.fetchone()
            #If there is data, continue
            if data:
                #If the member id is within the in_progress table, delete the entries
                if member.id in data:
                    await self.bot.db.execute("DELETE FROM in_progress WHERE user_id = ?", (member.id,))
                    await self.bot.db.commit()
                    #Create the embed to show the author that the checkup has been finished
                    embed = discord.Embed(
                        title = f"{member}'s Checkup Completed",
                        description = f"{member.mention} will not need another checkup for 21 days (3 weeks).",
                        color = member.color
                    )

                    await interaction.response.send_message(embed=embed)
            #If there isnt data, then the user doesnt have a checkup in progress, so alert the author
            else: 
                embed = discord.Embed(
                    title = "User Not in Checkup",
                    description = f"{member.mention} does not have an `in_progress` checkup at the moment, therefore one cannot be finished.",
                    color = discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            embed = discord.Embed(
                title = "Needed Roles Missing",
                description = "You are missing one of the required HR roles as defined by the database! If you believe this is an error, please make sure that all HR roles have been added using the `/hrrole add` command.",
                color = discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            

async def setup(bot):
    await bot.add_cog(check_up(bot))