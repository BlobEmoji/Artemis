from __future__ import annotations

import enum
import functools
import logging
import re
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from .. import Artemis, config


if TYPE_CHECKING:
    from .prompts import Prompts


log = logging.getLogger(__name__)


class SubmissionStatus(enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    DENIED = 'denied'
    DISMISSED = 'dismissed'


def wrap_interface_button(f):
    @functools.wraps(f)
    async def wrapper(self: QueueInterface, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()

        assert self.cog.bot.pool is not None
        assert interaction.message is not None

        async with self.cog.bot.pool.acquire() as conn:
            submission_id = await conn.fetchval(
                'SELECT id FROM submissions WHERE queue_message_id = $1', interaction.message.id
            )

        await f(self, submission_id)
        await interaction.message.delete()

    return wrapper


class QueueInterface(discord.ui.View):
    def __init__(self, cog: Queue):
        super().__init__(timeout=None)

        self.cog = cog

    @discord.ui.button(label='Approve', custom_id='approve', style=discord.ButtonStyle.green)  # type: ignore
    @wrap_interface_button
    async def approve(self, submission_id: int):
        await self.cog.approve_submission(submission_id)

    @discord.ui.button(label='Reject', custom_id='reject', style=discord.ButtonStyle.red)  # type: ignore
    @wrap_interface_button
    async def reject(self, submission_id: int):
        await self.cog.reject_submission(submission_id)

    @discord.ui.button(label='Dismiss', custom_id='dismiss', style=discord.ButtonStyle.gray)  # type: ignore
    @wrap_interface_button
    async def dismiss(self, submission_id: int):
        await self.cog.dismiss_submission(submission_id)


class Queue(commands.Cog):
    def __init__(self, bot: Artemis):
        self.bot = bot

        view = QueueInterface(self)
        bot.loop.call_later(0, bot.add_view, view)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if config.submission_channel_id == message.channel.id:
            await self._process_message(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if payload.channel_id != config.submission_channel_id:
            return

        channel = self.bot.get_channel(config.submission_channel_id)

        if TYPE_CHECKING:
            assert isinstance(channel, discord.TextChannel)

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        await self._process_message(message)

    async def _process_message(self, message: discord.Message):
        if message.author.bot:
            return

        urls = re.findall(r'(https?://\S+)', message.content)
        attachment_urls = [a.url for a in message.attachments]

        for url in urls + attachment_urls:
            await self._process_submission(message, url)

    async def _process_submission(self, message: discord.Message, url: str):
        assert self.bot.pool is not None

        channel = self.bot.get_channel(config.queue_channel_id)
        prompts: Optional[Prompts] = self.bot.get_cog('Prompts')  # type: ignore

        if prompts is None:
            return

        if prompts.current_prompt is None:
            return

        if TYPE_CHECKING:
            assert isinstance(channel, discord.TextChannel)

        prompt = await channel.send(
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

    async def approve_submission(self, submission_id: int):
        assert self.bot.pool is not None

        async with self.bot.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT user_id, image_url, prompt_idx
                FROM submissions
                WHERE id = $1
                """,
                submission_id,
            )

        guild = self.bot.get_guild(config.event_guild_id)

        if guild is None:
            return

        member = guild.get_member(record['user_id'])

        if member is None:
            return

        prompt_idx = record['prompt_idx']
        prompt = config.prompts[prompt_idx]

        embed = discord.Embed(title=f'{prompt} (Prompt #{prompt_idx})')

        embed.color = config.embed_color
        embed.set_image(url=record['image_url'])

        embed.set_author(name=str(member), icon_url=member.display_avatar.url)

        channel = self.bot.get_channel(config.gallery_channel_id)

        if TYPE_CHECKING:
            assert isinstance(channel, discord.TextChannel)

        message = await channel.send(embed=embed)

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE submissions SET status = $1, gallery_message_id = $2 WHERE id = $3',
                SubmissionStatus.APPROVED.value,
                message.id,
                submission_id,
            )

            approved = await conn.fetchval(
                'SELECT COUNT(*) FROM submissions WHERE user_id = $1 AND status = \'approved\'', member.id
            )

        if approved >= config.event_role_requirement:
            await member.add_roles(discord.Object(config.event_role_id), reason='Event participation')

        await self.update_statistics_file()

    async def reject_submission(self, submission_id: int):
        submission = await self._update_submission_status(submission_id, SubmissionStatus.DENIED)

        user = self.bot.get_user(submission['user_id'])

        if user is None:
            return

        prompt = config.prompts[submission['prompt_idx']]

        try:
            await user.send(
                f'Your {prompt} Drawfest submission has been denied by a staff member.\n\n'
                f'Please review that your submission was made according to our rules, '
                f'if you\'re confused about the denial feel free to DM Blob Mail.',
                allowed_mentions=discord.AllowedMentions(users=[user]),
            )
        except discord.HTTPException:
            return

    async def dismiss_submission(self, submission_id: int):
        await self._update_submission_status(submission_id, SubmissionStatus.DISMISSED)

    async def _update_submission_status(self, submission_id: int, status: SubmissionStatus):
        assert self.bot.pool is not None

        async with self.bot.pool.acquire() as conn:
            record = await conn.fetchrow(
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

    async def update_statistics_file(self):
        assert self.bot.pool is not None
        assert self.bot.session is not None

        async with self.bot.pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT user_id, ARRAY_AGG(prompt_idx) approved_submissions
                FROM submissions
                WHERE status = 'approved'
                GROUP BY user_id
                """
            )

        data = []

        for record in records:
            user = self.bot.get_user(record['user_id'])

            if user is None:
                continue

            data.append(
                {
                    'id': str(user.id),
                    'name': user.name,
                    'discriminator': user.discriminator,
                    'avatar': user.avatar and user.avatar.key,
                    'approved_submissions': record['approved_submissions'],
                }
            )

        headers = {
            'Authorization': config.statistics_authorization,
        }

        async with self.bot.session.put(config.statistics_endpoint, headers=headers, json=data) as resp:
            text = await resp.text()
            log.info(f'Updated statistics: {resp.status} - {text}.')


def setup(bot: Artemis):
    bot.add_cog(Queue(bot))
