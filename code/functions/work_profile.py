import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from reader import MAIN_SERVER, TEAM_SERVER, FRONTLINES_SERVER
from functions.permission import permission

class work_profile(commands.GroupCog, name="workprofile"):
    def __init__(self, bot):
        self.bot = bot
        self.perms = permission(self.bot)
        super().__init__()


    @app_commands.command()
    @app_commands.describe(member="Member whose work profile you would like to add a rank to")
    @app_commands.describe(role="Role that you would like to add to the members work profile")
    async def add(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        "Add a rank to the users work profile"
        # Check that the user has permission to add a role
        if await self.perms.check_perms(interaction.user.id, "workprofile"):
            # Make sure the role provided is not higher than the bots highest role, because
            # if it is, the bot cannot add/remove it from people
            if interaction.guild.me.top_role < role:
                embed = discord.Embed(
                    title = "Role Too High",
                    description = f"{role.mention} is too high of a role for me to be able to add to people, therefore it cannot be added to {member.mention}'s work profile. If you would like to add this role, first move my top role - {interaction.guild.me.top_role} - to be above {role.mention}.",
                    color = discord.Color.red()
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            # Make sure the role isnt '@everyone' because bots cant add or remove this role
            elif role == discord.utils.get(interaction.guild.roles, name="@everyone"):
                embed = discord.Embed(
                    title = "Role @everyone Not Allowed",
                    description = f"{role.mention} is not allowed to be added to the work profile, please choose a different role.",
                    color = discord.Color.red()
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            try:
                # Add the user and role IDs to the database
                await self.bot.db.execute("INSERT INTO workprofile (user_id, role_id, guild_id) VALUES (?,?,?)", (member.id, role.id, interaction.guild.id))
                await self.bot.db.commit()
                # Create and send the embed
                embed = discord.Embed(
                    title = f"Role Added To Work Profile",
                    description = f"{role.mention} has been added to {member.mention}'s work profile.",
                    color = role.color
                )
                return await interaction.response.send_message(embed=embed)

            except sqlite3.IntegrityError:
                # If the role is already defiend in the DB, send a message letting the user know
                embed = discord.Embed(
                    title = "User Already Has Role",
                    description = f"{member.mention} already has {role.mention} in their work profile.",
                    color = discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        # Else, send a message letting the user know they do not have permission
        else:
            embed = discord.Embed(
                title = "Missing Permissions",
                description = "You do not have permission to use the `workprofile` group of commands! An administrator must give you permission using the `/permission` command.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.describe(member="Member whose work profile you would like to remove a role from")
    @app_commands.describe(role="Role that you would like to be removed from the members work profile")
    async def delete(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        "Delete a role from a users work profile"
        # Check that the user has permission to delete a role
        if await self.perms.check_perms(interaction.user.id, "workprofile"):
            # Delete the role and user IDs from the database
            # We don't need to add checks, because if the role isn't defined, it will just delete nothing
            await self.bot.db.execute("DELETE FROM workprofile WHERE role_id = ? AND user_id = ?", (role.id, member.id))
            await self.bot.db.commit()
            embed = discord.Embed(
                title=f"Role Deleted From Work Profile",
                description=f"{role.mention} has been removed from {member.mention}'s work profile.",
                color = role.color
            )
            return await interaction.response.send_message(embed=embed)
        # Else, send a message letting the user know they do not have permission
        else:
            embed = discord.Embed(
                title = "Missing Permissions",
                description = "You do not have permission to use the `workprofile` group of commands! An administrator must give you permission using the `/permission` command.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.describe(member="Member whose work profile you would like to see")
    async def view(self, interaction: discord.Interaction, member: discord.Member):
        "View a users work profile"
        # Check that the user has permission to view a users work profile
        if await self.perms.check_perms(interaction.user.id, "workprofile"):
            # Try to retrieve both servers - makes sure the bot wasnt kicked or the server deleted
            try:
                main_server = self.bot.get_guild(MAIN_SERVER)
                team_server = self.bot.get_guild(TEAM_SERVER)
                frontlines_server = self.bot.get_guild(FRONTLINES_SERVER)
            except:
                # If this fails, thats bad, so tell them to contact the developer
                return await interaction.response.send_message("ERROR, talk to the developer!", ephemeral=True)
            # Create the embed, and set the description to be empty
            embed = discord.Embed(
                title = f"{member}'s Work Profile",
                description = "",
                color = member.color
            )
            # Select all of the roles from the workprofile table where the user id and guild id match
            async with self.bot.db.execute("SELECT role_id FROM workprofile WHERE user_id = ?", (member.id,)) as cursor:
                data = await cursor.fetchall()
                # If there is data, continue
                if data:
                    #For every entry, attempt to add the role to the embed
                    for entry in data:
                        role = entry[0]
                        # If the role is in the main server - add it to the embed
                        if main_server.get_role(role) != None:
                                embed.description += (f"`{main_server.get_role(role)}` - Main Server\n")
                        # Elif the role is in the team server - add it to the embed
                        elif team_server.get_role(role) != None:
                                embed.description += (f"`{team_server.get_role(role)}` - Team Server\n")
                        # Elif the role is in the frontlines server - add it to the embed
                        elif frontlines_server.get_role(role) != None:
                                embed.description += (f"`{frontlines_server.get_role(role)}` - Frontlines Server\n")
                        #Else, means the role is not in either server (prob deleted) so remove it from the table
                        else:
                            await self.bot.db.execute("DELETE FROM workprofile WHERE user_id = ? AND role_id = ?", (member.id, role))
                            await self.bot.db.commit()

                    await interaction.response.send_message(embed=embed)
                # Else, send a message letting the author know that the user has no roles
                else:
                    embed = discord.Embed(
                        title = "User Has no Roles",
                        description = f"{member.mention} does not have any roles in their work profile.",
                        color = discord.Color.red()
                    )
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
        # Else, send a message letting the user know they do not have permission
        else:
            embed = discord.Embed(
                title = "Missing Permissions",
                description = "You do not have permission to use the `workprofile` group of commands! An administrator must give you permission using the `/permission` command.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(work_profile(bot))