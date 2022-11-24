import asyncio
import datetime
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands, tasks

from .. import Artemis, config
from .prompts import Prompts


class Tasks(commands.Cog):
    def __init__(self, bot: Artemis):
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
        guild = self.bot.get_guild(config.event_guild_id)

        if guild is None:
            return

        submission_channel = guild.get_channel(config.submission_channel_id)

        prompts: Optional[Prompts] = self.bot.get_cog('Prompts')  # type: ignore

        if prompts is None:
            return

        if TYPE_CHECKING:
            assert isinstance(submission_channel, discord.TextChannel)

        await submission_channel.edit(topic=prompts.get_topic())

        info_message = await submission_channel.fetch_message(config.info_message_id)

        if info_message is not None and info_message.author == self.bot.user:
            await info_message.edit(content=prompts.get_info_message())

        if prompts.current_prompt is None:
            return

        prompt_message = await submission_channel.fetch_message(config.current_prompts_message_id)

        if prompt_message is not None and prompt_message.author == self.bot.user:
            await prompt_message.edit(content=config.prompts_image_links[prompts.current_day])

        if self.new_day.current_loop != 0:
            await submission_channel.send(f"It's a new day! The current prompt is {prompts.current_prompt} (#{prompts.current_prompt_number + 1})")


async def setup(bot):
    await bot.add_cog(Tasks(bot))
