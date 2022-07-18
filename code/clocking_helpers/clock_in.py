import discord
import time
from reader import MAIN_SERVER, TEAM_SERVER, FRONTLINES_SERVER, POSTGRESQL_URI_CONNECTION_STRING
from clocking_helpers.work_profile import work_profile
from clocking_helpers.get_nickname import get_nickname
import asyncpg
import datetime

class TimerError(Exception):
    """Used to report errors within the clock in/out functions"""


def get_hours(time_in_seconds):
    hours = round(time_in_seconds // 3600, 0)
    return hours


"""
This is the function used to clock in users while also sending error/confirmation messages
This function is called when the user clocks themself in through the button
"""
async def clock_in(self, interaction: discord.Interaction):
    member = interaction.user
    main_server = self.bot.get_guild(MAIN_SERVER)
    team_server = self.bot.get_guild(TEAM_SERVER)
    frontlines_server = self.bot.get_guild(FRONTLINES_SERVER)
    member_main = main_server.get_member(interaction.user.id)
    member_team = team_server.get_member(interaction.user.id)
    try:
        member_frontlines = frontlines_server.get_member(interaction.user.id)
    except:
        pass
    # Check that the user is not already clocked in, if they are, send a different message
    if interaction.user.id in self.bot.clocked_in_users:
        return await interaction.response.send_message("You are already clocked in!", ephemeral=True)

    # Make sure the user is not on LOA
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
 
    # Grab the users `days` data to make sure they are not overdue for a checkup
    async with self.bot.db.execute("SELECT days FROM need_checkup WHERE user_id = ?", (member.id,)) as cursor:
        days = await cursor.fetchone()
        try:
            days = days[0]
            # If they are over 21 days without a checkup, alert them and return
            if int(days) >= 21:
                embed = discord.Embed(
                    title = "In Need of Checkup",
                    description = f"You are overdue for a checkup, I cannot clock you in until an HR members performs your checkup. Checkups are needed every 21 days, you last checkup was {days} days ago.",
                    color = discord.Color.red()
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)
        except TypeError:
            pass

    # Grab the `in_progress` data
    async with self.bot.db.execute("SELECT user_id FROM in_progress") as cursor:
        data = [row[0] for row in await cursor.fetchall()]
    # If the member is in the middle of a checkup, alert them and return
    if member.id in data:
        embed = discord.Embed(
            title = "Checkup in Progress",
            description = "You have a checkup that is currently in progress, therefore I cannot clock you in. Try again later after getting your checkup finished.",
            color = discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    # Add work profile roles
    await work_profile(self.bot, interaction.user.id, "add")

    # Gets the nickname/suffix that will need to be added to the user
    try:
        nickname = await get_nickname(self, interaction.user.id)

    # If the user doesnt have a role that matches with any roles in the DB, it throws IndexError
    except IndexError:
        embed = discord.Embed(
            title = "Needed Roles Missing",
            description = "You are missing one of the required support roles as defined by the database! If you believe this is an error, please make sure that all support roles have been added using the `/suffix add` command.",
            color = discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    # Make sure user DMs are opened
    try:
        # Define variables, and calculate the dates for today, yesteraday, and one week ago
        today = datetime.date.today()
        first_of_week = datetime.date.today().weekday() + 1
        first_of_month = int(datetime.date.today().day)
        # Create the finals dictionary, so that all of the correct date can be pulled
        finals = {}
        # Retrieve all of the necessary data (time, date) from the 'times' table where the user_id is the same
        async with self.bot.db.execute("SELECT time, date FROM times WHERE user_id = ?", (interaction.user.id,)) as cursor:
            # For every entry in the table, add date:time to the 'finals' dict
            async for entry in cursor:
                time_, date = entry
                finals[date] = time_

        # If the user has data, sum all of the time entries and convert it
        total_time = sum(tuple(finals.values()))

        # For every day in the past week, we use first_of_week to calculate the correct date, get
        # the time entry for that day from the finals dict, and add it to week_time
        week_time = 0
        for i in range(1, first_of_week):
            day = today - datetime.timedelta(days=i)
            try:
                week_time += finals.get(f'{day}')
            except TypeError:
                pass
        # For every day in the past month, we use first_of_month to calculate the correct date, get
        # the time entry for that day from the finals dict, and add it to month_time
        month_time = 0
        for i in range(1, first_of_month):
            day = today - datetime.timedelta(days=i)
            try:
                month_time += finals.get(f'{day}')
            except TypeError:
                pass
        # Get the amount of time in hours for week_time, month_time, total_time
        week_time = get_hours(week_time)
        month_time = get_hours(month_time)
        total_time = get_hours(total_time)
        # Get the amount of weekly hour goal completions the user has ever had
        async with self.bot.db.execute("SELECT count FROM weekly_completions WHERE user_id = ?", (interaction.user.id,)) as cursor:
            completions = await cursor.fetchone()
            # If the user has past completions, get the amount of completions they've had
            if completions:
                completions = completions[0]
            # Else, assign the value to 0, so that we don't get 'None'
            else:
                completions = 0
        # Create the embed to confirm that user has been clocked in
        confirm_embed = discord.Embed(
            title="Possibility Management",
            description="You have been clocked in, this message was to make sure that your DMs are open."
        )
        # Create the embed to show the user their time from completing their goal this week
        recommendation_embed = discord.Embed(
            title="Recommendation",
            description="This is only a recommendation to see our targets for most volunteers."
        )
        # If they have completed their weekly goal, add the field to say its completed
        if week_time >= 8:
            recommendation_embed.add_field(name="Weekly 8 Hours Goal", value=f"``` COMPLETED ```", inline=False)
        # Else, add an embed field to show that the amount of hours left before they complete their goal
        else:
            recommendation_embed.add_field(name="Weekly 8 Hours Goal", value=f"```{8-week_time:,} hours away from meeting the goal```", inline=False)
        # If their weekly hours are above 16, add the warning to tell them to think about taking a break
        if week_time >= 16:
            recommendation_embed.add_field(name="Warnings", value=f"```You have reached more than 16 hours this week; we recommend taking more time for your mental health and returning next week or try to take more breaks. Thanks, the Board Team.```", inline=False)
        # Create the embed to show the user their statistics over the past week, month, and in total
        statistics_embed = discord.Embed(
            title="Your Statistics"
        )
        statistics_embed.add_field(name="Total Hours", value=f"```{total_time:,}```", inline=True)
        statistics_embed.add_field(name="Hours This Month", value=f"```{month_time:,}```", inline=True)
        statistics_embed.add_field(name="Hours This Week", value=f"```{week_time:,}```", inline=True)
        statistics_embed.add_field(name="Amount of Weekly Completion Goals Met", value=f"```{completions:,}```", inline=False)
        # Send the embed to the user
        await member.send(embed=confirm_embed)
        await member.send(embed=recommendation_embed)
        await member.send(embed=statistics_embed)
    # Except, Foribidden, means the user has their DMs closed, so return alert them
    except discord.errors.Forbidden:
        return await interaction.response.send_message("You do not have your DMs open, therefore you cannot be clocked in. Try again after opening your DMs.", ephemeral=True)
    # Change nickname to add suffix - also store originalnickname in dict so that there name is 
    # restored once they clock out
    try:
        if member_team.nick:
            self.bot.user_nicks[interaction.user.id] = member_team.nick
            try: # Try to edit the nickname for the main server
                await member_main.edit(nick=f"{member_team.nick} ♾️ {nickname}")
            except: # If there is an error, just pass it, we catch them in the first try block
                pass

            try: # Try to edit the nickname for the team server
                await member_team.edit(nick=f"{member_team.nick} ♾️ {nickname}")
            except: # If there is an error, just pass it, we catch them in the first try block
                pass

            try: # Try to edit the nickname for the frontlines server
                await member_frontlines.edit(nick=f"{member_frontlines.nick} ♾️ {nickname}")
            except: # If there is an error, just pass it, we catch them in the first try block
                pass

        elif not member.nick:
            try: # Try to edit the nickname for the main server
                await member_main.edit(nick=f"{str(member.name)} ♾️ {nickname}")
            except: # If there is an error, just pass it, we catch them in the first try block
                pass

            try: # Try to edit the nickname for the team server
                await member_team.edit(nick=f"{str(member.name)} ♾️ {nickname}")
            except: # If there is an error, just pass it, we catch them in the first try block
                pass

            try: # Try to edit the nickname for the frontlines server
                await member_frontlines.edit(nick=f"{str(member.name)} ♾️ {nickname}")
            except: # If there is an error, just pass it, we catch them in the first try block
                pass

    # If the user is above the bot, its cant change the nick, so clock them in but also alert them
    except discord.errors.Forbidden:
        self.bot.clocked_in_users[interaction.user.id] = time.time()
        self.bot.check_up_times[interaction.user.id] = time.time()
        return await interaction.response.send_message("You have been clocked in. But your nickname wasn't changed as you are above the bot.", ephemeral=True)
    # If the nickname is over 32 characters, alert them and return after clocking them in
    except discord.errors.HTTPException:
        self.bot.clocked_in_users[interaction.user.id] = time.time()
        self.bot.check_up_times[interaction.user.id] = time.time()
        return await interaction.response.send_message("You have been clocked in. But your nickname wasn't changed as it is too long.", ephemeral=True)
        
    # Store the time in the dict in order to keep track of how long someone has been clocked in
    self.bot.clocked_in_users[interaction.user.id] = time.time()
    self.bot.check_up_times[interaction.user.id] = time.time()

    # Add the user to the PostgreSQL DB so that it can be read from the FrontLines bot
    vol_conn = await asyncpg.connect(POSTGRESQL_URI_CONNECTION_STRING)
    try:
        await vol_conn.execute("INSERT INTO clocked_in_users (user_id) VALUES ($1)", interaction.user.id)
    except:
        pass
    await vol_conn.close()

    await interaction.response.send_message("You are clocked in!", ephemeral=True)