import typing

import aiohttp
import asyncpg
import discord
from discord.ext import commands

from .config import token


T = typing.TypeVar('T', bound=commands.Cog)


class Artemis(commands.Bot):
    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents(guilds=True, members=True, guild_messages=True, message_content=True)
        super().__init__(command_prefix='f!', intents=intents)

        self.pool: asyncpg.Pool = discord.utils.MISSING
        self.session: aiohttp.ClientSession = discord.utils.MISSING

    def run(self) -> None:
        super().run(token)

    def get_cog(self, cog_type: type[T]) -> T:
        cog: cog_type | commands.Cog | None = super().get_cog(cog_type.__name__)

        if not isinstance(cog, cog_type):
            raise RuntimeError(f'Expected cog of type {cog_type}, got {type(cog)}')

        return cog

    async def setup_hook(self) -> None:
        self.pool = await asyncpg.create_pool(user="postgres", host="db")
        self.session = aiohttp.ClientSession(headers={'User-Agent': 'Artemis/2.0 (+https://blobs.gg)'})

        cogs: list[str] = ['jishaku', 'bot.cogs.queue', 'bot.cogs.tasks', 'bot.cogs.prompts', 'bot.cogs.information']
        for cog in cogs:
            await self.load_extension(cog)

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()

        if self.session is not None:
            await self.session.close()

        await super().close()
