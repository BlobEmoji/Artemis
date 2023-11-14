from __future__ import annotations

import asyncio
import enum
import functools
import logging
import re
from typing import TYPE_CHECKING, Any, TypedDict

import discord
from discord.ext import commands

from .. import Artemis, ArtemisCog, config
from .file_utils import FileUtils


log = logging.getLogger(__name__)


class SubmissionStatus(enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    DENIED = 'denied'
    DISMISSED = 'dismissed'


class UserData(TypedDict):
    username: str
    discriminator: str

    avatar: str | None


class SubmissionInfo(TypedDict):
    prompt_id: int
    image_url: str


def wrap_interface_button(f):
    @functools.wraps(f)
    async def wrapper(self: QueueInterface, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        assert interaction.message is not None

        async with self.cog.bot.pool.acquire() as conn:
            submission_id: int = await conn.fetchval('SELECT id FROM submissions WHERE queue_message_id = $1', interaction.message.id)

        await f(self, submission_id)
        await interaction.message.delete()

    return wrapper


class QueueInterface(discord.ui.View):
    def __init__(self, cog: Queue):
        super().__init__(timeout=None)

        self.cog: Queue = cog

    @discord.ui.button(label='Approve', custom_id='approve', style=discord.ButtonStyle.green)  # type: ignore
    @wrap_interface_button
    async def approve(self, submission_id: int) -> None:
        await self.cog.approve_submission(submission_id)

    @discord.ui.button(label='Reject', custom_id='reject', style=discord.ButtonStyle.red)  # type: ignore
    @wrap_interface_button
    async def reject(self, submission_id: int) -> None:
        await self.cog.reject_submission(submission_id)

    @discord.ui.button(label='Dismiss', custom_id='dismiss', style=discord.ButtonStyle.gray)  # type: ignore
    @wrap_interface_button
    async def dismiss(self, submission_id: int) -> None:
        await self.cog.dismiss_submission(submission_id)


class Queue(ArtemisCog):
    view: QueueInterface
    lock: asyncio.Lock

    def __init__(self, bot: Artemis) -> None:
        super().__init__(bot)

        view = QueueInterface(self)
        bot.add_view(view)

        self.lock = asyncio.Lock()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if config.submission_channel_id == message.channel.id:
            await self._process_message(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        if payload.channel_id != config.submission_channel_id:
            return

        channel: discord.TextChannel | Any = self.bot.get_channel(config.submission_channel_id)

        if TYPE_CHECKING:
            assert isinstance(channel, discord.TextChannel)

        try:
            message: discord.Message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        await self._process_message(message)

    async def _process_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        urls: list[str] = re.findall(r'(https?://\S+)', message.content)
        attachment_urls: list[str] = [a.url for a in message.attachments]

        for url in urls + attachment_urls:
            async with self.lock:
                await self._process_submission(message, url)

    async def _process_submission(self, message: discord.Message, url: str) -> None:
        from .prompts import Prompts

        queue_channel: discord.TextChannel | Any = self.bot.get_channel(config.queue_channel_id)
        if not isinstance(queue_channel, discord.TextChannel):
            raise RuntimeError(f'The submission channel configured is of {type(queue_channel)} type, not TextChannel!')

        prompts: Prompts = self.bot.get_cog(Prompts)

        if prompts.current_prompt is None:
            return

        async with self.bot.pool.acquire() as conn:
            exists: bool = await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT *
                    FROM submissions
                    WHERE image_url = $1
                )
                """,
                url,
            )

            if exists:
                return

        prompt: discord.Message = await queue_channel.send(
            f'**{prompts.current_prompt}** submission by **{message.author}** {message.author.mention}\n\n{url}',
            view=QueueInterface(self),
        )

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO submissions (user_id, image_url, prompt_idx, status, message_id, queue_message_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                message.author.id,
                url,
                prompts.current_prompt_number,
                SubmissionStatus.PENDING.value,
                message.id,
                prompt.id,
            )

    async def approve_submission(self, submission_id: int) -> None:
        async with self.bot.pool.acquire() as conn:
            record: dict = await conn.fetchrow(
                """
                SELECT user_id, image_url, prompt_idx
                FROM submissions
                WHERE id = $1
                """,
                submission_id,
            )

        guild: discord.Guild | None = self.bot.get_guild(config.event_guild_id)
        if guild is None:
            raise RuntimeError('The guild ID given in the config is invalid!')

        member: discord.Member | None = guild.get_member(record['user_id'])
        if member is None:
            return

        prompt_idx: int = record['prompt_idx']
        prompt: str = config.prompts[prompt_idx]

        embed: discord.Embed = discord.Embed(title=f'{prompt} (Prompt #{prompt_idx + 1})', color=config.embed_color)

        file_utils = self.bot.get_cog(FileUtils)

        artwork_url: str = record['image_url']
        artwork: discord.File

        artwork_url, artwork = await file_utils.attempt_reupload('artwork', record['image_url'], guild)
        embed.set_image(url=artwork_url)

        avatar_url: str = member.display_avatar.with_static_format('png').url
        avatar: discord.File

        avatar_url, avatar = await file_utils.attempt_reupload('avatar', avatar_url, guild)

        embed.set_author(name=str(member), icon_url=avatar_url)

        channel: discord.TextChannel | Any = self.bot.get_channel(config.gallery_channel_id)

        if TYPE_CHECKING:
            assert isinstance(channel, discord.TextChannel)

        message: discord.Message = await channel.send(
            embed=embed, files=[file for file in (artwork, avatar) if file is not discord.utils.MISSING]
        )

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE submissions SET status = $1, gallery_message_id = $2 WHERE id = $3',
                SubmissionStatus.APPROVED.value,
                message.id,
                submission_id,
            )

            approved = await conn.fetchval('SELECT COUNT(*) FROM submissions WHERE user_id = $1 AND status = \'approved\'', member.id)

        if approved >= config.event_role_requirement:
            await member.add_roles(discord.Object(config.event_role_id), reason='Event participation')

        await self.update_user_statistics(member)
        await self.update_submission_info(member)

    async def reject_submission(self, submission_id: int) -> None:
        submission: dict = await self._update_submission_status(submission_id, SubmissionStatus.DENIED)

        user = self.bot.get_user(submission['user_id'])

        if user is None:
            return

        prompt: str = config.prompts[submission['prompt_idx']]

        try:
            await user.send(
                f'Your {prompt} Drawfest submission has been denied by a staff member.\n\n'
                f'Please review that your submission was made according to our rules, '
                f'if you\'re confused about the denial feel free to DM Blob Mail.',
                allowed_mentions=discord.AllowedMentions(users=[user]),
            )
        except discord.HTTPException:
            return

    async def dismiss_submission(self, submission_id: int) -> None:
        await self._update_submission_status(submission_id, SubmissionStatus.DISMISSED)

    async def _update_submission_status(self, submission_id: int, status: SubmissionStatus) -> dict:
        async with self.bot.pool.acquire() as conn:
            record: dict = await conn.fetchrow(
                """
                UPDATE submissions
                SET status = $2
                WHERE id = $1
                RETURNING id, user_id, image_url, prompt_idx, status, message_id, queue_message_id, gallery_message_id
                """,
                submission_id,
                status.value,
            )

        return record

    async def post_statistics(self, link: str, data: UserData | list[SubmissionInfo]) -> None:
        headers: dict = {
            'Authorization': config.statistics_authorization,
        }

        async with self.bot.session.post(link, headers=headers, json=data) as resp:
            text: str = await resp.text()
            log.info(f'Updated statistics: {resp.status} - {text}.')

    async def update_user_statistics(self, user: discord.Member) -> None:
        if config.statistics_authorization is None:
            return

        link: str = f'https://api.blobs.gg/v1/users/{user.id}'

        data: UserData = {
            "username": user.name,
            "discriminator": user.discriminator,
            "avatar": user.avatar and user.avatar.key,  # type: ignore
        }

        await self.post_statistics(link, data)

    async def update_submission_info(self, user: discord.Member) -> None:
        if config.statistics_authorization is None:
            return

        link: str = f'https://api.blobs.gg/v1/events/drawfest/{config.start_day.year}/submissions/{user.id}'

        data: list[SubmissionInfo] = []

        async with self.bot.pool.acquire() as conn:
            approved: list[dict] = await conn.fetch(
                'SELECT image_url, prompt_idx FROM submissions WHERE user_id = $1 AND status = \'approved\'', user.id
            )

        for record in approved:
            data.append({'prompt_id': record['prompt_idx'], 'image_url': record['image_url']})

        await self.post_statistics(link, data)


setup = Queue.setup
