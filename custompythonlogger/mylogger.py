# -*- coding: utf-8 -*-

from pathlib import Path
import atexit
import datetime as dt
import json
import sys
import logging.config
import logging.handlers
#from typing import override # the 'override' decorator is python3.12 specific 
import importlib.resources as pkg_resources

__all__ = ['SetupLogging', 'DisplayJsonLogs']

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

    #@override # typing new function in python 3.12, only here to INDICATE the below method got ovewritten from its base class. I am not using it since it is python3.12 specific.
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
    #@override # typing new function in python 3.12, only here to INDICATE the below method got ovewritten from its base class. I am not using it since it is python3.12 specific.
    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        return record.levelno <= logging.INFO

class SetupLogging:
    '''
    Custom logging from json file. The configuration is very specific. Check the json sample in ../config/logging.json
    :param output_dir: file path to output the log files. Defaults to /logs/log.jsonl in the parent dir of the started script. 
    :param json_config: json string, containing configuration for logging. A default configuration is provided in ../config. It can be overwritten passing a new path. In such a case, note that the Json file needs to match the functions and classes of this module
    '''
    
    default_logging_filename = "logging.json"
    default_config_module = "custompythonlogger.config"
    
    def __init__(self, output_path:str = None, json_config:str = None):
        
        self.root_script_path = Path(sys.argv[0]).resolve()
        root_script_parent_dir = self.root_script_path.parent.parent
        self.logger_name = f"{root_script_parent_dir.name}.{self.root_script_path.stem}" # 'stem' affiche le nom du fichier sans l'extension, 'name' affiche le nom du dossier/fichier d'un path
        print(f"logger name: {self.logger_name}")

        self.log = logging.getLogger(self.logger_name)
        self.config = self._init_config_path(json_config)
        self.queue_handler = self._setup()

        self.json_file_handler = self._get_json_file_handler()
        self.stdout_handler = self._get_stdout_handler()

        self.output_path = self._init_output_path(output_path)
        self._set_output_path( self.output_path )


    def set_loglevel(self, level: str = 'INFO'):
        """Set the logging level for the stdout handler.
        :param level: Logging level (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        """
        # Convert the level string to logging level value
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {level}")
        
        # Set level
        self.stdout_handler.setLevel(numeric_level)
        print(f"Updated stdout handler log level to: {level}")


    def _set_output_path(self, output_path: str):
        """ Change the filename of the file_json handler (overwrites json config file) """
        self.json_file_handler.baseFilename = str(output_path) # necessary conversion
        self.json_file_handler.stream.close()  # Close the old file stream
        self.json_file_handler.stream = open(output_path, 'a', encoding='utf-8')  # Reopen with the new filename
        print(f"log output: {output_path}")
        

    def _init_output_path(self, path):
        """ Make sure the specified output path exists and has a .jsonl extension.
            If not, creates the file and dir as mentionned in json config, in package root folder 
        """
        if not path:
            filename_from_config = self.config['handlers']['file_json']['filename']
            path = self.root_script_path.parent.parent / filename_from_config # dossier parent du script principal
        else:
            # ensure file extension is .jsonl
            path = Path(path)
            if path.suffix != '.jsonl':
                path.with_suffix('.jsonl')
        # ensure the parent directories exist, if not create them
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        return path


    def _init_config_path(self, json_config):
        """ 
        If the user did not specify a json config, use default one
        In such a case, the file is loaded from the package with urllib 
        (which does not work with paths but packages names)
        """
        if not json_config:
            # Access the default logging config file from the package
            json_config = pkg_resources.files(self.default_config_module) / self.default_logging_filename
            print(f"log using default config file: {json_config}")
            with json_config.open('r', encoding='utf-8') as f:
                return json.loads(f.read())
        print(f"log using custom config file: {json_config}")
        return json_config


    def _get_json_file_handler(self):
        """ Look for the json_file handler in all the handlers """
        if isinstance(self.queue_handler, logging.handlers.QueueHandler):
            for listener in self.queue_handler.listener.handlers:
                if isinstance(listener, logging.handlers.RotatingFileHandler):
                    return listener
            print("json_file handler not found or not configured properly. Check config.")        
        else: 
            print('QueueHandler not found or not configured properly.')
        return None


    def _get_stdout_handler(self):
        """ Look for the stream handler stdout in all the handlers """
        if isinstance(self.queue_handler, logging.handlers.QueueHandler):
            # Access the handlers managed by the QueueListener
            for listener in self.queue_handler.listener.handlers:
                if isinstance(listener, UTF8StreamHandler) and listener.stream.name == 1: # stdout is 1, stderr is 2 
                    return listener
            print("stdout stream handler not found or not configured properly. Check config.")        
        else:
            print("QueueHandler not found or not configured properly.")


    def _get_handler_by_name(self, handler_name):
        """
        Find the handler by name in the logger.
        :param handler_name: Name of the handler (e.g., 'queue_handler')
        :return: Logging handler object or None if not found.
        """
        for handler in self.log.handlers:
            if handler.get_name() == handler_name:
                return handler
        return None

    
    def _setup(self):
        """ :config: json file path """
        try:
            logging.config.dictConfig(self.config)
        except ValueError as err:
            print(f"ValueError: {err}. The json config file has mistakes. Check referenced files path...")

        queue_handler = self._get_handler_by_name("queue_handler")
        if queue_handler is not None:
            queue_handler.listener.start()
            atexit.register(queue_handler.listener.stop)
        return queue_handler


