# -*- coding: utf-8 -*-

from pathlib import Path
import atexit
import datetime as dt
import json
import sys
# import logging
import logging.config
import logging.handlers
from typing import override


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

# class UTF8StreamHandler(logging.StreamHandler):
#     def __init__(self, stream=None):
#         super().__init__(stream=stream)
#         if stream is None:
#             stream = sys.stdout
#         # Remove the fileno part and use the stream directly.
#         self.stream = stream


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


class SetupLogging:
    '''
    :config_path: json configuration file. See samples in ./config
    :log_dir: output logs
    The Json file needs to match the functions and classes of this module
    '''
    def __init__(self, config_path = None, log_dir = None):
        self.config_path = config_path
        self.log_dir = log_dir

        self.cwd = Path(__file__).resolve().parent

        if not self.config_path:
            self.config_path =  self.cwd / 'logging.json'
        print(f"log config path: {self.config_path}")

        if not self.log_dir:
            self.log_dir = self.cwd.parent / 'logs'
            self.log_dir.mkdir(parents=True, exist_ok=True)
        print(f"log output directory: {self.log_dir}")

        self.log = logging.getLogger()
        self._setup()
        
        self.set_loglevel()


    def set_loglevel(self, level:str='DEBUG'):
        """ :level: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] """                
        pass
        # Not possible yet
        # otherwise the log level is configurable in the logging file


    def _setup(self):
        """ :config: json file path """

        with open(self.config_path, 'r') as f:
            config = json.load(f)
        try:
            logging.config.dictConfig(config)
        except ValueError as err:
            print(f"ValueError: {err}. The json config file has mistakes. Check referenced files path...")

        queue_handler = logging.getHandlerByName("queue_handler")
        if queue_handler is not None:
            queue_handler.listener.start()
            atexit.register(queue_handler.listener.stop)


if __name__ == '__main__':
    # use it like this
    mylogger = SetupLogging()
    log = mylogger.log
    
    print('test')
    log.debug("test")
    log.info("test")
    log.warning("test")
    log.error("test")
    log.critical("test")
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("exception message")
        
        