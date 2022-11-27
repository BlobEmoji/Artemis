import datetime
from typing import Any

import ruamel.yaml


with open('config.yaml', encoding='utf-8') as file:
    data: dict = ruamel.yaml.safe_load(file)

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
