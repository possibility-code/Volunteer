import discord
from discord.ext import commands
from discord.ext.commands.errors import *

class slash_handlers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.tree.on_error = self.on_error


    async def on_error(self, interaction: discord.Interaction, command, error):
        error = getattr(error, 'original', error)
        # If the error is a 'MissingPermissions' error, send the embed
        if isinstance(error, MissingPermissions):
            embed = discord.Embed(
                title = "→ Missing Permissions!",
                description = f"• {error}",
                colour = discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        # Else, we have a new, unhandled error, so print the error to the console
        else:
            print(error)


async def setup(bot: commands.Bot):
    await bot.add_cog(slash_handlers(bot))