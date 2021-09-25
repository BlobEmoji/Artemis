import datetime
import asyncio

import asyncpg
from discord.ext import commands
from discord.ext.commands import Bot

from .daily import do_daily
from .config import token, prompts, start_day

class CalendarBot(Bot):
    def __init__(self):
        super().__init__(command_prefix='f!')

    @property
    def topic(self):
        current_day = (datetime.datetime.utcnow().date() - start_day).days

        accepted_days = [f'{prompts[i]} ({i})' for i in range(current_day-1, current_day+2) if prompts.get(i) is not None]

        accepted_days[-1] = f'and {accepted_days[-1]}' if len(accepted_days) > 1 else accepted_days[-1]

        topic_format = 'Currently accepting prompt{s}: {days}'

        return topic_format.format(s=['', 's'][len(accepted_days) > 1], days=', '.join(accepted_days))

    def run(self):
        cogs = ['jishaku', 'bot.cogs.queue']

        for cog in cogs:
            self.load_extension(cog)

        self.can_start_daily = True

        super().run(token)


    async def on_ready(self):
        if not  self.can_start_daily:
            return

        await asyncio.sleep(10)

        self.can_start_daily = False



    async def start(self, *args, **kwargs):
        await asyncio.sleep(1)
        self.pool= await asyncpg.create_pool(user="postgres", host="db")

        return await super().start(*args, **kwargs)
