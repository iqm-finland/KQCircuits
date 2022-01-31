# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# https://www.gnu.org/licenses/gpl-3.0.html.
#
# The software distribution should follow IQM trademark policy for open-source software
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


import logging
import sys


def route_log(lowest_visible_level="INFO", remove_old_handlers=True, filename=""):
    """Routes the log output to stdout and to an optional file

    Enables monitoring the log in KLayout console. If requested it also appends logs to the
    specified file. By default removes old handlers from root logger to avoid output to other places
    than defined here.

    Arguments:
        lowest_visible_level (String): one of DEBUG, INFO, WARNING, ERROR, CRITICAL
        remove_old_handlers (Boolean): determines if old handlers are removed from the root logger
        filename: name of the file to append logs to
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

    if filename:
        fh = logging.FileHandler(filename)
        fh.setFormatter(formatter)
        fh.setLevel(lowest_visible_level)
        root_logger.addHandler(fh)
