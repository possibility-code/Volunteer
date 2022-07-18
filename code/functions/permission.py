import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
import sqlite3

class permission(commands.GroupCog, name="permission"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    async def check_perms(self, user_id, group_name):
        # Get the all of the group names from the users entry in the database
        async with self.bot.db.execute("SELECT group_name FROM permissions WHERE user_id = ?", (user_id,)) as cursor:
            # Fetch all the data and string them together
            data = await cursor.fetchall()
            data = ''.join(map(str, data))
        # If the group name is in the data, return True
        if group_name in data:
            return True
        # Else, return False
        else:
            return False

    @app_commands.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="Member that you want to add a permission group to")
    @app_commands.describe(group="Group of commands to add to the user")
    async def add(self, interaction: discord.Interaction, member: discord.Member, group: Literal['suffix', 'userdata', 'workprofile']):
        "Adds a permission group to a user"
        # Try to insert the data into the database and send the success message
        try:
            await self.bot.db.execute("INSERT INTO permissions (user_id, group_name) VALUES (?,?)", (member.id, group))
            await self.bot.db.commit()
            embed = discord.Embed(
                title = "Permission Added",
                description = f"{member.mention} has been given the `{group}` permission group",
                color = member.color
            )
            await interaction.response.send_message(embed=embed)
        # If the data already exists, send the error message
        except sqlite3.IntegrityError:
            embed = discord.Embed(
                title = "User Already has Permission Group",
                description = f"{member.mention} already has the `{group}` permission group",
                color = discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="The member whose permissions you want to view.")
    async def view(self, interaction: discord.Interaction, member: discord.Member):
        "View all of the permission groups the user has access to"
        # Get the data from the database
        async with self.bot.db.execute("SELECT group_name FROM permissions WHERE user_id = ?", (member.id,)) as cursor:
            data = await cursor.fetchall()
        # If there is data, add the group name for each entry and then send the embed
        if data:
            embed = discord.Embed(
                title = "Permissions",
                description = f"{member.mention} has permissions to the following commands:\n\n",
                color = member.color
            )
            for entry in data:
                group_name = entry[0]
                embed.description += f"**{group_name}**\n"

            await interaction.response.send_message(embed=embed)
        # Else, send the error message
        else:
            embed = discord.Embed(
                title = "User Has No Permissions",
                description = f"{member.mention} does not have permission to any command groups",
                color = discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="Member that you want to remove a permission group from")
    @app_commands.describe(group="Group of commands to remove from the user")
    async def delete(self, interaction: discord.Interaction, member: discord.Member, group: Literal['suffix', 'userdata', 'workprofile']):
        """Removes a permission group from a user"""
        # Delete the data from the database, and send the success message
        # If the data doesn't exist, its okay, it just deleted nothing, so just send the success message anyways
        await self.bot.db.execute("DELETE FROM permissions WHERE user_id = ? AND group_name = ?", (member.id, group))
        await self.bot.db.commit()
        embed = discord.Embed(
            title = "Permission Removed",
            description = f"`{group}` permission group has been removed from {member.mention}",
            color = member.color
        )
        await interaction.response.send_message(embed=embed)



async def setup(bot):
    await bot.add_cog(permission(bot))