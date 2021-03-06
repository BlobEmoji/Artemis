import datetime
import math
import time

from discord.ext import commands

from .. import Artemis, config


info_message_format = f"""
Welcome to {config.event_name} {config.start_day.year}!

In this event, a pair of prompts are revealed every {config.days_per_prompt} days, and you may either pick ony one of them or mix them together in order to make an artwork of it. You can submit it here in order to get it displayed in the gallery channel! Each submission counts as one ticket for a raffle that will be done later.

"""


class Prompts(commands.Cog):
    def __init__(self, bot: Artemis):
        self.bot = bot

    @property
    def current_day(self):
        return (datetime.datetime.now().date() - config.start_day).days

    @property
    def current_prompt(self):
        try:
            return config.prompts[self.current_prompt_number]
        except IndexError:
            return None

    @property
    def current_prompt_number(self):
        return self.current_day // config.days_per_prompt

    @property
    def current_prompt_timestamp(self):
        end_timestamp = math.floor(time.mktime(config.end_day.timetuple()))
        prompt_timestamp = math.floor(time.mktime(config.start_day.timetuple())) + ((86400 * config.days_per_prompt) * (self.current_prompt_number + 1))
        return min(prompt_timestamp, end_timestamp)

    @property
    def before_event(self):
        return datetime.datetime.now().date() < config.start_day

    @property
    def during_event(self):
        return config.start_day <= datetime.datetime.now().date() <= config.end_day

    @property
    def after_event(self):
        return config.end_day < datetime.datetime.now().date()

    def get_topic(self):
        if self.before_event:
            prompt_message = f'Event starts on {config.start_day}.'
        elif self.during_event:
            prompt_message = f'Current Prompt: {self.current_prompt} (#{self.current_prompt_number + 1}).'
            prompt_message += f'\nThe deadline is <t:{self.current_prompt_timestamp}>\n\n'
        else:
            prompt_message = 'The event has ended. Thanks for participating!'

        return f'{prompt_message}\nCheck pins for more info.'

    def get_info_message(self):
        past_prompts = "\n".join(
            f'{i+1}. {config.prompts[i]}' for i in range(self.current_prompt_number) if i < len(config.prompts)
        )

        info_message = info_message_format

        if self.before_event:
            info_message += f'The event starts on {config.start_day}! Come back then!\n\n'
        elif self.during_event:
            info_message += f'The current prompt is {config.prompts[self.current_prompt_number]}!\n'
            info_message += f'The deadline is <t:{self.current_prompt_timestamp}>\n\n'
        else:
            info_message += f'The event has ended. Thanks for participating!\n\n'

        if past_prompts:
            info_message += f'Previous Prompts:\n{past_prompts}'

        return info_message


def setup(bot):
    return bot.add_cog(Prompts(bot))
