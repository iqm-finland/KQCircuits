# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.


def test_simulation_has_schema(empty_simulation):
    schema = empty_simulation.get_schema()

    assert type(schema) == dict
