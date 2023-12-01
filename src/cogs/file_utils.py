import io
import re

import discord
from PIL import Image

from .. import ArtemisCog, config
from ..errors import FilesizeLimitException, NoExtensionFound


class FileUtils(ArtemisCog):
    def get_file_extension(self, url: str) -> str:
        extension = re.match(r'.*\.([\w\d]+)', url)

        if extension is None:
            raise NoExtensionFound(url)

        return extension.group(1)

    async def upload_image_to_cdn(self, image: bytes, extension: str) -> str:
        assert config.image_uploading_authorization is not None

        headers = {
            'Content-Type': f'image/{extension}',
            'Authorization': config.image_uploading_authorization,
        }

        async with self.bot.session.post(config.image_uploading_endpoint, headers=headers, data=image) as resp:
            data = await resp.json()

        return data['url']

    async def attempt_reupload(self, name: str, url: str) -> str:
        upload_url: str = url

        async with self.bot.session.get(url) as resp:
            image: bytes = await resp.read()

        try:
            upload_url: str = await self.upload_image_to_cdn(image, self.get_file_extension(url))
        except NoExtensionFound:
            pass

        return upload_url

    def upload_image(self, name: str, image: Image.Image) -> discord.File:
        data: io.BytesIO = io.BytesIO()
        image.save(data, format='png')
        data.seek(0)

        return discord.File(data, f'{name}.png')


setup = FileUtils.setup
