from __future__ import annotations

import asyncio
import functools
import logging
import re
from typing import Callable, Coroutine

import discord
from discord.ext import commands
from discord.ui.item import ItemCallbackType

from .. import Artemis, ArtemisCog, config
from ..plaques import create_plaque
from .event_data import EventData, FullSubmission, SubmissionStatus
from .file_utils import FileUtils
from .prompts import Prompts


log = logging.getLogger(__name__)


def autoload_queue_submission(
    button_callback: Callable[[QueueInterface, FullSubmission, discord.Message], Coroutine]
) -> ItemCallbackType[QueueInterface, discord.ui.Button]:
    @functools.wraps(button_callback)
    async def wrapper(self: QueueInterface, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        assert interaction.message is not None

        submission: FullSubmission | None = await self.cog.bot.get_cog(EventData).submission_from_queue(interaction.message.id)

        if submission is None:
            log.error(f'No corresponding submission for queue message {interaction.message.id}')
            return

        await button_callback(self, submission, interaction.message)

    return wrapper


class QueueInterface(discord.ui.View):
    def __init__(self, cog: Queue):
        super().__init__(timeout=None)

        self.cog: Queue = cog

    @discord.ui.button(label='Approve', custom_id='approve', style=discord.ButtonStyle.green)
    @autoload_queue_submission
    async def approve(self, submission: FullSubmission, queue_message: discord.Message) -> None:
        await self.cog.approve_submission(submission)
        await queue_message.delete()

    @discord.ui.button(label='Reject', custom_id='reject', style=discord.ButtonStyle.red)
    @autoload_queue_submission
    async def reject(self, submission: FullSubmission, queue_message: discord.Message) -> None:
        await self.cog.reject_submission(submission)
        await queue_message.delete()

    @discord.ui.button(label='Dismiss', custom_id='dismiss', style=discord.ButtonStyle.gray)
    @autoload_queue_submission
    async def dismiss(self, submission: FullSubmission, queue_message: discord.Message) -> None:
        await self.cog.dismiss_submission(submission)
        await queue_message.delete()

    @discord.ui.button(label='Previous Prompt', custom_id='previous', style=discord.ButtonStyle.primary, row=1)
    @autoload_queue_submission
    async def previous(self, submission: FullSubmission, queue_message: discord.Message) -> None:
        await self.cog.increment_prompt(-1, submission, queue_message)

    @discord.ui.button(label='Next Prompt', custom_id='next', style=discord.ButtonStyle.primary, row=1)
    @autoload_queue_submission
    async def next(self, submission: FullSubmission, queue_message: discord.Message) -> None:
        await self.cog.increment_prompt(+1, submission, queue_message)


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

    def queue_text(self, prompt_id: int, image_url: str, user: discord.User | discord.Member) -> str:
        return f'**{config.prompts[prompt_id]}** ({prompt_id + 1}) submission by **{user}** {user.mention}\n\n{image_url}'

    async def _process_submission(self, message: discord.Message, url: str) -> None:
        prompts: Prompts = self.bot.get_cog(Prompts)

        submission_exists: bool = await self.bot.get_cog(EventData).submission_by_image(url) is not None

        if submission_exists:
            return

        prompt: discord.Message = await self.bot.queue_channel.send(
            self.queue_text(prompts.current_prompt_number, url, message.author),
            view=QueueInterface(self),
        )

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO submissions (user_id, image_url, prompt_id, status, message_id, queue_message_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                message.author.id,
                url,
                prompts.current_prompt_number,
                SubmissionStatus.PENDING.value,
                message.id,
                prompt.id,
            )

    async def increment_prompt(self, amount: int, submission: FullSubmission, queue_message: discord.Message):
        user: discord.User | None = self.bot.get_user(submission['user_id'])
        if user is None:
            return

        new_prompt_id: int = (submission['prompt_id'] + amount) % len(config.prompts)

        async with self.bot.pool.acquire() as conn:
            await conn.execute('UPDATE submissions SET prompt_id = $1 WHERE id = $2', new_prompt_id, submission['id'])

        await queue_message.edit(content=self.queue_text(new_prompt_id, submission['image_url'], user))

    async def approve_submission(self, submission: FullSubmission) -> None:
        await self._update_submission_status(submission['id'], SubmissionStatus.APPROVED)

        member: discord.Member | None = self.bot.event_guild.get_member(submission['user_id'])
        if member is None:
            return

        prompt_id: int = submission['prompt_id']

        file_utils = self.bot.get_cog(FileUtils)

        artwork_url = await file_utils.attempt_reupload('artwork', submission['image_url'])

        plaque = create_plaque([f'@{member.name}', f'"{config.prompts[prompt_id]}" (#{prompt_id})'], bold_lines=[0])
        plaque = file_utils.upload_image('plaque', plaque)

        gallery_message: discord.Message = await self.bot.gallery_channel.send(artwork_url, file=plaque)

        event_data: EventData = self.bot.get_cog(EventData)

        async with self.bot.pool.acquire() as conn:
            await conn.execute('UPDATE submissions SET image_url = $1 WHERE id = $2', artwork_url, submission['id'])
            await conn.execute('INSERT INTO gallery (submission_id, message_id) VALUES ($1, $2)', submission['id'], gallery_message.id)

        approved_submissions: int = len(await event_data.submissions_with_status(SubmissionStatus.APPROVED, member.id))
        if approved_submissions >= config.event_role_requirement:
            await member.add_roles(discord.Object(config.event_role_id), reason='Event participation')

        await event_data.update_user_statistics(member)
        await event_data.update_submission_info(member)

    async def reject_submission(self, submission: FullSubmission) -> None:
        await self._update_submission_status(submission['id'], SubmissionStatus.DENIED)

        user = self.bot.get_user(submission['user_id'])

        if user is None:
            return

        prompt: str = config.prompts[submission['prompt_id']]

        try:
            await user.send(
                f'Your {prompt} Drawfest submission has been denied by a staff member.\n\n'
                f'Please review that your submission was made according to our rules, '
                f'if you\'re confused about the denial feel free to DM Blob Mail.',
                allowed_mentions=discord.AllowedMentions(users=[user]),
            )
        except discord.HTTPException:
            return

    async def dismiss_submission(self, submission: FullSubmission) -> None:
        await self._update_submission_status(submission['id'], SubmissionStatus.DISMISSED)

    async def _update_submission_status(self, submission_id: int, status: SubmissionStatus) -> None:
        async with self.bot.pool.acquire() as conn:
            await conn.execute('UPDATE submissions SET status = $2 WHERE id = $1', submission_id, status.value)


setup = Queue.setup
