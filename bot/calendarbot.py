import asyncio
from typing import Optional

import asyncpg
from discord.ext import commands

from .config import token


class CalendarBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='f!')

        self.pool: Optional[asyncpg.Pool] = None

    def run(self):
        cogs = ['jishaku', 'bot.cogs.queue', 'bot.cogs.tasks', 'bot.cogs.prompts']

        for cog in cogs:
            self.load_extension(cog)

        super().run(token)

    async def start(self, *args, **kwargs):
        await asyncio.sleep(1)
        self.pool = await asyncpg.create_pool(user="postgres", host="db")

        return await super().start(*args, **kwargs)
