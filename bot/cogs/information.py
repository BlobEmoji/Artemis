import io

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from .. import Artemis, config


class Information(commands.Cog):
    def __init__(self, bot: Artemis) -> None:
        self.bot: Artemis = bot

    @app_commands.command()
    async def card(self, interaction: discord.Interaction, user: discord.User | discord.Member | None = None) -> None:
        from .prompts import Prompts

        if user is None:
            user = interaction.user

        prompts: Prompts = self.bot.get_cog(Prompts)

        async with self.bot.pool.acquire() as conn:
            approved: int = await conn.fetchval(
                'SELECT COUNT(*) FROM submissions WHERE user_id = $1 AND status = \'approved\'', user.id
            )

            latest_status: str = await conn.fetchval(
                'SELECT status FROM submissions WHERE user_id = $1 AND prompt_idx = $2',
                user.id,
                prompts.current_prompt_number,
            )

        card: discord.Embed = discord.Embed(
            title=f"{user.name}'s {config.event_name} stats",
            description=f"{approved}/{len(config.prompts)}",
            color=config.embed_color,
        )

        if prompts.current_prompt is not None:
            if latest_status is None:
                latest_status = "unsubmitted"

            card.add_field(name='Current prompt progress', value=latest_status)

        avatar_url: str = user.display_avatar.with_static_format('png').url
        avatar_ext: str = 'gif' if user.display_avatar.is_animated() else 'png'

        if interaction.guild is None:
            return

        # Send as attachment if possible, as URLs expire
        file: discord.File = discord.utils.MISSING

        async with self.bot.session.get(avatar_url) as resp:
            size: int = int(resp.headers['Content-Length'])
            link: str

            if size <= interaction.guild.filesize_limit:
                file_name: str = 'avatar.' + avatar_ext
                link = f'attachment://{file_name}'

                data: io.BytesIO = io.BytesIO(await resp.read())
                file: discord.File = discord.File(data, file_name)
            else:
                link = avatar_url

        card.set_thumbnail(url=link)

        await interaction.response.send_message(embed=card, ephemeral=user != interaction.user, file=file)


async def setup(bot: Artemis) -> None:
    await bot.add_cog(Information(bot))
