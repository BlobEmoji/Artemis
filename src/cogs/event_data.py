import enum
import logging
from typing import TypedDict, cast

import asyncpg
import discord

from .. import ArtemisCog, config


class SubmissionStatus(enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    DENIED = 'denied'
    DISMISSED = 'dismissed'


class UserData(TypedDict):
    username: str
    discriminator: str

    avatar: str | None


class BasicSubmissionInfo(TypedDict):
    prompt_id: int
    image_url: str


class FullSubmission(BasicSubmissionInfo):
    id: int
    user_id: int

    status: str

    message_id: int


log = logging.getLogger(__name__)

SUBMISSION_FIELDS: str = 'id, user_id, image_url, prompt_id, status, message_id'


class EventData(ArtemisCog):
    @property
    def pool(self) -> asyncpg.Pool:
        return self.bot.pool

    async def submission_by_id(self, id: int) -> FullSubmission | None:
        async with self.pool.acquire() as conn:
            submission: asyncpg.Record | None = await conn.fetchrow(
                f"""
                SELECT {SUBMISSION_FIELDS}
                FROM submissions
                WHERE id = $1
                """,
                id,
            )

        return cast(FullSubmission | None, submission)

    async def submission_by_image(self, image_url: str) -> FullSubmission | None:
        async with self.pool.acquire() as conn:
            submission: asyncpg.Record | None = await conn.fetchrow(
                f"""
                SELECT {SUBMISSION_FIELDS}
                FROM submissions
                WHERE image_url = $1
                """,
                image_url,
            )

        return cast(FullSubmission | None, submission)

    async def submission_by_prompt(self, user_id: int, prompt_id: int) -> FullSubmission | None:
        async with self.pool.acquire() as conn:
            submission: asyncpg.Record | None = await conn.fetchrow(
                f"""
                SELECT {SUBMISSION_FIELDS}
                FROM submissions
                WHERE user_id = $1 AND prompt_id = $2
                """,
                user_id,
                prompt_id,
            )

        return cast(FullSubmission | None, submission)

    async def submission_from_queue(self, message_id):
        async with self.pool.acquire() as conn:
            submission: asyncpg.Record | None = await conn.fetchrow(
                f"""
                SELECT {SUBMISSION_FIELDS}
                FROM submissions
                WHERE queue_message_id = $1
                """,
                message_id,
            )

        return cast(FullSubmission | None, submission)

    async def submissions_with_status(
        self,
        status: SubmissionStatus,
        user_id: int,
    ) -> list[FullSubmission]:
        async with self.pool.acquire() as conn:
            submissions: list[asyncpg.Record] = await conn.fetch(
                f"""
                SELECT {SUBMISSION_FIELDS}
                FROM submissions
                WHERE user_id = $1 AND status = $2
                """,
                user_id,
                status.value,
            )

        return cast(list[FullSubmission], submissions)

    async def post_statistics(self, link: str, data: UserData | list[BasicSubmissionInfo]) -> None:
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

        approved_submissions: list[FullSubmission] = await self.bot.get_cog(EventData).submissions_with_status(
            SubmissionStatus.APPROVED, user.id
        )

        await self.post_statistics(
            link, [{'prompt_id': submission['prompt_id'], 'image_url': submission['image_url']} for submission in approved_submissions]
        )


setup = EventData.setup
