# -*- coding: utf-8 -*-

from custompythonlogger.mylogger import SetupLogging

import sys
print(sys.path)

mylogger = SetupLogging()
log = mylogger.log

log.info("test")

