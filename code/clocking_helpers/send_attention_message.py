import discord
import asyncio
import time
from clocking_helpers.clock_out_user import clock_out_user

# Send the attention message to the user
async def send_attention_message(self, member, user_id):
    try:
        # Send the message to the user, add the reaction, and check for the user to add a reaction with a timeout of 5 minutes
        try:
            self.bot.in_progress[user_id] = "IN PROGRESS"
            msg = await member.send("It is time for your attention checkup, please react to this message within 5 minutes in order to stay clocked in!")
        except discord.errors.Forbidden:
            del self.bot.in_progress[user_id]
            return await clock_out_user(self.bot, user_id)

        await msg.add_reaction("\U00002705")
        reaction, _ = await self.bot.wait_for(
            'reaction_add', check=lambda reaction, member:member != self.bot.user and str(reaction.emoji) == "\U00002705" and reaction.message.id == msg.id, timeout=300
        )
    # If we get a TimeoutError, the user did not respond, so we clock them out
    except asyncio.TimeoutError:
        del self.bot.in_progress[user_id]
        await clock_out_user(self.bot, user_id)
        return await member.send("You have been clocked out as you did not react in time!")
    # If the user reacts, we clock them in
    if reaction.emoji:
        await member.send("Thank you for showing you are still active!")
        self.bot.check_up_times[user_id] = time.time()
        del self.bot.in_progress[user_id]
