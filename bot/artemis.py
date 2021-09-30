import asyncio
from typing import Optional

import asyncpg
import discord
from discord.ext import commands

from .config import token


class Artemis(commands.Bot):
    def __init__(self):
        intents = discord.Intents(guilds=True, members=True, guild_messages=True)
        super().__init__(command_prefix='f!', intents=intents)

        self.pool: Optional[asyncpg.Pool] = None

    def run(self):
        super().run(token)

    async def start(self, *args, **kwargs):
        await asyncio.sleep(1)
        self.pool = await asyncpg.create_pool(user="postgres", host="db")

        cogs = ['jishaku', 'bot.cogs.queue', 'bot.cogs.tasks', 'bot.cogs.prompts']

        for cog in cogs:
            self.load_extension(cog)

        return await super().start(*args, **kwargs)
