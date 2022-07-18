import discord
import datetime
import time
import sqlite3
from reader import MAIN_SERVER, TEAM_SERVER, FRONTLINES_SERVER, POSTGRESQL_URI_CONNECTION_STRING
from clocking_helpers.work_profile import work_profile
import asyncpg

"""
Clock out the user while also sending error/confirmation messages
This function is used for when the user manually clocks themself out with the button
"""
async def clock_out(self, interaction: discord.Interaction):
    main_server = self.bot.get_guild(MAIN_SERVER)
    team_server = self.bot.get_guild(TEAM_SERVER)
    frontlines_server = self.bot.get_guild(FRONTLINES_SERVER)
    member_main = main_server.get_member(interaction.user.id)
    member_team = team_server.get_member(interaction.user.id)
    try:
        member_frontlines = frontlines_server.get_member(interaction.user.id)
    except:
        pass
    # Check that the user is not already clocked out, if they are, send a different message
    try:
        if not self.bot.clocked_in_users[interaction.user.id]:
            return await interaction.response.send_message("You are already clocked out!", ephemeral=True)
    except KeyError:
        return await interaction.response.send_message("You are already clocked out!", ephemeral=True)

    # Restores the users name to their original nickname, or just their basic discord name
    if interaction.user.id in self.bot.user_nicks:
        try:
            try:
                await member_main.edit(nick=f"{self.bot.user_nicks[interaction.user.id]}")
            except:
                pass
            try:
                await member_team.edit(nick=f"{self.bot.user_nicks[interaction.user.id]}")
            except:
                pass
            try:
                await member_frontlines.edit(nick=f"{self.bot.user_nicks[interaction.user.id]}")
            except:
                pass
            #If the user had their nick stored, delete it
            del self.bot.user_nicks[interaction.user.id]

        except discord.errors.Forbidden:
            pass      
    # Try/Except to handle errors that would occur if the user is above the bot
    elif interaction.user.id not in self.bot.user_nicks:
        try:
            if interaction.user.id not in self.bot.user_nicks:
                try:
                    await member_main.edit(nick=member_main.name)
                except:
                    pass
                try:
                    await member_team.edit(nick=member_team.name)
                except:
                    pass
                try:
                    await member_frontlines.edit(nick=member_frontlines.name)
                except:
                    pass

        except discord.errors.Forbidden:
            pass

    # Remove work profile roles 
    await work_profile(self.bot, interaction.user.id, "remove")

    # Calc the time that the user has been clocked in for (in seconds)
    add_time = round(time.time() - self.bot.clocked_in_users[interaction.user.id], 0)

    # Add the time to the DB 
    try:
        await self.bot.db.execute("INSERT INTO times (user_id, date, time) VALUES (?,?,?)", (interaction.user.id, datetime.date.today(), add_time))
        await self.bot.db.commit()
    except sqlite3.IntegrityError:
        await self.bot.db.execute("UPDATE times SET time = time + ? WHERE user_id = ?", (add_time, interaction.user.id))
        await self.bot.db.commit()  


    # Delete the clock out time for the user
    del self.bot.clocked_in_users[interaction.user.id]
    del self.bot.check_up_times[interaction.user.id]
    try:
        del self.bot.in_progress[interaction.user.id]
    except KeyError:
        pass

    # Delete the user from the PostgreSQL DB
    vol_conn = await asyncpg.connect(POSTGRESQL_URI_CONNECTION_STRING)
    await vol_conn.execute("DELETE FROM clocked_in_users WHERE user_id = $1", interaction.user.id)
    await vol_conn.close()

    await interaction.response.send_message("I have clocked you out!", ephemeral=True)