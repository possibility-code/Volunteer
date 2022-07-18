import discord
from clocking_helpers.clock_in import clock_in
from clocking_helpers.clock_out import clock_out

class TimerError(Exception):
    """Used to report errors within the clock in/out functions"""

class ClockView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot


    @discord.ui.button(label='Clock In', style=discord.ButtonStyle.green, row=1)
    async def clock_in(self, interaction: discord.Interaction, button: discord.ui.Button):
        await clock_in(self, interaction)


    @discord.ui.button(label='Clock Out', style=discord.ButtonStyle.red, row=1)
    async def clock_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        await clock_out(self, interaction)
