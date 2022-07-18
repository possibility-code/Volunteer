import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import datetime

class manage_roles(commands.GroupCog, name="hrrole"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()


    @tasks.loop(seconds=10)
    async def delete_loa(self):
        await self.bot.wait_until_ready()
        # Grab all of the users that currently have a checkup in progress
        async with self.bot.db.execute("SELECT user_id, end_date FROM on_loa") as cursor:
            async for entry in cursor:
                # If the end date is in the past, delete the entry
                user_id, end_date = entry
                if end_date <= datetime.datetime.now():
                    await self.bot.db.execute("DELETE FROM on_loa WHERE user_id = ?", user_id)
                    await self.bot.db.commit()
                    # Get the user
                    user = self.bot.get_user(user_id)
                    # Send a message to the user
                    await user.send(f"Your leave of absence has ended, you can now once again clock in.")
                # Else, do nothing
                else:
                    return


    @app_commands.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="Role which you would like to define as an HR Role within the database")
    async def add(self, interaction: discord.Interaction, role: discord.Role):
        "Add a role to the database that defines HR members. Example role name would be: HR Staff"
        try:
            # Add the role to the DB, then send a message to tell the user it worked
            await self.bot.db.execute("INSERT INTO hr_roles (role_id) VALUES (?)", (role.id,))
            await self.bot.db.commit()
            embed = discord.Embed(
                title = "HR Role added",
                description = f"{role.mention} has been added as an HR Role in the database.",
                color = role.color
            )
            return await interaction.response.send_message(embed=embed)

        # If the role is already defiend in the DB, send a message letting the user know
        except sqlite3.IntegrityError:
            embed = discord.Embed(
                title = "Role Already Defined",
                description = f"{role.mention} has already been defined as an HR role within the database.",
                color = discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="Role that you would like to remove as an HR role from the database")
    async def delete(self, interaction: discord.Interaction, role: discord.Role):
        "Delete the role from the database that was defined for HR members"
        # Delete the role from the DB, then send a message to tell the user it worked
        # If the role isn't currently in the DB, it just deletes nothing, so 
        # we can just send a success message anyways
        await self.bot.db.execute("DELETE FROM hr_roles WHERE role_id = ?", (role.id,))
        await self.bot.db.commit()
        embed = discord.Embed(
            title="Role Deleted",
            description=f"The role {role.mention} has been deleted from the database",
            color = role.color
        )
        return await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(manage_roles(bot))