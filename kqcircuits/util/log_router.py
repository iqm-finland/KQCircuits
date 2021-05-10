# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy's prior
# written permission.

import logging
import sys


def route_log_to_stdout(lowest_visible_level="INFO", remove_old_handlers=True):
    """Routes the log output to stdout

    Enables monitoring the log in KLayout console. Optionally removes old handlers from root logger to avoid output to
    other places than defined here.

    Arguments:
        lowest_visible_level (String): one of DEBUG, INFO, WARNING, ERROR, CRITICAL
        remove_old_handlers (Boolean): determines if old handlers are removed from the root logger
    """

    root_logger = logging.getLogger()

    # To make sure that the logs are only output to the place defined here, old handlers must be removed from the
    # logger. This is needed for example if you want to set a different lowest_visible_level by re-running this.
    # Otherwise the old handlers would cause output with the old lowest_visible_level.
    if remove_old_handlers:
        while root_logger.hasHandlers():
            root_logger.removeHandler(root_logger.handlers[0])

    message_format = "%(asctime)s:%(levelname)s:%(name)s:%(funcName)s:%(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(message_format, date_format)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(lowest_visible_level)

    root_logger.addHandler(handler)
