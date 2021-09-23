import datetime
import itertools

import ruamel.yaml

class Config:
    def __init__(self, file:str='config.yaml'):
        self.file = file

        with open(file, encoding='utf-8') as f:
            self._data = ruamel.yaml.safe_load(f)

        self.emojis = {i: j for i, j in itertools.chain(*[list(i.items()) for i in self._data['emojis']])}

    def get_allowed_days(self, now:datetime.datetime):

        before = now - datetime.timedelta(days=1)
        after = now + datetime.timedelta(days=1)

        return [(i.day if i.month == self._data['month'] else 0) for i in [before, now, after]]

    def get_prompt(self, day):
        try:
            return self._data['prompts'][day-1]
        except IndexError:
            return self._data['prompts'][-1]

    @property
    def month(self):
        return self._data['month']

    def get_prompts_image_link(self, day):
        try:
            return self._data['prompts_image_links'][day-1]
        except:
            return self._data['prompts_image_links'][-1]

    @property
    def festive_role_id(self):
        return self._data['discord']['festive_role_id']

    def get_token(self):
        return self._data['bot']['token']

    @property
    def guild_id(self):
        return self._data['discord']['guild_id']

    @property
    def submission_channel_id(self):
        return self._data['discord']['submission_channel_id']

    @property
    def queue_channel_id(self):
        return self._data['discord']['queue_channel_id']

    @property
    def gallery_channel_id(self):
        return self._data['discord']['gallery_channel_id']

    @property
    def prefix(self):
        return self._data['bot']['prefix']

    @property
    def owner_id(self):
        return self._data['bot']['owner_id']

    @property
    def year(self):
        return self._data['year']

    @property
    def info_message_id(self):
        return self._data['discord']['info_message_id']

    @property
    def embed_color(self):
        return self._data['discord']['embed_color']

    @property
    def prompt_list_message_id(self):
        return self._data['discord']['prompt_list_message_id']

    def get_postgres_args(self):
        return self._data['postgres']

    def get_emoji(self, emoji_name):
        return self.emojis[emoji_name]

    def get_emojis(self, stage):
        return self._data['emojis'][stage]

    def get_stage(self, emoji):
        if emoji in self.emojis.values():
            for i, stage in enumerate(self._data['emojis']):
                reverse = [j==emoji for i, j in stage.items()]

                if sum(reverse):
                    return i

    def translate(self, emoji):
        inverse = {j: i for i, j in self.emojis.items()}

        return inverse[emoji]
