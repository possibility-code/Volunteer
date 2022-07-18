import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from functions.permission import permission

class manage_roles(commands.GroupCog, name="suffix"):
    def __init__(self, bot):
        self.bot = bot
        self.perms = permission(self.bot)
        super().__init__()


    @app_commands.command()
    @app_commands.describe(role="Role you would like to add a suffix to")
    @app_commands.describe(suffix="Suffix assocaited with the chosen role")
    async def add(self, interaction: discord.Interaction, role: discord.Role, suffix: str):
        "Add a suffix that will be associated with a specific role"
        # Check that the user has permission to add a suffix
        if await self.perms.check_perms(interaction.user.id, "suffix"):
            try:
                # Add the role and suffix to the DB, then send a message to tell the user it worked
                await self.bot.db.execute("INSERT INTO role_suffix (role_id, suffix) VALUES (?,?)", (role.id, suffix))
                await self.bot.db.commit()
                embed = discord.Embed(
                    title = "Role and Suffix Added",
                    description = f"`{suffix}` has been added as the suffix associated with {role.mention}",
                    color = role.color
                )
                return await interaction.response.send_message(embed=embed)

            except sqlite3.IntegrityError:
                # If the role is already defined in the DB, send a message letting the user know
                embed = discord.Embed(
                    title = "Suffix Already Defined",
                    description = f"{role.mention} already has a suffix assigned to it. If you would like to edit this suffix, use `/suffix edit`.",
                    color = discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        # Else, send a message letting the user know they do not have permission
        else:
            embed = discord.Embed(
                title = "Missing Permissions",
                description = "You do not have permission to use the `suffix` group of commands! An administrator must give you permission using the `/permission` command.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.describe(role="Role whose suffix you would like to edit")
    @app_commands.describe(suffix="The new suffix you would like to be assoicated with this role")
    async def edit(self, interaction: discord.Interaction, role: discord.Role, suffix: str):
        "Edit the suffix that is currently associated with a role"
        # Check that the user has permission to edit a suffix
        if await self.perms.check_perms(interaction.user.id, "suffix"):
            # Pulls data from role_suffix in order to check that the role is already in the DB
            async with self.bot.db.execute("SELECT role_id FROM role_suffix") as cursor:
                roles = [row[0] for row in await cursor.fetchall()]
            # Check the data to see if the role is within the database
            try:
                # If the role is in the database, update the role
                if role.id in roles:
                    await self.bot.db.execute("UPDATE role_suffix SET suffix = ? WHERE role_id = ?", (suffix, role.id))
                    await self.bot.db.commit()
                    embed = discord.Embed(
                        title="Role Edited",
                        description=f"{role.mention} has had its suffix updated to `{suffix}`",
                        color = role.color
                    )
                    return await interaction.response.send_message(embed=embed)

                # Elif the role is not in the database, alert the user to add the role using /addrole
                elif role.id not in roles:
                    embed = discord.Embed(
                        title = "Suffix Not Yet Added",
                        description = f"{role.mention} does not yet has a suffix associated with it, therefore I cannot edit this role. To add this role, use `/suffix add`",
                        color = discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)

            # If NOTHING at all is in the database, it throws a TypeError, so just send the same message alerting the user
            except TypeError:
                embed = discord.Embed(
                    title = "Suffix Not Yet Added",
                    description = f"{role.mention} does not yet has a suffix associated with it, therefore I cannot edit this role. To add this role, use `/suffix add`",
                    color = discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        # Else, send a message letting the user know they do not have permission
        else:
            embed = discord.Embed(
                title = "Missing Permissions",
                description = "You do not have permission to use the `suffix` group of commands! An administrator must give you permission using the `/permission` command.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.describe(role="Role you whose suffix you would like to delete")
    async def delete(self, interaction: discord.Interaction, role: discord.Role):
        "Delete a suffix that is assoicated with a role"
        # Check that the user has permission to delete a suffix
        if await self.perms.check_perms(interaction.user.id, "suffix"):
            # Deletes the data from the role_suffix table in the DB
            # If rhe role is not in the DB, it just deletes nothing, so we 
            # can just send the success message anyways
            await self.bot.db.execute("DELETE FROM role_suffix WHERE role_id = ?", (role.id,))
            await self.bot.db.commit()
            embed = discord.Embed(
                title="Suffix Deleted",
                description=f"The suffix associated with {role.mention} has been deleted from the database",
                color = role.color
            )
            return await interaction.response.send_message(embed=embed)
        # Else, send a message letting the user know they do not have permission
        else:
            embed = discord.Embed(
                title = "Missing Permissions",
                description = "You do not have permission to use the `suffix` group of commands! An administrator must give you permission using the `/permission` command.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            

async def setup(bot):
    await bot.add_cog(manage_roles(bot))