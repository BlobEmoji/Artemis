from typing import Any


class NoExtensionFound(Exception):
    pass


class FilesizeLimitException(Exception):
    pass


class ConfiguredResourceNotFound(Exception):
    def __init__(self, field_name: str, value: Any):
        super().__init__(f'Failed to find the resource with ID `{value}` for {field_name}.')
