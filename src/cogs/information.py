import io

import discord
from discord import app_commands
from discord.ext import commands

from .. import ArtemisCog, config
from .file_utils import FileUtils


class Information(ArtemisCog):
    @app_commands.command()
    async def card(self, interaction: discord.Interaction, user: discord.User | discord.Member | None = None) -> None:
        from .prompts import Prompts

        if user is None:
            user = interaction.user

        prompts: Prompts = self.bot.get_cog(Prompts)

        async with self.bot.pool.acquire() as conn:
            approved: int = await conn.fetchval('SELECT COUNT(*) FROM submissions WHERE user_id = $1 AND status = \'approved\'', user.id)

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

        avatar_url: str = user.display_avatar.with_static_format('png').url

        file: discord.File
        avatar_url, file = await self.bot.get_cog(FileUtils).attempt_reupload('avatar', avatar_url, interaction.guild)

        card.set_thumbnail(url=avatar_url)

        if prompts.current_prompt is not None:
            if latest_status is None:
                latest_status = "unsubmitted"

            card.add_field(name='Current prompt progress', value=latest_status)

        await interaction.response.send_message(embed=card, ephemeral=user != interaction.user, file=file)


setup = Information.setup
