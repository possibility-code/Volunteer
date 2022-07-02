import sqlite3
from tempfile import TemporaryFile
import discord
from discord.ext import commands, tasks
import asyncio
import time
import datetime
from reader import CLOCKING_CHANNEL_ID, MAIN_SERVER, TEAM_SERVER

class TimerError(Exception):
    """Used to report errors within the clock in/out functions"""

class ClockView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.attention.start()
        bot.clocked_in_users = {}
        bot.check_up_times = {}
        bot.await_to_add = {}
        bot.user_nicks = {}


    async def get_nickname(self, interaction):
        #Get the roles from the database in order to check them against the users roles
        async with self.bot.db.execute("SELECT role_id FROM role_suffix") as cursor:
            roles = [row[0] for row in await cursor.fetchall()]

        #Grab the users roles in order from low to high, and create a new list for only ids
        low_to_high = interaction.user.roles
        id_only = []

        #Check the ids from the user to the DB ids and append matching ids to the id_only list
        for role in low_to_high:
            if role.id in roles:
                id_only.append(role.id)

        #Reverse list in order to rank roles from highest to lowest
        id_only.reverse()

        #Pull the first role id, which is the highest role
        nick_role_id = id_only[0]
        
        #Use the role id to retrive the suffix associated with it
        async with self.bot.db.execute("SELECT suffix FROM role_suffix WHERE role_id = ?", (nick_role_id,)) as cursor:
            data = await cursor.fetchone()
            nick_suffix = data[0]

        #Return the suffix
        return nick_suffix


    async def work_profile(self, user_id, decision):
        main_server = self.bot.get_guild(MAIN_SERVER)
        team_server = self.bot.get_guild(TEAM_SERVER)
        if decision == "add":
            #Pull the users work profile roles
            async with self.bot.db.execute("SELECT role_id FROM workprofile WHERE user_id = ?", (user_id,)) as cursor:
                #For each entry, define the role id
                async for entry in cursor:
                    role_id = entry[0]
                    #Try to add their roles in the main server
                    try:
                        member = main_server.get_member(user_id)
                        role = main_server.get_role(role_id)
                        await member.add_roles(role)
                    #If the role is in another server we get Attribute error, to try to add the role in the team server
                    except AttributeError:
                        pass
                    try:
                        member = team_server.get_member(user_id)
                        role = team_server.get_role(role_id)
                        await member.add_roles(role)
                    #If the role doesnt exists in either server, we get AttributeError, but we cant except for 
                    #that, so we just have to use a bare except
                    except AttributeError:
                        await self.bot.db.execute("DELETE FROM workprofile WHERE user_id = ?", (user_id,))

        elif decision == "remove":
            #Pull the users non-work profile roles
            async with self.bot.db.execute("SELECT role_id FROM workprofile WHERE user_id = ?", (user_id,)) as cursor:
                #For each entry, define the role id
                async for entry in cursor:
                    role_id = entry[0]

                    try:
                        member = main_server.get_member(user_id)
                        role = main_server.get_role(role_id)
                        return await member.remove_roles(role)
                    except AttributeError:
                        pass
                    try:
                        member = team_server.get_member(user_id)
                        role = team_server.get_role(role_id)
                        return await member.remove_roles(role)
                    #If the role doesnt exists in either server, we get AttributeError, but we cant except for 
                    #that, so we just have to use a bare except
                    except AttributeError:
                        await self.bot.db.execute("DELETE FROM workprofile WHERE user_id = ?", (user_id,))


    async def nonwork_profile(self, user_id, decision):
        main_server = self.bot.get_guild(MAIN_SERVER)
        team_server = self.bot.get_guild(TEAM_SERVER)
        if decision == "add":
            #Pull roles from the users non-work profile
            async with self.bot.db.execute("SELECT role_id FROM nonworkprofile WHERE user_id = ?", (user_id,)) as cursor:
                #For each entry, define the role id
                async for entry in cursor:
                    role_id = entry[0]
                    #Try to add their roles in the main server
                    try:
                        member = main_server.get_member(user_id)
                        role = main_server.get_role(role_id)
                        await member.add_roles(role)
                    #If the role is in another server we get Attribute error, to try to add the role in the team server
                    except AttributeError:
                        pass
                    try:
                        member = team_server.get_member(user_id)
                        role = team_server.get_role(role_id)
                        await member.add_roles(role)
                    #If the role doesnt exists in either server, we get AttributeError, but we cant except for 
                    #that, so we just have to use a bare except
                    except AttributeError:
                        await self.bot.db.execute("DELETE FROM nonworkprofile WHERE user_id = ?", (user_id,))

        elif decision == "remove":   
            #Pull the users non-work profile roles
            async with self.bot.db.execute("SELECT role_id FROM nonworkprofile WHERE user_id = ?", (user_id,)) as cursor:
                #For each entry, define the role id
                async for entry in cursor:
                    role_id = entry[0]
                    #Try removing the role from the member in the main server
                    try:
                        member = main_server.get_member(user_id)
                        role = main_server.get_role(role_id)
                        await member.remove_roles(role)
                    #If the role is in a different server we get Attribute error, so try the same thing on the `team_server`
                    except AttributeError:
                        pass
                    try:
                        member = team_server.get_member(user_id)
                        role = team_server.get_role(role_id)
                        await member.remove_roles(role) 
                    #If the role doesnt exists in either server, we get AttributeError, but we cant except for 
                    #that, so we just have to use a bare except
                    except AttributeError:
                        await self.bot.db.execute("DELETE FROM nonworkprofile WHERE user_id = ?", (user_id,))


    @discord.ui.button(label='Clock In', style=discord.ButtonStyle.green, row=1)
    async def clock_in(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        main_server = self.bot.get_guild(MAIN_SERVER)
        team_server = self.bot.get_guild(TEAM_SERVER)
        member_main = await main_server.fetch_member(interaction.user.id)
        member_team = await team_server.fetch_member(interaction.user.id)
        #Check that the user is not already clocked in, if they are, send a different message
        if interaction.user.id in self.bot.clocked_in_users:
            return await interaction.response.send_message("You are already clocked in!", ephemeral=True)

        #Make sure the user is not on LOA
        async with self.bot.db.execute("SELECT user_id FROM on_loa WHERE user_id = ?", (member.id,)) as cursor:
            data = await cursor.fetchone()
            if data:
                embed = discord.Embed(
                    title = "Your on LOA",
                    description = "You cannot clocked in, as you are on LOA. Come back at the end of your LOA period, or have an HR member end it early!",
                    color = discord.Color.red()
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                pass

        #Grab the users `days` data to make sure they are not overdue for a checkup
        async with self.bot.db.execute("SELECT days FROM need_checkup WHERE user_id = ?", (member.id,)) as cursor:
            days = await cursor.fetchone()
            try:
                days = days[0]
                #If they are over 21 days without a checkup, alert them and return
                if int(days) >= 21:
                    embed = discord.Embed(
                        title = "In Need of Checkup",
                        description = f"You are overdue for a checkup, I cannot clock you in until an HR members performs your checkup. Checkups are needed every 21 days, you last checkup was {days} ago.",
                        color = discord.Color.red()
                    )
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
            except TypeError:
                pass

        #Grab the `in_progress` data
        async with self.bot.db.execute("SELECT user_id FROM in_progress") as cursor:
            data = [row[0] for row in await cursor.fetchall()]
        #If the member is in the middle of a checkup, alert them and return
        if member.id in data:
            embed = discord.Embed(
                title = "Checkup in Progress",
                description = "You have a checkup that is currently in progress, therefore I cannot clock you in. Try again later after getting your checkup finished.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        #Gets the nickname/suffix that will need to be added to the user
        try:
            nickname = await self.get_nickname(interaction)

        #If the user doesnt have a role that matches with any roles in the DB, it throws IndexError
        except IndexError:
            embed = discord.Embed(
                title = "Needed Roles Missing",
                description = "You are missing one of the required support roles as defined by the database! If you believe this is an error, please make sure that all support roles have been added using the `/suffix add` command.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        #Add work profile roles and remove nonwork profile roles
        await self.work_profile(interaction.user.id, "add")
        await self.nonwork_profile(interaction.user.id, "remove")

        #Change nickname to add suffix - also store originalnickname in dict so that there name is 
        #restored once they clock out
        try:
            if member.nick:
                self.bot.user_nicks[interaction.user.id] = member.nick
                await member_main.edit(nick=f"{member.nick} | {nickname}")
                await member_team.edit(nick=f"{member.nick} | {nickname}")

            elif not member.nick:
                await member_main.edit(nick=f"{str(member.name)} | {nickname}")
                await member_team.edit(nick=f"{str(member.name)} | {nickname}")
        
        #If the user is above the bot, its cant change the nick, so clock them in but also alert them
        except discord.errors.Forbidden:
            self.bot.clocked_in_users[interaction.user.id] = time.time()
            self.bot.check_up_times[interaction.user.id] = time.time()
            return await interaction.response.send_message("You have been clocked in. However, your nickname wasn't changed as you are above the bot", ephemeral=True)

        #Store the time in the dict in order to keep track of how long someone has been clocked in
        self.bot.clocked_in_users[interaction.user.id] = time.time()
        self.bot.check_up_times[interaction.user.id] = time.time()
        await interaction.response.send_message("You are clocked in!", ephemeral=True)


    @discord.ui.button(label='Clock Out', style=discord.ButtonStyle.red, row=1)
    async def clock_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        main_server = self.bot.get_guild(MAIN_SERVER)
        team_server = self.bot.get_guild(TEAM_SERVER)
        member_main = await main_server.fetch_member(interaction.user.id)
        member_team = await team_server.fetch_member(interaction.user.id)
        #Check that the user is not already clocked out, if they are, send a different message
        try:
            if not self.bot.clocked_in_users[interaction.user.id]:
                return await interaction.response.send_message("You are already clocked out!", ephemeral=True)
        except KeyError:
            return await interaction.response.send_message("You are already clocked out!", ephemeral=True)

        #Restores the users name to their original nickname, or just their basic discord name
        if interaction.user.id in self.bot.user_nicks:
            try:
                await member_main.edit(nick=f"{self.bot.user_nicks[interaction.user.id]}")
                await member_team.edit(nick=f"{self.bot.user_nicks[interaction.user.id]}")
                #If the user had their nick stored, delete it
                del self.bot.user_nicks[interaction.user.id]

            except discord.errors.Forbidden:
                pass      
        #Try/Except to handle errors that would occur if the user is above the bot
        elif interaction.user.id not in self.bot.user_nicks:
            try:
                if interaction.user.id not in self.bot.user_nicks:
                    await member_main.edit(nick=None)
                    await member_team.edit(nick=None)

            except discord.errors.Forbidden:
                pass

        #Add nonwork profile roles and removes work profile roles
        await self.nonwork_profile(interaction.user.id, "add")
        await self.work_profile(interaction.user.id, "remove")

        #Calc the time that the user has been clocked in for (in seconds)
        add_time = round(time.time() - self.bot.clocked_in_users[interaction.user.id], 0)

        #Add the time to the DB 
        try:
            await self.bot.db.execute("INSERT INTO times (user_id, date, time) VALUES (?,?,?)", (interaction.user.id, datetime.date.today(), add_time))
            await self.bot.db.commit()
        except sqlite3.IntegrityError:
            await self.bot.db.execute("UPDATE times SET time = time + ? WHERE user_id = ?", (add_time, interaction.user.id))
            await self.bot.db.commit()  


        #Delete the clock out time for the user
        del self.bot.clocked_in_users[interaction.user.id]
        del self.bot.check_up_times[interaction.user.id]
        await interaction.response.send_message("I have clocked you out!", ephemeral=True)


    #This function is used to clock out users for them being AFK/not reacting to the attention message, this is used as the normal clock out function also sends messages and is slightly different
    async def clock_out_user_for_afk(self, user_id):
        main_server = self.bot.get_guild(MAIN_SERVER)
        team_server = self.bot.get_guild(TEAM_SERVER)
        member_main = await main_server.fetch_member(user_id)
        member_team = await team_server.fetch_member(user_id)
    #PERFORM CLOCK OUT ACTIVITIES, BECAUSE THEY DIDNT RESPOND
        try:
            if not self.bot.clocked_in_users[user_id]:
                return
        except KeyError:
            return
        #Restores the users name to their original nickname, or just their basic discord name
        if user_id in self.bot.user_nicks:
            try:
                await member_main.edit(nick=f"{self.bot.user_nicks[user_id]}")
                await member_team.edit(nick=f"{self.bot.user_nicks[user_id]}")
                #If the user had their nick stored, delete it
                del self.bot.user_nicks[user_id]

            except discord.errors.Forbidden:
                pass      
        #Try/Except to handle errors that would occur if the user is above the bot
        elif user_id not in self.bot.user_nicks:
            try:
                if user_id not in self.bot.user_nicks:
                    await member_main.edit(nick=None)
                    await member_team.edit(nick=None)

            except discord.errors.Forbidden:
                pass
        #Add nonwork profile roles and removes work profile roles
        await self.nonwork_profile(user_id, "add")
        await self.work_profile(user_id, "remove")
        #Calc the time that the user has been clocked in for (in seconds)
        add_time = round(time.time() - self.bot.clocked_in_users[user_id], 0)
        #Add the time to the DB 
        try:
            await self.bot.db.execute("INSERT INTO times (user_id, date, time) VALUES (?,?,?)", (user_id, datetime.date.today(), add_time))
            await self.bot.db.commit()
        except sqlite3.IntegrityError:
            await self.bot.db.execute("UPDATE times SET time = time + ? WHERE user_id = ?", (add_time, user_id))
            await self.bot.db.commit()  
        #Delete the clock out time for the user
        del self.bot.clocked_in_users[user_id]
        del self.bot.check_up_times[user_id]


    #Send the attention message to the user
    async def send_attention_message(self, member, user_id):
        try:
            #Send the message to the user, add the reaction, and check for the user to add a reaction with a timeout of 5 minutes
            msg = await member.send("It is time for your attention checkup, please react to this message within 5 minutes in order to stay clocked in!")
            await msg.add_reaction("\U00002705")
            reaction, _ = await self.bot.wait_for(
                'reaction_add', check=lambda reaction, member:member != self.bot.user and str(reaction.emoji) == "\U00002705" and reaction.message.id == msg.id, timeout=300
            )
        #If we get a TimeoutError, the user did not respond, so we clock them out
        except asyncio.TimeoutError:
            await self.clock_out_user_for_afk(user_id)
            return await member.send("You have been clocked out as you did not react in time!")
        #If the user reacts, we clock them in
        if reaction.emoji:
            await member.send("Thank you for showing you are still active!")
            self.bot.check_up_times[user_id] = time.time()

    #Create a loop that checks if the user is clocked in
    @tasks.loop(minutes=30)
    async def attention(self):
        #Wait until the bot is ready
        await self.bot.wait_until_ready()
        #Create a list and iterate through the clocked in users
        for user_id in list(self.bot.check_up_times):  
            #fetch the user and their time in seconds
            member = await self.bot.fetch_user(user_id)
            user_time = round(time.time() - self.bot.check_up_times[user_id], 0)
            #If the user has been clocked in for more than 30 minutes, we send the attention message         
            if user_time / 60 >= 30:
                asyncio.create_task(self.send_attention_message(member, user_id))
            #If the user has been clocked in for less than 30 minutes, we return
            else:
                return


class start(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.dm_only()
    @commands.is_owner()
    async def setup(self, ctx):
        channel = self.bot.get_channel(CLOCKING_CHANNEL_ID)

        embed = discord.Embed(
            title="Possibility Management",
            description=":stopwatch: - Clock In \n\n:alarm_clock: - Clock Out"
        )

        view = ClockView(self.bot)
        await channel.send(embed=embed, view=view)
        await ctx.author.send("Setup Complete")


async def setup(bot):
    await bot.add_cog(start(bot))