import datetime
import asyncio

import asyncpg
import discord
from discord.ext import commands
from discord.ext.commands import Bot

from .daily import do_daily
from .config import Config

class CalendarBot(Bot):
    def __init__(self, config_file):
        self.c = Config(config_file)
        super().__init__(command_prefix = commands.when_mentioned_or(self.c.prefix), owner_id = self.c.owner_id)

    @classmethod
    def with_config(cls, config_file='config.yaml'):
        calendarbot = cls(config_file)

        return calendarbot

    @property
    def topic(self):
        accepted_days = [f'{self.c.get_prompt(i)} ({i})' for i in self.c.get_allowed_days(datetime.datetime.utcnow()) if i != 0]

        accepted_days[-1] = f'and {accepted_days[-1]}' if len(accepted_days) > 1 else accepted_days[-1]

        topic_format = 'Currently accepting prompt{s}: {days}'

        return topic_format.format(s=['', 's'][len(accepted_days) > 1], days=', '.join(accepted_days))

    async def daily_submission_channel_news(self):
        guild = self.get_guild(self.c.guild_id)
        submission_channel = guild.get_channel(self.c.guild_id)

        await self.update_submission_channel_topic()

        accepted_days = ' '.join([f'{self.c.get_prompt(i)} ({i})' for i in self.c.get_allowed_days(datetime.datetime.utcnow()) if
                         i != 0])

        # await submission_channel.send(f"It's a new day! Today's prompts are: **{accepted_days}**")


    async def update_submission_channel_topic(self):
        await asyncio.sleep(1)
        guild = self.get_guild(self.c.guild_id)

        submission_channel: discord.TextChannel = guild.get_channel(self.c.submission_channel_id)

        await submission_channel.edit(reason="Daily channel update",
                                      topic=self.topic)

        info_message = await submission_channel.fetch_message(self.c.info_message_id)
        prompt_list_message = await submission_channel.fetch_message(self.c.prompt_list_message_id)

        embed = discord.Embed(title="Today's prompts", description="Green highlighted prompts are currently allowed to be submitted.", color=self.c.embed_color)
        days_since_month_started = (datetime.datetime.utcnow() - datetime.datetime(day=1, month=self.c.month, year=self.c.year)+datetime.timedelta(days=1)).days
        embed.set_image(url=self.c.get_prompts_image_link(days_since_month_started))

        prompt_list_text = '**Revealed prompts:**\n' + "\n".join(f'{i}. {self.c.get_prompt(i)}' for i in range(1, days_since_month_started+2))

        await info_message.edit(embed=embed)
        await prompt_list_message.edit(content=prompt_list_text)




    def run(self, token=None):
        cogs = ['jishaku', 'bot.cogs.queue']

        for cog in cogs:
            self.load_extension(cog)

        if not token:
            token = self.c.get_token()

        self.can_start_daily = True

        super().run(token)


    async def on_ready(self):
        if not  self.can_start_daily:
            return

        await asyncio.sleep(10)

        self.can_start_daily = False

        await self.update_submission_channel_topic()

        await do_daily(self.daily_submission_channel_news, datetime.time(0, 0, 0, 0))

        self.can_start_daily = True


    async def start(self, *args, **kwargs):
        self.pool= await asyncpg.create_pool(**self.c.get_postgres_args())

        return await super().start(*args, **kwargs)
