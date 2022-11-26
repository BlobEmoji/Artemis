import io
import logging
from typing import TYPE_CHECKING, Optional

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.prompts import Prompts

from .. import Artemis, config


class Information(commands.Cog):
    def __init__(self, bot: Artemis):
        self.bot = bot

    @app_commands.command()
    async def card(self, interaction: discord.Interaction, user: discord.User | discord.Member | None = None):
        if user is None:
            user = interaction.user

        prompts: Prompts | commands.Cog | None = self.bot.get_cog('Prompts')

        if not isinstance(prompts, Prompts):
            return

        async with self.bot.pool.acquire() as conn:
            approved: int = await conn.fetchval(
                'SELECT COUNT(*) FROM submissions WHERE user_id = $1 AND status = \'approved\'', user.id
            )

            latest_status: str = await conn.fetchval(
                'SELECT status FROM submissions WHERE user_id = $1 AND prompt_idx = $2',
                user.id,
                prompts.current_prompt_number,
            )

        card = discord.Embed(
            title=f"{user.name}'s {config.event_name} stats",
            description=f"{approved}/{len(config.prompts)}",
            color=config.embed_color,
        )

        if prompts.current_prompt is not None:
            if latest_status is None:
                latest_status = "unsubmitted"

            card.add_field(name='Current prompt progress', value=latest_status)

        avatar_url = user.display_avatar.with_static_format('png').url
        avatar_ext = 'gif' if user.display_avatar.is_animated() else 'png'

        if interaction.guild is None:
            return

        # Send as attachment if possible, as URLs expire
        file: Optional[discord.File] = None
        link = None

        async with self.bot.session.get(avatar_url) as resp:
            size = int(resp.headers['Content-Length'])

            if size <= interaction.guild.filesize_limit:
                file_name = 'avatar.' + avatar_ext
                link = f'attachment://{file_name}'

                data = io.BytesIO(await resp.read())
                file = discord.File(data, file_name)

        if file is None:
            link = avatar_url

        card.set_thumbnail(url=link)

        await interaction.response.send_message(embed=card, ephemeral=user != interaction.user, file=file)


async def setup(bot: Artemis):
    await bot.add_cog(Information(bot))
