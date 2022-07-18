from reader import MAIN_SERVER, TEAM_SERVER, FRONTLINES_SERVER

"""
This is used to retrieve the work profile information for a specific user
"""
async def work_profile(bot, user_id, decision):
    main_server = bot.get_guild(MAIN_SERVER)
    team_server = bot.get_guild(TEAM_SERVER)
    frontlines_server = bot.get_guild(FRONTLINES_SERVER)
    if decision == "add":
        # Pull the users work profile roles
        async with bot.db.execute("SELECT role_id, guild_id FROM workprofile WHERE user_id = ?", (user_id,)) as cursor:
            # For each entry, define the role id
            async for entry in cursor:
                role_id, guild_id = entry
                # Try to add their roles in the main server
                if guild_id == MAIN_SERVER:
                    try:
                        member = main_server.get_member(user_id)
                        role = main_server.get_role(role_id)
                        await member.add_roles(role)
                    # Return on error
                    except AttributeError:
                        return
                # Try to add their roles in the team server   
                elif guild_id == TEAM_SERVER:
                    try:
                        member = team_server.get_member(user_id)
                        role = team_server.get_role(role_id)
                        await member.add_roles(role)
                    # Return on error
                    except AttributeError:
                        return
                # Try to add their roles in the frontlines server   
                elif guild_id == FRONTLINES_SERVER:
                    try:
                        member = frontlines_server.get_member(user_id)
                        role = frontlines_server.get_role(role_id)
                        await member.add_roles(role)
                    # Return on error
                    except:
                        return


    elif decision == "remove":
        # Pull the users work profile roles
        async with bot.db.execute("SELECT role_id, guild_id FROM workprofile WHERE user_id = ?", (user_id,)) as cursor:
            # For each entry, define the role id
            async for entry in cursor:
                role_id, guild_id = entry
                # Try to add their roles in the main server
                if guild_id == MAIN_SERVER:
                    try:
                        member = main_server.get_member(user_id)
                        role = main_server.get_role(role_id)
                        await member.remove_roles(role)
                    # Return on error
                    except AttributeError:
                        return
                # Try to add their roles in the team server   
                elif guild_id == TEAM_SERVER:
                    try:
                        member = team_server.get_member(user_id)
                        role = team_server.get_role(role_id)
                        await member.remove_roles(role)
                    # Return on error
                    except AttributeError:
                        return
                # Try to add their roles in the frontlines server   
                elif guild_id == FRONTLINES_SERVER:
                    try:
                        member = frontlines_server.get_member(user_id)
                        role = frontlines_server.get_role(role_id)
                        await member.remove_roles(role)
                    # Return on error
                    except:
                        return

