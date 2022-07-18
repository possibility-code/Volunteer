from reader import TEAM_SERVER

"""
This is used to get the users suffix based on their highest volunteer role
"""
async def get_nickname(self, user_id):
    # Get the roles from the database in order to check them against the users roles
    async with self.bot.db.execute("SELECT role_id FROM role_suffix") as cursor:
        roles = [row[0] for row in await cursor.fetchall()]

    team_server = self.bot.get_guild(TEAM_SERVER)
    member_team = team_server.get_member(user_id)
    # Grab the users roles in order from low to high, and create a new list for only ids
    low_to_high = member_team.roles
    id_only = []
    # Check the ids from the user to the DB ids and append matching ids to the id_only list
    for role in low_to_high:
        if role.id in roles:
            id_only.append(role.id)
    # Reverse list in order to rank roles from highest to lowest
    id_only.reverse()

    # Pull the first role id, which is the highest role
    nick_role_id = id_only[0]
    
    # Use the role id to retrive the suffix associated with it
    async with self.bot.db.execute("SELECT suffix FROM role_suffix WHERE role_id = ?", (nick_role_id,)) as cursor:
        data = await cursor.fetchone()
        nick_suffix = data[0]

    # Return the suffix
    return nick_suffix