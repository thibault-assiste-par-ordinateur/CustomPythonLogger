# -*- coding: utf-8 -*-

from pathlib import Path
import atexit
import datetime as dt
import json
import sys
import logging
from typing import override

__all__ = ['setup_logging', 'log']

LOG_RECORD_BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}

class UTF8StreamHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        super().__init__(stream=stream)
        self.stream = open(stream.fileno(), 'w', encoding='utf-8', buffering=1)

class MyJSONFormatter(logging.Formatter):
    def __init__(
        self,
        *,
        fmt_keys: dict[str, str] | None = None,
    ):
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}

    @override
    def format(self, record: logging.LogRecord) -> str:
        message = self._prepare_log_dict(record)
        return json.dumps(message, ensure_ascii=False, default=str)

    def _prepare_log_dict(self, record: logging.LogRecord):
        always_fields = {
            "message": record.getMessage(),
            "timestamp": dt.datetime.fromtimestamp(
                record.created, tz=dt.timezone.utc
            ).isoformat(),
        }
        if record.exc_info is not None:
            always_fields["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info is not None:
            always_fields["stack_info"] = self.formatStack(record.stack_info)

        message = {
            key: msg_val
            if (msg_val := always_fields.pop(val, None)) is not None
            else getattr(record, val)
            for key, val in self.fmt_keys.items()
        }
        message.update(always_fields)

        for key, val in record.__dict__.items():
            if key not in LOG_RECORD_BUILTIN_ATTRS:
                message[key] = val

        return message

class NonErrorFilter(logging.Filter):
    @override
    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        return record.levelno <= logging.INFO


def setup_logging(config: None):
    """ :config: au format json """
    
    if not config:
        # si aucun fichier config n'est précisé, 
        # utiliser le fichier dans le dossier config
        config = Path(__file__).resolve().parent / 'config' / 'logging.json'
    
    with open(config, 'r') as f_in:
        config = json.load(f_in)
        
    logging.config.dictConfig(config)

    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)

log = logging.getLogger()
