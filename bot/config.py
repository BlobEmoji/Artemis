import datetime
import itertools

import ruamel.yaml


with open('config.yaml', encoding='utf-8') as file:
    data = ruamel.yaml.safe_load(file)

token = data['bot']['token']

event_guild_id = data['discord']['guild_id']
info_message_id = data['discord']['info_message_id']
prompt_list_message_id = data['discord']['prompt_list_message_id']
queue_channel_id = data['discord']['queue_channel_id']
submission_channel_id = data['discord']['submission_channel_id']
gallery_channel_id = data['discord']['gallery_channel_id']
embed_color = data['discord']['embed_color']
event_role_id = data['discord']['event_role_id']

start_day = data['start_day']

prompts = data['prompts']
prompts_image_links = data['prompts_image_links']
