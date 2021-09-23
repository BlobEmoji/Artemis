from discord.ext import commands
import discord

from common import url_extractor

from bot import CalendarBot
from bot import Config

from common import get_gallery_embed

async def process_queue(bot:CalendarBot, im_link, message):
    guild = bot.get_guild(bot.c.guild_id)
    queue_channel = guild.get_channel(bot.c.queue_channel_id)
    e = discord.Embed(description=(message.content+'\n\n' if message.content else '')+f'**>** [Link to original post]({message.jump_url})').set_image(url=im_link)

    in_queue = await bot.pool.fetchval("""
        SELECT in_queue FROM submissions
        WHERE image_link = $1;
    """, im_link)

    if not in_queue:
        queue_message = await queue_channel.send(embed=e)

        if in_queue == False:
            await bot.pool.execute("""
            UPDATE submissions
            SET queue_post_id = $1,
                in_queue = true
            WHERE
                image_link = $2
            """, queue_message.id, im_link)
        else:
            await bot.pool.execute("""
            INSERT INTO submissions(user_id, user_post_id, queue_post_id, image_link)
            VALUES
            ($1, $2, $3, $4);
            """, message.author.id, message.id, queue_message.id, im_link)

        [await queue_message.add_reaction(i) for i in bot.c.get_emojis(0).values()]

class Queue(commands.Cog):
    def __init__(self, bot:CalendarBot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if self.bot.c.submission_channel_id != message.channel.id:
            return
        images = url_extractor.findall(message.clean_content) + [a.url for a in message.attachments]
        for i in images:
            await process_queue(self.bot, i, message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.channel_id == self.bot.c.submission_channel_id:
            guild = self.bot.get_guild(self.bot.c.guild_id)
            channel = guild.get_channel(self.bot.c.queue_channel_id)
            submissions = await self.bot.pool.fetch('''
                SELECT * FROM submissions
                WHERE 
                    user_post_id = $1
            ''', payload.message_id)

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
                        await self.bot.pool.execute("""
                            UPDATE submissions
                            SET in_queue = false,
                                approved = false
                            WHERE
                                image_link = $1
                        """, submission['image_link'])
                else:
                    if submission['gallery_post_id']:
                        msg = await channel.fetch_message(submission['gallery_post_id'])
                        await msg.delete()
                        await self.bot.pool.execute("""
                        UPDATE submissions
                        SET in_queue = false,
                            approved = false
                        WHERE
                            image_link = $1
                        """, submission['image_link'])


    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        guild = self.bot.get_guild(self.bot.c.guild_id)
        channel = guild.get_channel(self.bot.c.submission_channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.errors.NotFound:
            return

        images = url_extractor.findall(message.clean_content) + [a.url for a in message.attachments]

        for i in images:
            await process_queue(self.bot, i, message)

    async def reaction_interface(self, emoji: str, message: discord.Message, reactor: discord.User):
        if message.channel.id != self.bot.c.queue_channel_id:
            return
        elif reactor.id == self.bot.user.id:
            return

        submission = await self.bot.pool.fetchrow("""
        SELECT * FROM submissions
        WHERE queue_post_id = $1;
        """, message.id)

        if not submission:
            return

        if not submission['in_queue']:
            return

        submitter = message.guild.get_member(submission['user_id'])

        author_msg: discord.Message = await message.guild.get_channel(self.bot.c.submission_channel_id).fetch_message(
            submission['user_post_id'])

        if self.bot.c.get_stage(emoji)== 0:
            converted = self.bot.c.translate(emoji)
            if submission['approved']:
                return
            if converted == 'yes':
                await self.bot.pool.execute("""
                UPDATE submissions
                SET approved = TRUE,
                    approver_id = $1
                WHERE
                    queue_post_id = $2;
                """, reactor.id, message.id)
                await message.clear_reactions()
                usable_emoji = zip(self.bot.c.get_emojis(1).values(), self.bot.c.get_allowed_days(message.created_at))
                [await message.add_reaction(i) for i, j in usable_emoji if j]
            elif converted in ['no', 'na']:
                await self.bot.pool.execute("""
                UPDATE submissions
                SET approved = FALSE,
                    in_queue = FALSE,
                    approver_id = $1
                WHERE
                    queue_post_id = $2;
                """, message.author.id, message.id)
                await message.delete()
            if converted == 'no':
                await author_msg.author.send(
                    "Your submission was denied. Here's a picture of it, so you know which one to resubmit. If you don't know why it was denied, maybe try asking, although the most common ones are that you either didn't put a date for it, or that you didn't put enough effort in.",
                    embed=discord.Embed().set_image(url=submission['image_link'])
                )

                await author_msg.add_reaction(self.bot.c.get_emoji('no'))

        elif self.bot.c.get_stage(emoji) == 1:

            time = self.bot.c.get_allowed_days(author_msg.created_at)

            date = None
            if self.bot.c.translate(emoji) == 'backward':
                date = time[0]
            elif self.bot.c.translate(emoji) == 'default':
                date = time[1]
            elif self.bot.c.translate(emoji) == 'forward':
                date = time[2]

            if date:
                await self.bot.pool.execute("""
                UPDATE submissions
                SET day_num = $1,
                    identifier_id = $2
                WHERE
                    queue_post_id = $3;
                """, date, reactor.id, message.id)
            else:
                return


            await message.edit(content=f'{author_msg.author.name}: {date} ({self.bot.c.get_prompt(date)})')
            [await message.add_reaction(i) for i in self.bot.c.get_emoji('lock')]
        elif self.bot.c.get_stage(emoji) == 2:
            day = await self.bot.pool.fetchval("""
                SELECT day_num FROM submissions
                WHERE 
                    queue_post_id = $1;
                """, message.id)
            if not day:
                return
            e = await get_gallery_embed(self.bot, submission['image_link'])
            gallery_channel = message.guild.get_channel(self.bot.c.gallery_channel_id)

            gallery_msg = await gallery_channel.send(embed=e)

            await message.delete()

            await self.bot.pool.execute("""
            UPDATE submissions
            SET in_queue = false,
                gallery_post_id = $1
            WHERE
                queue_post_id = $2;
            """, gallery_msg.id, message.id)

            await author_msg.add_reaction(self.bot.c.get_emoji('yes'))

            # owo
            submissions_by_user = await self.bot.pool.fetch('''
                    SELECT approved FROM submissions
                    WHERE
                        user_id = $1
                ''', submission['user_id'])

            approved = sum(sub['approved'] for sub in submissions_by_user)


            if approved >= 10:
                role = gallery_msg.guild.get_role(self.bot.c.festive_role_id)

                member = gallery_msg.guild.get_member(submission['user_id'])

                if role.id in [r.id for r in member.roles]:
                    return
                else:
                    await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild: discord.Guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel: discord.TextChannel = guild.get_channel(payload.channel_id)
        user: discord.User = self.bot.get_user(payload.user_id)
        message: discord.Message = await channel.fetch_message(payload.message_id)


        emoji = payload.emoji

        if emoji.is_custom_emoji():
            string_form = '<{a}:{name}:{id}>'.format(
                a=['','a'][emoji.animated],
                name=emoji.name,
                id=emoji.id)
        else:
            string_form = str(emoji)

        await self.reaction_interface(
            string_form, message, user
        )

def setup(bot):
    bot.add_cog(Queue(bot))

