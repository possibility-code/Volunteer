import discord
import time
import sqlite3
import datetime
from clocking_helpers.work_profile import work_profile
from reader import MAIN_SERVER, TEAM_SERVER, FRONTLINES_SERVER, POSTGRESQL_URI_CONNECTION_STRING
import asyncpg

"""
This function is used to clock out a user without sending any error messages or confirmation messages
This is used when users need to be clocked out at midnight, for being AFK, or for other reasons
"""
async def clock_out_user(bot, user_id):
    main_server = bot.get_guild(MAIN_SERVER)
    team_server = bot.get_guild(TEAM_SERVER)
    frontlines_server = bot.get_guild(FRONTLINES_SERVER)
    member_main = main_server.get_member(user_id)
    member_team = team_server.get_member(user_id)
    try:
        member_frontlines = frontlines_server.get_member(user_id)
    except:
        pass
# PERFORM CLOCK OUT ACTIVITIES, BECAUSE THEY DIDNT RESPOND
    try:
        if not bot.clocked_in_users[user_id]:
            return
    except KeyError:
        return
    # Restores the users name to their original nickname, or just their basic discord name
    if user_id in bot.user_nicks:
        try:
            try:
                await member_main.edit(nick=f"{bot.user_nicks[user_id]}")
            except:
                pass
            try:
                await member_team.edit(nick=f"{bot.user_nicks[user_id]}")
            except:
                pass
            try:
                await member_frontlines.edit(nick=f"{bot.user_nicks[user_id]}")
            except:
                pass
            #If the user had their nick stored, delete it
            del bot.user_nicks[user_id]

        except discord.errors.Forbidden:
            pass      
    # Try/Except to handle errors that would occur if the user is above the bot
    elif user_id not in bot.user_nicks:
        try:
            if user_id not in bot.user_nicks:
                try:
                    await member_main.edit(nick=None)
                except:
                    pass
                try:
                    await member_team.edit(nick=None)
                except:
                    pass
                try:
                    await member_frontlines.edit(nick=None)
                except:
                    pass

        except discord.errors.Forbidden:
            pass
    # Remove work profile roles
    await work_profile(bot, user_id, "remove")
    # Calc the time that the user has been clocked in for (in seconds)
    add_time = round(time.time() - bot.clocked_in_users[user_id], 0)
    # Add the time to the DB 
    try:
        await bot.db.execute("INSERT INTO times (user_id, date, time) VALUES (?,?,?)", (user_id, datetime.date.today(), add_time))
        await bot.db.commit()
    except sqlite3.IntegrityError:
        await bot.db.execute("UPDATE times SET time = time + ? WHERE user_id = ?", (add_time, user_id))
        await bot.db.commit()  
    # Delete the clock out time for the user
    del bot.clocked_in_users[user_id]
    del bot.check_up_times[user_id]
    try:
        del bot.in_progress[user_id]
    except KeyError:
        return

    # Delete the user from the PostgreSQL DB
    vol_conn = await asyncpg.connect(POSTGRESQL_URI_CONNECTION_STRING)
    await vol_conn.execute("DELETE FROM clocked_in_users WHERE user_id = $1", user_id)
    await vol_conn.close()