import io
import re

import discord
from discord.ext import commands

from .. import ArtemisCog
from ..errors import FilesizeLimitException, NoExtensionFound


class FileUtils(ArtemisCog):
    def get_file_extension(self, url: str) -> str:
        extension = re.match(r'.*\.([\w\d]+)', url)

        if extension is None:
            raise NoExtensionFound(url)

        return extension.group(1)

    async def attempt_reupload(self, name: str, url: str, guild: discord.Guild | None) -> tuple[str, discord.File]:
        file: discord.File = discord.utils.MISSING
        upload_url: str = url

        size_limit: int = guild.filesize_limit if guild is not None else discord.utils.DEFAULT_FILE_SIZE_LIMIT_BYTES

        async with self.bot.session.get(url) as resp:
            size: int = int(resp.headers['Content-Length'])

            try:
                if size >= size_limit:
                    raise FilesizeLimitException(size, size_limit)

                file_name = f'{name}.{self.get_file_extension(url)}'
                data: io.BytesIO = io.BytesIO(await resp.read())

                file = discord.File(data, file_name)
                upload_url = f'attachment://{file_name}'
            except (NoExtensionFound, FilesizeLimitException):
                pass

        return (upload_url, file)


setup = FileUtils.setup
