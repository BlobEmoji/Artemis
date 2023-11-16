import datetime
from typing import Any, TypeVar

import discord
from discord.ext import commands
from ruamel.yaml import YAML

from .errors import ConfiguredResourceNotFound


with YAML(typ='safe', pure=True) as yaml:
    with open('config.yaml', encoding='utf-8') as file:
        data: dict = yaml.load(file)

# Bot
token: str = data['bot']['token']

# Event Guild & Channels
event_guild_id: int = data['discord']['guild_id']
queue_channel_id: int = data['discord']['queue_channel_id']
submission_channel_id: int = data['discord']['submission_channel_id']
gallery_channel_id: int = data['discord']['gallery_channel_id']

# Event Info
event_name: str = data['discord']['event_name']

# Event Info Messages
info_message_id: int = data['discord']['info_message_id']
current_prompts_message_id: int = data['discord']['current_prompts_message_id']

# Event Role
event_role_id: int = data['discord']['event_role_id']
event_role_requirement: int = data['event_role_requirement']

# Event Embed Color
embed_color: int = data['discord']['embed_color']

# Event Schedule Info
start_day: datetime.date = data['start_day']
end_day: datetime.date = data['end_day']
days_per_prompt: int = data['days_per_prompt']

# Event Prompts
prompts: list[str] = data['prompts']
prompts_image_links: list[str] = data['prompts_image_links']

# Statistics endpoint
statistics_authorization: str | None = data['statistics_authorization']


class EventBot(commands.Bot):
    def __get_text_channel(self, field_name: str, channel_id: int) -> discord.TextChannel:
        channel = self.get_channel(channel_id)

        if not isinstance(channel, discord.TextChannel):
            raise ConfiguredResourceNotFound(field_name, channel_id)

        return channel

    @property
    def event_guild(self) -> discord.Guild:
        guild: discord.Guild | None = self.get_guild(event_guild_id)

        if guild is None:
            raise ConfiguredResourceNotFound('event_guild_id', event_guild_id)

        return guild

    @property
    def queue_channel(self) -> discord.TextChannel:
        return self.__get_text_channel('queue_channel', queue_channel_id)

    @property
    def submission_channel(self) -> discord.TextChannel:
        return self.__get_text_channel('submission_channel', submission_channel_id)

    @property
    def gallery_channel(self) -> discord.TextChannel:
        return self.__get_text_channel('gallery_channel', gallery_channel_id)
