#!/usr/bin/env python
"""
A simple module setting up the Python logger for logging to stdout
"""

import logging

logger = logging.getLogger("dave")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
