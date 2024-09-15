# -*- coding: utf-8 -*-

import sys
from pathlib import Path

# DIRTY FIX TO APPEND THE FOLDER AS A WORKING DIRECTORY (usefull for VSC code-runner)
import os
import sys
cwd = os.getcwd()
sys.path.append(cwd)
print("Current working directory: {0}".format(cwd))


from custompythonlogger.mylogger import SetupLogging, DisplayJsonLogs

# setup logging
mylogger = SetupLogging()
log = mylogger.log

# overwrite log level
mylogger.set_loglevel('DEBUG')

# testing logging
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

# display output logs
launched_script = Path(sys.argv[0]).resolve()
output_logs = launched_script.parent.parent / 'logs' / 'log.jsonl'
print('*'*50)
jsonl = DisplayJsonLogs(output_logs)
jsonl.display('ERROR')