class DisplayJsonLogs:
    """ Display file in a .jsonl in a more readable manner 
        :param log_file_path: input .jsonl file to read and display
    """
    
    def __init__(self, log_file_path:str):
        self.log_path = Path(log_file_path)
        if not self.log_path.exists():
            print(f"Log file not found for display: {self.log_path}")
    
    def display(self, min_level:str='DEBUG'):
        """ Reads and pretty-prints the JSON log file, filtering by log level."""

        # Mapping of log levels to numeric values
        numeric_min_level = getattr(logging, min_level.upper(), None)
        if not isinstance(numeric_min_level, int):
            raise ValueError(f"Invalid log level: {min_level}")              

        if not self.log_path.exists():
            print(f"Log file not found for display: {self.log_path}")
            return

        try:
            with open(self.log_path, 'r', encoding='utf-8') as log_file:
                for line in log_file:
                    try:
                        log_entry = json.loads(line)
                        log_level = log_entry.get("level", "DEBUG")
                        numeric_log_level = getattr(logging, log_level.upper(), None)

                        # Only print logs with level >= min_level
                        if numeric_log_level >= numeric_min_level:
                            l = json.loads(line)
                            output = f"[{l['level']}|{l['module']}|l.{l['line']}] {l['message']}"
                            print(output)
                    except json.JSONDecodeError:
                        print(f"Skipping invalid JSON line: {line}")
        except Exception as e:
            print(f"An error occurred while reading the log file: {e}")


if __name__ == '__main__':
    pass




    # def set_loglevel(self, level: str = 'INFO'):
    #     """Set the logging level for the stdout handler.
    #     :param level: Logging level (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    #     """
    #     # Convert the level string to logging level value
    #     numeric_level = getattr(logging, level.upper(), None)
    #     if not isinstance(numeric_level, int):
    #         raise ValueError(f"Invalid log level: {level}")

    #     if isinstance(self.queue_handler, logging.handlers.QueueHandler):
    #         # Access the handlers managed by the QueueListener
    #         for listener in self.queue_handler.listener.handlers:
    #             if isinstance(listener, UTF8StreamHandler) and listener.stream.name == 1: # stdout is 1, stderr is 2 
    #                 # Set the new log level for the stdout handler
    #                 listener.setLevel(numeric_level)
    #                 print(f"Updated stdout handler log level to: {level}")
    #                 break
    #     else:
    #         print("QueueHandler not found or not configured properly.")


    # def set_log_path(self, output_path: str):
    #     """ Change the filename of the file_json handler (overwrites json config file) """
        
    #     if isinstance(self.queue_handler, logging.handlers.QueueHandler):
    #         # Iterate through all handlers and find file_json handler
    #         for listener in self.queue_handler.listener.handlers:
    #             if isinstance(listener, logging.handlers.RotatingFileHandler):
    #                 # Update the filename attribute
    #                 listener.baseFilename = output_path
    #                 listener.stream.close()  # Close the old file stream
    #                 listener.stream = open(output_path, 'a', encoding='utf-8')  # Reopen with the new filename
    #                 print(f"log output: {output_path}")
    #                 break
    #         else:
    #             print("file_json handler not found.")
