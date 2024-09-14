# -*- coding: utf-8 -*-

from pathlib import Path
import atexit
import datetime as dt
import json
import sys
import logging.config
import logging.handlers
from typing import override

__all__ = ['SetupLogging', 'DisplayJsonLogs']

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

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
    """ Classic Stream handler that also handles UTF8 syntax"""
    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        super().__init__(stream=stream)
        self.stream = open(stream.fileno(), 'w', encoding='utf-8', buffering=1)

class MyJSONFormatter(logging.Formatter):
    """ Format logs into a .jsonl format"""
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
    """ Do not display non error messages twice in stdout"""
    @override
    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        return record.levelno <= logging.INFO

class SetupLogging:
    '''
    Custom logging from json file. The configuration is very specific. Check the json sample in ../config/logging.json
    :param log_dir: required file path to output the log files.
    :param config_path: (optional) json configuration file for logging. A default configuration is provided in ../config. It can be overwritten passing a new path. In such a case, note that the Json file needs to match the functions and classes of this module
    '''
    def __init__(self, output_path:str, config_path:str = None):
        
        self.log = logging.getLogger()
        self.config_path = self._init_config_path(config_path)        
        self.queue_handler = self._setup()

        self.output_path = self._init_output_path(output_path)
        self.set_logfile( self.output_path )

    def _init_output_path(self, path):
        """ Make sure the specified output path exists and has a .jsonl extension"""
        if not path:
            print("WARNING: wrong log file output.")
        else:
            path = Path(path)
            # ensure file extension is .jsonl
            if path.suffix != '.jsonl':
                path.with_suffix('.jsonl')
            # ensure the parent directories exist, if not create them
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _init_config_path(self, path):
        """ If the user did not specify a config path, use default one"""
        if not path:
            parent_dir = Path(__file__).resolve().parent.parent
            path =  parent_dir / 'config' / 'logging.json'
        print(f"log config path: {path}")
        return path

    def set_loglevel(self, level: str = 'INFO'):
        """Set the logging level for the stdout handler.
        :param level: Logging level (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        """
        # Convert the level string to logging level value
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {level}")

        if isinstance(self.queue_handler, logging.handlers.QueueHandler):
            # Access the handlers managed by the QueueListener
            for listener in self.queue_handler.listener.handlers:
                if isinstance(listener, UTF8StreamHandler) and listener.stream.name == 1: # stdout is 1, stderr is 2 
                    # Set the new log level for the stdout handler
                    listener.setLevel(numeric_level)
                    print(f"Updated stdout handler log level to: {level}")
                    break
        else:
            print("QueueHandler not found or not configured properly.")

    def set_logfile(self, output_path: str):
        """ Change the filename of the file_json handler (overwrites json config file) """
        
        # Iterate through all handlers and find file_json handler
        if isinstance(self.queue_handler, logging.handlers.QueueHandler):
            for listener in self.queue_handler.listener.handlers:
                if isinstance(listener, logging.handlers.RotatingFileHandler):
                    # Update the filename attribute
                    old_filename = listener.baseFilename
                    listener.baseFilename = output_path
                    listener.stream.close()  # Close the old file stream
                    listener.stream = open(output_path, 'a', encoding='utf-8')  # Reopen with the new filename
                    print(f"log files: {output_path}")
                    break
            else:
                print("file_json handler not found.")

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
        return queue_handler

class DisplayJsonLogs:
    """ Display file in a .jsonl in a more readable manner """
    
    def __init__(self, log_file_path:str):
        self.log_path = Path(log_file_path)
        if not self.log_path.exists():
            print(f"Log file not found: {self.log_path}")
    
    def display(self, min_level:str='DEBUG'):
        """ Reads and pretty-prints the JSON log file, filtering by log level."""

        # Mapping of log levels to numeric values
        min_level_value = LEVELS.get(min_level.upper(), 10)

        if not self.log_path.exists():
            print(f"Log file not found: {self.log_path}")
            return

        try:
            with open(self.log_path, 'r', encoding='utf-8') as log_file:
                for line in log_file:
                    try:
                        log_entry = json.loads(line)
                        log_level = log_entry.get("level", "DEBUG")
                        
                        # Only print logs with level >= min_level
                        if LEVELS.get(log_level.upper(), 0) >= min_level_value:
                            l = json.loads(line)
                            output = f"[{l['level']}|{l['module']}|{l['function']}|{l['line']}] {l['message']}"
                            print(output)
                    except json.JSONDecodeError:
                        print(f"Skipping invalid JSON line: {line}")
        except Exception as e:
            print(f"An error occurred while reading the log file: {e}")


if __name__ == '__main__':
    # use it like this
    output_logs = Path(__file__).resolve().parent.parent / 'logs' / 'test.jsonl'
    mylogger = SetupLogging(output_logs)
    log = mylogger.log
    
    mylogger.set_loglevel('DEBUG')
    
    print('*'*50)
    log.debug("test")
    log.info("test")
    log.warning("test")
    log.error("test")
    log.critical("test")
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("exception message")

    jsonl = DisplayJsonLogs(output_logs)
    jsonl.display('WARNING')

