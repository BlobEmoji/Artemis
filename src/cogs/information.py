import discord
from discord import app_commands

from .. import ArtemisCog, config
from .event_data import EventData, FullSubmission, SubmissionStatus
from .file_utils import FileUtils


class Information(ArtemisCog):
    @app_commands.command()
    async def card(self, interaction: discord.Interaction, user: discord.User | discord.Member | None = None) -> None:
        from .prompts import Prompts

        if user is None:
            user = interaction.user

        prompts: Prompts = self.bot.get_cog(Prompts)
        event_data: EventData = self.bot.get_cog(EventData)

        approved: int = len(await event_data.submissions_with_status(SubmissionStatus.APPROVED, user.id))
        current_submission: FullSubmission | None = await event_data.submission_by_prompt(user.id, prompts.current_prompt_id)

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
            latest_status: str = current_submission['status'] if current_submission is not None else 'unsubmitted'
            card.add_field(name='Current prompt progress', value=latest_status)

        await interaction.response.send_message(embed=card, ephemeral=user != interaction.user, file=file)


setup = Information.setup
