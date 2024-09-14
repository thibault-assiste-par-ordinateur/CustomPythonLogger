# -*- coding: utf-8 -*-
from custompythonlogger.mylogger import SetupLogging, DisplayJsonLogs
from pathlib import Path

output_logs = Path(__file__).resolve().parent / 'logs' / 'test.jsonl'
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

