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

    async def upload_file_to_cdn(self, file_data: bytes, extension: str) -> str:
        assert config.image_uploading_authorization is not None

        headers = {
            'Content-Type': f'image/{extension}',
            'Authorization': config.image_uploading_authorization,
        }

        async with self.bot.session.post(config.image_uploading_endpoint, headers=headers, data=file_data) as resp:
            data = await resp.json()

        return data['url']

    def upload_image_to_discord(self, file_data: bytes, filename: str, guild: discord.Guild | None) -> discord.File:
        size_limit: int = guild.filesize_limit if guild is not None else discord.utils.DEFAULT_FILE_SIZE_LIMIT_BYTES

        size = len(file_data)
        if size > size_limit:
            raise FilesizeLimitException(size, size_limit)
        else:
            return discord.File(io.BytesIO(file_data), filename)

    async def attempt_double_reupload(self, name: str, url: str, guild: discord.Guild | None) -> tuple[str, discord.File]:
        upload_url: str = url
        file: discord.File = discord.utils.MISSING

        async with self.bot.session.get(url) as resp:
            file_data: bytes = await resp.read()

        try:
            extension: str = self.get_file_extension(url)

            upload_url: str = await self.upload_file_to_cdn(file_data, extension)
            file = self.upload_image_to_discord(file_data, f'{name}.{extension}', guild)
        except (NoExtensionFound, FilesizeLimitException):
            pass

        return (upload_url, file)

    def upload_image(self, name: str, image: Image.Image) -> discord.File:
        data: io.BytesIO = io.BytesIO()
        image.save(data, format='png')
        data.seek(0)

        return discord.File(data, f'{name}.png')


setup = FileUtils.setup
