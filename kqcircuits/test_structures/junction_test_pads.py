# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import numpy

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element
from kqcircuits.test_structures.test_structure import TestStructure
from kqcircuits.defaults import default_layers


class JunctionTestPads(TestStructure):
    """
  Junction Test Pads for general purpose pixels
  """

    PARAMETERS_SCHEMA = {
        "pad_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Pad width (um)",
            "default": 500
        },
        "area_height": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Area height (um)",
            "default": 1900
        },
        "area_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Area width (um)",
            "default": 1300
        },
        "squid_name": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "SQUID Type",
            "default": "QCD1"
        },
        "junctions_horizontal": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Horizontal (True) or vertical (False) junctions",
            "default": True
        },
        "pad_spacing": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Spacing between different pad pairs (um)",
            "default": 100
        },
    }

    def __init__(self):
        super().__init__()

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "JunctionTestPads"

    def coerce_parameters_impl(self):
        None

    def can_create_from_shape_impl(self):
        return False

    def parameters_from_shape_impl(self):
        None

    def transformation_from_shape_impl(self):
        return pya.Trans()

    def produce_impl(self):
        # for some SQUIDs, the below arm length must be different
        extra_arm_length = 0
        if self.squid_name == "IQM2" or self.squid_name == "IQM3":
            extra_arm_length = 9

        # background area
        ah = self.area_height
        aw = self.area_width

        test_area = pya.DPolygon([
            pya.DPoint(aw, ah),
            pya.DPoint(aw, 0),
            pya.DPoint(0, 0),
            pya.DPoint(0, ah),
        ])
        reg_test_area = pya.Region(test_area.to_itype(self.layout.dbu))

        # SQUID from template
        # SQUID refpoint at the ground plane edge
        squid_cell = Element.create_cell_from_shape(self.layout, self.squid_name)
        squid_pos_rel = self.get_refpoints(squid_cell)
        pos_rel_squid_top = squid_pos_rel["port_common"]

        # pads for junction probing
        pw = self.pad_width
        reg_pads = pya.Region()
        pad_space = self.pad_spacing  # um
        pad_step = pad_space + pw
        for y in numpy.arange(pad_space, ah - pw, pad_step, dtype=numpy.double):
            for x in numpy.arange(pad_space, aw - pw, pad_step, dtype=numpy.double):
                pad = pya.DPolygon([
                    pya.DPoint(x, y),
                    pya.DPoint(x + pw, y),
                    pya.DPoint(x + pw, y + pw),
                    pya.DPoint(x, y + pw),
                ])
                reg_pads.insert(pad.to_itype(self.layout.dbu))

        # junction s with arms
        i = 0
        if self.junctions_horizontal:
            for x in numpy.arange(pad_space * 1.5 + pw, aw - pad_step, 2 * pad_step, dtype=numpy.double):
                for y in numpy.arange(pad_space + pw * 0.5, ah - pw / 2, pad_step, dtype=numpy.double):
                    # squid
                    trans = pya.DTrans(x, y)
                    region_unetch = pya.Region(squid_cell.shapes(self.layout.layer(default_layers["b base metal addition"])))
                    region_unetch.transform(trans.to_itype(self.layout.dbu))
                    reg_pads.insert(region_unetch)
                    self.insert_cell(squid_cell, trans)
                    # arm below
                    arm1 = pya.DBox(
                        pya.DPoint(x + 11 + extra_arm_length, y),
                        pya.DPoint(x - pad_space / 2, y - 8),
                    )
                    reg_pads.insert(arm1.to_itype(self.layout.dbu))
                    # arm above
                    arm2 = pya.DBox(
                        trans * pos_rel_squid_top + pya.DVector(-4, 0),
                        trans * pos_rel_squid_top + pya.DVector(pad_space / 2, 8),
                    )
                    reg_pads.insert(arm2.to_itype(self.layout.dbu))
                    i+=1
                    self.refpoints["probe_{}_l".format(i)] = pya.DPoint(x-pad_step/2, y)
                    self.refpoints["probe_{}_r".format(i)] = pya.DPoint(x+pad_step/2, y)
        else:
            for y in numpy.arange(pad_space * 1.5 + pw, ah - pad_step, 2 * pad_step, dtype=numpy.double):
                for x in numpy.arange(pad_space + pw * 0.5, aw - pw / 2, pad_step, dtype=numpy.double):
                    # squid
                    trans = pya.DTrans(x, y)
                    region_unetch = pya.Region(squid_cell.shapes(self.layout.layer(default_layers["b base metal addition"])))
                    region_unetch.transform(trans.to_itype(self.layout.dbu))
                    reg_pads.insert(region_unetch)
                    self.insert_cell(squid_cell, trans)
                    # arm below
                    arm1 = pya.DBox(
                        pya.DPoint(x + 11 + extra_arm_length, y),
                        pya.DPoint(x - 11 - extra_arm_length, y - 8),
                    )
                    reg_pads.insert(arm1.to_itype(self.layout.dbu))
                    arm2 = pya.DBox(
                        pya.DPoint(x + 4, y),
                        pya.DPoint(x - 4, y - pad_space / 2),
                    )
                    reg_pads.insert(arm2.to_itype(self.layout.dbu))
                    # arm above
                    arm3 = pya.DBox(
                        trans * pos_rel_squid_top + pya.DVector(-4, 0),
                        trans * pos_rel_squid_top + pya.DVector(4, pad_space / 2),
                    )
                    reg_pads.insert(arm3.to_itype(self.layout.dbu))
                    i+=1
                    self.refpoints["probe_{}_l".format(i)] = pya.DPoint(x, y-pad_step/2)
                    self.refpoints["probe_{}_r".format(i)] = pya.DPoint(x, y+pad_step/2)

                    # etched region
        reg_etch = reg_test_area - reg_pads
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(reg_etch)

        # grid avoidance region
        reg_protect = reg_etch.extents(int(self.margin / self.layout.dbu))
        self.cell.shapes(self.layout.layer(self.face()["ground grid avoidance"])).insert(reg_protect)

        super().produce_impl()
