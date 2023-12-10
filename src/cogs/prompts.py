import datetime
import math
import time

from .. import ArtemisCog, config


info_message_format: str = f"""
Welcome to {config.event_name} {config.start_day.year}!

In this event, a pair of prompts are revealed every {config.days_per_prompt} days, \
and you may either pick one of them or mix them together to inspire your artwork. \
Once created, you can submit it here in order to get it displayed in the gallery channel! \
Each submission counts as one ticket for a raffle that will be done later.
"""


class Prompts(ArtemisCog):
    @property
    def current_day(self) -> int:
        return (datetime.datetime.now().date() - config.start_day).days

    @property
    def current_prompt(self) -> str | None:
        try:
            return config.prompts[self.current_prompt_id]
        except IndexError:
            return None

    @property
    def current_prompt_id(self) -> int:
        return self.current_day // config.days_per_prompt

    @property
    def current_prompt_timestamp(self) -> int:
        end_timestamp: int = math.floor(time.mktime(config.end_day.timetuple()))
        prompt_timestamp: int = math.floor(time.mktime(config.start_day.timetuple())) + (
            (86400 * config.days_per_prompt) * (self.current_prompt_id + 1)
        )
        return min(prompt_timestamp, end_timestamp)

    @property
    def before_event(self) -> bool:
        return datetime.datetime.now().date() < config.start_day

    @property
    def during_event(self) -> bool:
        return config.start_day <= datetime.datetime.now().date() <= config.end_day

    @property
    def after_event(self) -> bool:
        return config.end_day < datetime.datetime.now().date()

    def prompt_text(self, prompt_id: int):
        return f'"{config.prompts[prompt_id]}" (#{prompt_id + 1})'

    def get_topic(self) -> str:
        prompt_message: str

        if self.before_event:
            prompt_message = f'Event starts on {config.start_day}.'
        elif self.during_event:
            prompt_message = (
                f'Newest Prompt: {self.prompt_text(self.current_prompt_id)}.\n'
                f'The next prompt reveal is at <t:{self.current_prompt_timestamp}>'
            )
        else:
            prompt_message = 'The event has ended. Thanks for participating!'

        return f'{prompt_message}\nCheck pins for more info.'

    def get_info_message(self) -> str:
        past_prompts: str = "\n".join(f'{i+1}. {config.prompts[i]}' for i in range(self.current_prompt_id) if i < len(config.prompts))

        info_message: str = info_message_format

        if self.before_event:
            info_message += f'The event starts on {config.start_day}! Come back then!'
        elif self.during_event:
            info_message += (
                f'The newest prompt is {self.prompt_text(self.current_prompt_id)}!\n'
                f'The next prompt reveal is at <t:{self.current_prompt_timestamp}>'
            )
        else:
            info_message += f'All prompts have been revealed!'

        if past_prompts:
            info_message += f'\n\nPrompts:\n{past_prompts}'

        return info_message


setup = Prompts.setup
