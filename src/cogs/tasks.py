import asyncio
import datetime

import discord
from discord.ext import commands, tasks

from .. import Artemis, ArtemisCog, config
from .prompts import Prompts


class Tasks(ArtemisCog):
    def __init__(self, bot: Artemis) -> None:
        super().__init__(bot)

        self.update_submission_channel.start()
        self.announce_new_day.start()
        asyncio.create_task(self.run_first_iteration())

    def cog_unload(self) -> None:
        self.update_submission_channel.cancel()

    async def run_first_iteration(self) -> None:
        await self.bot.wait_until_ready()

        await self.update_submission_channel()

    @tasks.loop(time=datetime.time(0, 0, 0, 0))
    async def update_submission_channel(self) -> None:
        prompts: Prompts = self.bot.get_cog(Prompts)

        await self.bot.submission_channel.edit(topic=prompts.get_topic())

        info_message: discord.Message = await self.bot.submission_channel.fetch_message(config.info_message_id)
        if info_message.author == self.bot.user:
            await info_message.edit(content=prompts.get_info_message())

        if prompts.current_prompt is None:
            return

        prompt_message: discord.Message = await self.bot.submission_channel.fetch_message(config.current_prompts_message_id)
        if prompt_message.author == self.bot.user:
            await prompt_message.edit(content=config.prompts_image_links[prompts.current_day])

    @tasks.loop(time=datetime.time(0, 0, 0, 0))
    async def announce_new_day(self) -> None:
        prompts: Prompts = self.bot.get_cog(Prompts)

        await self.bot.submission_channel.send(
            f"It's a new day! The current prompt is {prompts.current_prompt} (#{prompts.current_prompt_id + 1})"
        )

    @update_submission_channel.before_loop
    async def ensure_ready(self) -> None:
        await self.bot.wait_until_ready()


setup = Tasks.setup
