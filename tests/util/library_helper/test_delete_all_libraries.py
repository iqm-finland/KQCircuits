# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import logging

from kqcircuits.pya_resolver import pya

from kqcircuits.util.library_helper import load_libraries, delete_all_libraries

log = logging.getLogger(__name__)


def test_delete_all():
    load_libraries()
    assert len(pya.Library.library_names()) > 1
    delete_all_libraries()
    assert pya.Library.library_names() == ["Basic"]
