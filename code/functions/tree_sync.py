from discord.ext import commands
from discord import Object

class tree_sync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    @commands.dm_only()
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, *, guild: Object=None) -> None:
        #If no guild id is provided, sync the commands globally
        if not guild or guild == None:
            await self.bot.tree.sync()
            await ctx.author.send("Synced commands globally")
            return

        #If a guild id is provided, sync the commands to that specific guild
        elif guild != None:
            self.bot.tree.copy_global_to(guild=guild)
            await self.bot.tree.sync(guild=guild)

        await ctx.author.send(f"Synced the tree to 1 test guild.")

    #If the guild id provided is not valid, alert the author
    #Also is the command is done outside of a private message, return
    @sync.error
    async def error_sync(self, ctx, error):
        if isinstance(error, commands.errors.PrivateMessageOnly):
            return
        else:
            await ctx.author.send("That is not a valid guild ID")


async def setup(bot):
	await bot.add_cog(tree_sync(bot))