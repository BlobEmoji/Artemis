import asyncio
from typing import Optional

import aiohttp
import asyncpg
import discord
from discord.ext import commands

from .config import token


class Artemis(commands.Bot):
    def __init__(self):
        intents = discord.Intents(guilds=True, members=True, guild_messages=True)
        super().__init__(command_prefix='f!', intents=intents)

        self.pool: Optional[asyncpg.Pool] = None
        self.session: Optional[aiohttp.ClientSession] = None

    def run(self):
        super().run(token)

    async def start(self, *args, **kwargs):
        await asyncio.sleep(1)

        self.pool = await asyncpg.create_pool(user="postgres", host="db")
        self.session = aiohttp.ClientSession(headers={'User-Agent': 'Artemis/2.0 (+https://blobs.gg)'})

        cogs = ['jishaku', 'bot.cogs.queue', 'bot.cogs.tasks', 'bot.cogs.prompts']

        for cog in cogs:
            self.load_extension(cog)

        return await super().start(*args, **kwargs)

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()

        if self.session is not None:
            await self.session.close()

        await super().close()
