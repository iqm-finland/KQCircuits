# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

def deep_delete_pcells(cell):
    for inst in cell.each_inst():
        if (cell.is_pcell_variant(inst)):
            inst.delete()


def deep_delete_all(cell):
    for inst in cell.each_inst():
        inst.delete()
