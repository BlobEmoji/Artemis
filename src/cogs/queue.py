from __future__ import annotations

import asyncio
import enum
import functools
import logging
import re
from typing import TYPE_CHECKING, Any, TypedDict

import discord
from discord.ext import commands
from PIL import Image

from .. import Artemis, ArtemisCog, config
from ..plaques import create_plaque
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
        if self.bot.submission_channel == message.channel:
            await self._process_message(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        if payload.channel_id != config.submission_channel_id:
            return

        edited_message: discord.Message = await self.bot.submission_channel.fetch_message(payload.message_id)

        await self._process_message(edited_message)

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

        prompt: discord.Message = await self.bot.queue_channel.send(
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

        member: discord.Member | None = self.bot.event_guild.get_member(record['user_id'])
        if member is None:
            return

        prompt_idx: int = record['prompt_idx']

        file_utils = self.bot.get_cog(FileUtils)

        artwork_url, artwork = await file_utils.attempt_reupload('artwork', record['image_url'], self.bot.event_guild)

        plaque = create_plaque([f'@{member.name}', f'"{config.prompts[prompt_idx]}" (#{prompt_idx})'], bold_lines=[0])
        plaque = file_utils.upload_image('plaque', plaque)

        content: str = ''

        if artwork is discord.utils.MISSING:
            content += f'\n{artwork_url}'

        plaque_message: discord.Message = await self.bot.gallery_channel.send(file=plaque)
        art_message: discord.Message = await self.bot.gallery_channel.send(content, file=artwork)

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE submissions SET status = $1, gallery_message_id = $2 WHERE id = $3',
                SubmissionStatus.APPROVED.value,
                art_message.id,
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
