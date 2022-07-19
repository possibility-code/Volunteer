import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime

class loa(commands.GroupCog, name="loa"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()


    async def check_hr_roles(self, interaction):
        # Retrieve all of the role IDs from the hr_roles table
        async with self.bot.db.execute("SELECT role_id FROM hr_roles") as cursor:
            roles = [row[0] for row in await cursor.fetchall()]

        # Define the authors roles 
        author_roles = interaction.user.roles

        # Check the ids from the author to the DB ids and return True is they have one of the roles else return False
        for role in author_roles:
            if role.id in roles:
                return True
        else:
            return False


    @app_commands.command()
    @app_commands.describe(member="Member who you would like to put on LOA")
    @app_commands.describe(duration="Amount of time (in days) to LOA this person. EX: 5")
    @app_commands.describe(reason="Reason for putting this member on LOA")
    async def add(self, interaction: discord.Interaction, member: discord.Member, duration: int, reason: str):
        "Add LOA to a member"
        # Check that the user has permission to add LOA
        if await self.check_hr_roles(interaction):
            today = datetime.date.today()
            # Calculate the specific date at which the LOA will end
            end_time = today + datetime.timedelta(days=duration)
            try:
                # Add and commit changes to the DB, then send a message
                await self.bot.db.execute("INSERT INTO on_loa (user_id, start_date, end_date, reason) VALUES (?,?,?,?)", (member.id, datetime.date.today(), end_time, reason))
                await self.bot.db.commit()

                await self.bot.db.execute("DELETE FROM need_checkup WHERE user_id = ?", (member.id,))
                await self.bot.db.commit()

                embed = discord.Embed(
                    title = f"{member} has been put on LOA!",
                    description = f"This member will be on LOA until {end_time}",
                    color = member.color
                )
                embed.add_field(name="Reason for LOA:", value=reason)
                return await interaction.response.send_message(embed=embed)

            # If member is already in the on_loa table, send a message alerting the user
            except sqlite3.IntegrityError:
                embed = discord.Embed(
                    title = "Member Already on LOA",
                    description = f"{member.mention} is already on LOA. If you would like to view their LOA report, please use `/loa view`",
                    color = discord.Color.red()
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Else, send a message letting the user know they do not have permission
        else:
            embed = discord.Embed(
                title = "Needed Roles Missing",
                description = "You are missing one of the required HR roles as defined by the database! If you believe this is an error, please make sure that all HR roles have been added using the `/hrrole add` command.",
                color = discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.describe(member="Member whose LOA report you would like to view")
    async def view(self, interaction: discord.Interaction, member: discord.Member):
        "View a members LOA report"
        # Check that the user has permission to view LOA
        if await self.check_hr_roles(interaction):
            async with self.bot.db.execute("SELECT start_date, end_date, reason FROM on_loa WHERE user_id = ?", (member.id,)) as cursor:
                # Go the the data and send a message showing the users LOA report
                async for entry in cursor:
                    start_date, end_date, reason = entry
                    embed = discord.Embed(
                        title = f"LOA report for {member}",
                        color = member.color
                    )

                    embed.add_field(name="Start date:", value=start_date)
                    embed.add_field(name="End date:", value=end_date)
                    embed.add_field(name="Reason:", value=reason, inline=False)

                    return await interaction.response.send_message(embed=embed)
            # If there is no entry for that member, alert the author
            embed = discord.Embed(
                title = "Member Not on LOA",
                description = f"{member.mention} is not currently on LOA, therefore their is no LOA report to view.",
                color = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        # Else, send a message letting the user know they do not have permission
        else:
            embed = discord.Embed(
                title = "Needed Roles Missing",
                description = "You are missing one of the required HR roles as defined by the database! If you believe this is an error, please make sure that all HR roles have been added using the `/hrrole add` command.",
                color = discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command()
    @app_commands.describe(member="Member whose LOA you would like to end")
    async def end(self, interaction: discord.Interaction, member: discord.Member):
        "End a members LOA early"
        # Check that the user has permission to end LOA
        if await self.check_hr_roles(interaction):
            # Retrieve all of the needed information from the on_loa table
            async with self.bot.db.execute("SELECT end_date FROM on_loa WHERE user_id = ?", (member.id,)) as cursor:
                data = await cursor.fetchall()
                # If a data entry exists, continue
                if data:
                    # Retrive the end_date from data
                    end_date = data[0][0]
                    # Delete the LOA report for that user from the on_loa table, then send a message
                    await self.bot.db.execute("DELETE FROM on_loa WHERE user_id = ?", (member.id,))
                    await self.bot.db.commit()
                    embed = discord.Embed(
                        title = f"{member} has been taken off of LOA",
                        description = f"Their LOA was ended early.",
                        color = member.color
                    )
                    # Add expected end date, and actual end date
                    embed.add_field(name="Expected end date:", value=end_date)
                    embed.add_field(name="Actual end date:", value=datetime.date.today())

                    return await interaction.response.send_message(embed=embed)
                # Else, alert the author that the member given is not current on LOA
                else: 
                    embed = discord.Embed(
                        title = "Member Not on LOA",
                        description = f"{member.mention} is not currently on LOA, therefore there is no LOA I can end.",
                        color = discord.Color.red()
                    )
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
        # Else, send a message letting the user know they do not have permission
        else:
            embed = discord.Embed(
                title = "Needed Roles Missing",
                description = "You are missing one of the required HR roles as defined by the database! If you believe this is an error, please make sure that all HR roles have been added using the `/hrrole add` command.",
                color = discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(loa(bot))