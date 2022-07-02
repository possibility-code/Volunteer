import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from reader import MAIN_SERVER, TEAM_SERVER

class non_work_profile(commands.Cog, app_commands.Group, name="nonworkprofile"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()


    @app_commands.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="Member whose non-work profile you would like to add a rank to")
    @app_commands.describe(role="Role that you would like to add to the members non-work profile")
    async def add(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        "Add a rank to the users non-work profile"
        #Make sure the role is not higher than the bots highest role, therefore the bot cant add it to people
        if interaction.guild.me.top_role < role:
            embed = discord.Embed(
                title = "Role Too High",
                description = f"{role.mention} is too high of a role for me to be able to add to people, therefore it cannot be added to {member.mention}'s non-work profile. If you would like to add this role, first move my top role - {interaction.guild.me.top_role} - to be above {role.mention}.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        #Make sure the role isnt `@everyone` because you cant add or remove this role
        elif role == discord.utils.get(interaction.guild.roles, name="@everyone"):
            embed = discord.Embed(
                title = "Role @everyone Not Allowed",
                description = f"{role.mention} is not allowed to be added to the non-work profile, please choose a different role.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            #Add the user and role IDs to the database in order to add a the role to the users profile
            await self.bot.db.execute("INSERT INTO nonworkprofile (user_id, role_id) VALUES (?,?)", (member.id, role.id))
            await self.bot.db.commit()
            #Create and send the embed
            embed = discord.Embed(
                title = f"Role Added To Non-Work Profile",
                description = f"{role.mention} has been added to {member.mention}'s non-work profile.",
                color = role.color
            )
            return await interaction.response.send_message(embed=embed)

        except sqlite3.IntegrityError:
            #If the role is already defiend in the DB, send a message letting the user know
            embed = discord.Embed(
                title = "User Already Has Role",
                description = f"{member.mention} already has {role.mention} in their non-work profile.",
                color = discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="Member whose non-work profile you would like to remove a role from")
    @app_commands.describe(role="Role that you would like to be removed from the members non-work profile")
    async def delete(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        "Delete a role from a users non-work profile"
        #Pulls data from workprofile in order to make sure that the role entered by the user is not within the database already
        async with self.bot.db.execute("SELECT role_id FROM nonworkprofile WHERE user_id = ?", (member.id,)) as cursor:
            roles = [row[0] for row in await cursor.fetchall()]

        #Check the data to see if the role is within the database
        try:
            #If the role is in the database, delete the role
            if role.id in roles:
                await self.bot.db.execute("DELETE FROM nonworkprofile WHERE role_id = ? AND user_id = ?", (role.id, member.id))
                await self.bot.db.commit()
                embed = discord.Embed(
                    title=f"Role Deleted From Non-Work Profile",
                    description=f"{role.mention} has been removed from {member.mention}'s non-work profile.",
                    color = role.color
                )
                return await interaction.response.send_message(embed=embed)

            #Elif the role is not in the database, alert the user that the role is already not in the database
            elif role.id not in roles:
                embed = discord.Embed(
                    title = "Role Not Yet Added",
                    description = f"{member.mention} does not yet have the role, {role.mention}, therefore I cannot delete it.",
                    color = discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        #If NOTHING at all is in the database, it throws a TypeError, so just send the same message alerting the user
        except TypeError:
            embed = discord.Embed(
                title = "Role Not Yet Added",
                description = f"{member.mention} does not yet have the role, {role.mention}, therefore I cannot delete it.",
                color = discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.describe(member="Member whose non-work profile you would like to view")
    async def view(self, interaction: discord.Interaction, member: discord.Member):
        "View a users non-work profile"
        #Try to retrieve both servers, makes sure the bot wasnt kicked or the server deleted
        try:
            main_server = await self.bot.fetch_guild(MAIN_SERVER)
            team_server = await self.bot.fetch_guild(TEAM_SERVER)
        except:
            #If this fails, thats bad, so tell them to contact the developer
            return await interaction.response.send_message("ERROR, talk to the developer!", ephemeral=True)
        #Create the embed, and set the description to be empty
        embed = discord.Embed(
            title = f"{member}'s Non-Work Profile",
            description = "",
            color = member.color
        )
        #Select all of the roles from the nonworkprofile table where the user id and guild id match
        async with self.bot.db.execute("SELECT role_id FROM nonworkprofile WHERE user_id = ?", (member.id,)) as cursor:
            data = await cursor.fetchall()
            #If there is data, continue
            if data:
                #For every entry, attempt to add the role to the embed
                for entry in data:
                    role = entry[0]
                    #If the role is in the main server - add it to the embed
                    if main_server.get_role(role) != None:
                            embed.description += (f"`{main_server.get_role(role)}` - Main Server\n")
                    #Elif the role is in the team server - add it to the embed
                    elif team_server.get_role(role) != None:
                            embed.description += (f"`{team_server.get_role(role)}` - Team Server\n")
                    #Else, means the role is not in either server (prob deleted) so remove it from the table
                    else:
                        await self.bot.db.execute("DELETE FROM nonworkprofile WHERE user_id = ? AND role_id = ?", (member.id, role))
                        await self.bot.db.commit()
                        embed = discord.Embed(
                            title = "User Has no Roles",
                            description = f"{member.mention} does not have any roles in their non-work profile.",
                            color = discord.Color.red()
                        )
                        return await interaction.response.send_message(embed=embed, ephemeral=True)
            
                await interaction.response.send_message(embed=embed)
            #Else is there is not data, alert the user that there is no roles for that users work profile
            elif not data:
                embed = discord.Embed(
                    title = "User Has no Roles",
                    description = f"{member.mention} does not have any roles in their non-work profile.",
                    color = discord.Color.red()
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(non_work_profile(bot))