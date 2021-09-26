import asyncio
import datetime

import asyncpg
from discord.ext import commands
from discord.ext.commands import Bot

from .config import prompts, start_day, token


class CalendarBot(Bot):
    def __init__(self):
        super().__init__(command_prefix='f!')

    def run(self):
        cogs = ['jishaku', 'bot.cogs.queue', 'bot.cogs.tasks', 'bot.cogs.prompts']

        for cog in cogs:
            self.load_extension(cog)

        self.can_start_daily = True

        super().run(token)

    async def start(self, *args, **kwargs):
        await asyncio.sleep(1)
        self.pool = await asyncpg.create_pool(user="postgres", host="db")

        return await super().start(*args, **kwargs)
