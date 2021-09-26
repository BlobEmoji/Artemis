import ruamel.yaml


with open('config.yaml', encoding='utf-8') as file:
    data = ruamel.yaml.safe_load(file)

# Bot
token = data['bot']['token']

# Event Guild & Channels
event_guild_id = data['discord']['guild_id']
queue_channel_id = data['discord']['queue_channel_id']
submission_channel_id = data['discord']['submission_channel_id']
gallery_channel_id = data['discord']['gallery_channel_id']

#Event Info
event_name = data['discord']['event_name']

# Event Info Messages
info_message_id = data['discord']['info_message_id']
current_prompts_message_id = data['discord']['current_prompts_message_id']

# Event Role
event_role_id = data['discord']['event_role_id']

# Event Embed Color
embed_color = data['discord']['embed_color']

# Event Schedule Info
start_day = data['start_day']
end_day = data['end_day']
days_per_prompt = data['days_per_prompt']

# Event Prompts
prompts = data['prompts']
prompts_image_links = data['prompts_image_links']
