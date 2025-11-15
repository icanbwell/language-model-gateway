import logging
from typing import Any, override


class EndpointFilter(logging.Filter):
    def __init__(
        self,
        path: str,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._path = path

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find(self._path) == -1
