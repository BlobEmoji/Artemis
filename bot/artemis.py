import typing

import aiohttp
import asyncpg
import discord
from discord.ext import commands

from .config import token


T = typing.TypeVar('T', bound=commands.Cog)


class Artemis(commands.Bot):
    pool: asyncpg.Pool
    session: aiohttp.ClientSession

    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents(guilds=True, members=True, guild_messages=True, message_content=True)
        super().__init__(command_prefix='f!', intents=intents)

        self.pool = discord.utils.MISSING
        self.session = discord.utils.MISSING

    def run(self) -> None:
        super().run(token)

    def get_cog(self, cog_type: type[T]) -> T:
        cog: cog_type | typing.Any = super().get_cog(cog_type.__name__)

        if not isinstance(cog, cog_type):
            raise RuntimeError(f'Expected cog of type {cog_type}, got {type(cog)}')

        return cog

    async def setup_hook(self) -> None:
        self.pool = await asyncpg.create_pool(user='postgres', host='db')  # type: ignore # This function is not properly typed in asyncpg, but does work properly.
        self.session = aiohttp.ClientSession(headers={'User-Agent': 'Artemis/2.0 (+https://blobs.gg)'})

        cogs: list[str] = [
            'bot.cogs.file_utils',
            'bot.cogs.information',
            'bot.cogs.prompts',
            'bot.cogs.queue',
            'bot.cogs.tasks',
            'jishaku',
        ]
        for cog in cogs:
            await self.load_extension(cog)

    async def close(self) -> None:
        await self.session.close()

        await super().close()


class ArtemisCog(commands.Cog):
    bot: Artemis

    def __init__(self, bot: Artemis):
        self.bot = bot

    @classmethod
    async def setup(cls, bot: Artemis) -> None:
        await bot.add_cog(cls(bot))
