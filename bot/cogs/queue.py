import discord
from discord.ext import commands

from bot import CalendarBot
from common import get_gallery_embed, url_extractor

from .. import config


async def process_queue(bot: CalendarBot, im_link, message):
    guild = bot.get_guild(config.event_guild_id)
    queue_channel = guild.get_channel(config.queue_channel_id)
    e = discord.Embed(
        description=(message.content + '\n\n' if message.content else '')
        + f'**>** [Link to original post]({message.jump_url})'
    ).set_image(url=im_link)

    in_queue = await bot.pool.fetchval(
        """
        SELECT in_queue FROM submissions
        WHERE image_link = $1;
    """,
        im_link,
    )

    if not in_queue:
        queue_message = await queue_channel.send(embed=e)

        if in_queue == False:
            await bot.pool.execute(
                """
            UPDATE submissions
            SET queue_post_id = $1,
                in_queue = true
            WHERE
                image_link = $2
            """,
                queue_message.id,
                im_link,
            )
        else:
            await bot.pool.execute(
                """
            INSERT INTO submissions(user_id, user_post_id, queue_post_id, image_link)
            VALUES
            ($1, $2, $3, $4);
            """,
                message.author.id,
                message.id,
                queue_message.id,
                im_link,
            )

        [await queue_message.add_reaction(i) for i in [config.na_emoji, config.yes_emoji, config.no_emoji]]


class Queue(commands.Cog):
    def __init__(self, bot: CalendarBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if config.submission_channel_id != message.channel.id:
            return
        images = url_extractor.findall(message.clean_content) + [a.url for a in message.attachments]
        for i in images:
            await process_queue(self.bot, i, message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.channel_id == config.submission_channel_id:
            guild = self.bot.get_guild(config.event_guild_id)
            channel = guild.get_channel(config.queue_channel_id)
            submissions = await self.bot.pool.fetch(
                '''
                SELECT * FROM submissions
                WHERE 
                    user_post_id = $1
            ''',
                payload.message_id,
            )

            for submission in submissions:
                if submission['in_queue']:
                    msg = None
                    try:
                        msg = await channel.fetch_message(submission['queue_post_id'])
                    except:
                        pass
                    finally:
                        if msg:
                            await msg.delete()
                        await self.bot.pool.execute(
                            """
                            UPDATE submissions
                            SET in_queue = false,
                                approved = false
                            WHERE
                                image_link = $1
                        """,
                            submission['image_link'],
                        )
                else:
                    if submission['gallery_post_id']:
                        msg = await channel.fetch_message(submission['gallery_post_id'])
                        await msg.delete()
                        await self.bot.pool.execute(
                            """
                        UPDATE submissions
                        SET in_queue = false,
                            approved = false
                        WHERE
                            image_link = $1
                        """,
                            submission['image_link'],
                        )

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        guild = self.bot.get_guild(config.event_guild_id)
        channel = guild.get_channel(config.submission_channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.errors.NotFound:
            return

        images = url_extractor.findall(message.clean_content) + [a.url for a in message.attachments]

        for i in images:
            await process_queue(self.bot, i, message)


def setup(bot):
    bot.add_cog(Queue(bot))
