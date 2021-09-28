import asyncio
import datetime

from discord.ext import commands, tasks

from bot import CalendarBot

from .. import config


class Tasks(commands.Cog):
    def __init__(self, bot: CalendarBot):
        self.bot = bot

        if bot.is_ready():
            asyncio.create_task(self.on_ready())

    @commands.Cog.listener()
    async def on_ready(self):
        self.new_day.start()

    def cog_unload(self):
        self.new_day.cancel()

    @tasks.loop(time=datetime.time(0, 0, 0, 0))
    async def new_day(self):
        prompts = self.bot.get_cog('Prompts')

        submission_channel = self.bot.get_guild(config.event_guild_id).get_channel(config.submission_channel_id)

        await submission_channel.edit(topic=prompts.get_topic())

        info_message = await submission_channel.fetch_message(config.info_message_id)
        prompt_message = await submission_channel.fetch_message(config.current_prompts_message_id)

        if info_message is not None and info_message.author.id == self.bot.user.id:
            await info_message.edit(content=prompts.get_info_message())

        if prompt_message is not None and prompt_message.author.id == self.bot.user.id:
            await prompt_message.edit(content=config.prompts_image_links[prompts.current_prompt_number])

        day_number = (datetime.datetime.now().date() - config.start_day).days

        if self.new_day.current_loop != 0:
            await submission_channel.send(day_number)


def setup(bot):
    bot.add_cog(Tasks(bot))
