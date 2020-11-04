# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import numpy

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.element import Element
from kqcircuits.elements.qubits.qubit import Qubit
from kqcircuits.test_structures.test_structure import TestStructure


class JunctionTestPads(TestStructure):
    """Junction test structures.

    Produces an array of junction test structures within the given area. Each structure consists of a SQUID,
    which is connected to pads. There can be either 2 or 4 pads per SQUID, depending on the configuration.
    Optionally, it is possible to produce only pads without any SQUIDs.

    """

    PARAMETERS_SCHEMA = {
        "pad_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Pad width [μm]",
            "default": 500
        },
        "area_height": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Area height [μm]",
            "default": 1900
        },
        "area_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Area width [μm]",
            "default": 1300
        },
        "squid_name": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "SQUID Type",
            "default": "QCD1",
            "choices": [["QCD1", "QCD1"], ["QCD2", "QCD2"], ["QCD3", "QCD3"], ["SIM1", "SIM1"]]
        },
        "junctions_horizontal": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Horizontal (True) or vertical (False) junctions",
            "default": True
        },
        "pad_spacing": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Spacing between different pad pairs [μm]",
            "default": 100
        },
        "only_pads": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Only produce pads, no junctions",
            "default": False
        },
        "pad_configuration": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Pad configuration",
            "default": "2-port",
            "choices": [["2-port", "2-port"], ["4-port", "4-port"]]
        }
    }

    produce_squid = Qubit.produce_squid

    def produce_impl(self):

        if self.pad_configuration == "2-port":
            self._produce_two_port_junction_tests()
        if self.pad_configuration == "4-port":
            self._produce_four_port_junction_tests()

        super().produce_impl()

    def _produce_two_port_junction_tests(self):

        pads_region = pya.Region()
        pad_step = self.pad_spacing + self.pad_width
        squid_arm_width = 8

        junction_idx = 0
        if self.junctions_horizontal:
            for x in numpy.arange(self.pad_spacing*1.5 + self.pad_width, self.area_width - pad_step, 2*pad_step,
                                  dtype=numpy.double):
                for y in numpy.arange(self.pad_spacing + self.pad_width*0.5, self.area_height - self.pad_width/2,
                                      pad_step, dtype=numpy.double):
                    self.produce_pad(x - pad_step/2, y, pads_region, self.pad_width, self.pad_width)
                    self.produce_pad(x + pad_step/2, y, pads_region, self.pad_width, self.pad_width)
                    if not self.only_pads:
                        self._produce_squid_and_arms(x, y, pads_region, squid_arm_width)
                    self.refpoints["probe_{}_l".format(junction_idx)] = pya.DPoint(x - pad_step/2, y)
                    self.refpoints["probe_{}_r".format(junction_idx)] = pya.DPoint(x + pad_step/2, y)
                    junction_idx += 1
        else:
            for y in numpy.arange(self.pad_spacing*1.5 + self.pad_width, self.area_height - pad_step, 2*pad_step,
                                  dtype=numpy.double):
                for x in numpy.arange(self.pad_spacing + self.pad_width*0.5, self.area_width - self.pad_width/2,
                                      pad_step, dtype=numpy.double):
                    self.produce_pad(x, y - pad_step/2, pads_region, self.pad_width)
                    self.produce_pad(x, y + pad_step/2, pads_region, self.pad_width)
                    if not self.only_pads:
                        self._produce_squid_and_arms(x, y, pads_region, squid_arm_width)
                    self.refpoints["probe_{}_l".format(junction_idx)] = pya.DPoint(x, y - pad_step/2)
                    self.refpoints["probe_{}_r".format(junction_idx)] = pya.DPoint(x, y + pad_step/2)
                    junction_idx += 1

        self.produce_etched_region(pads_region, pya.DPoint(self.area_width/2, self.area_height/2), self.area_width,
                                   self.area_height)

    def _produce_four_port_junction_tests(self):

        pads_region = pya.Region()
        junction_idx = 0
        step = 2*(self.pad_width + self.pad_spacing)

        for x in numpy.arange(self.pad_spacing*1.5 + self.pad_width, self.area_width - step/2, step,
                              dtype=numpy.double):
            for y in numpy.arange(self.pad_spacing*1.5 + self.pad_width, self.area_height - step/2, step,
                                  dtype=numpy.double):

                if self.only_pads:
                    self.produce_four_point_pads(pads_region, self.pad_width, self.pad_width, self.pad_spacing,
                                                 self.pad_spacing, False, pya.DTrans(0, False, x, y),
                                                 "probe_{}".format(junction_idx))
                else:
                    self.produce_four_point_pads(pads_region, self.pad_width, self.pad_width, self.pad_spacing,
                                                 self.pad_spacing, True,
                                                 pya.DTrans(0 if self.junctions_horizontal else 1, False, x, y),
                                                 "probe_{}".format(junction_idx))
                    self._produce_squid_and_arms(x, y, pads_region, 5)

                junction_idx += 1

        self.produce_etched_region(pads_region, pya.DPoint(self.area_width/2, self.area_height/2), self.area_width,
                                   self.area_height)

    def _produce_squid_and_arms(self, x, y, pads_region, arm_width):
        """Produces a squid and arms for connecting it to pads.

        The squid is inserted as a subcell. The arm shapes are inserted to pads_region, and their shape depends on
        arm_width and self.junctions_horizontal.

        Args:
           x: x-coordinate of squid origin
           y: y-coordinate of squid origin
           pads_region: Region to which the arm shapes are inserted
           arm_width: width of the arms

        """

        # for some SQUIDs, the below arm length must be different
        extra_arm_length = 0

        # SQUID from template
        # SQUID refpoint at the ground plane edge
        squid_cell = Element.create_cell_from_shape(self.layout, self.squid_name)
        squid_pos_rel = self.get_refpoints(squid_cell)
        pos_rel_squid_top = squid_pos_rel["port_common"]

        if self.junctions_horizontal:
            # squid
            trans = pya.DCplxTrans(x, y)
            region_unetch = self.produce_squid(squid_cell, trans)
            pads_region.insert(region_unetch)
            # arm below
            arm1 = pya.DBox(
                pya.DPoint(x + 11 + extra_arm_length, y),
                pya.DPoint(x - self.pad_spacing/2, y - arm_width),
            )
            pads_region.insert(arm1.to_itype(self.layout.dbu))
            # arm above
            arm2 = pya.DBox(
                trans*pos_rel_squid_top + pya.DVector(-4, 0),
                trans*pos_rel_squid_top + pya.DVector(self.pad_spacing/2, arm_width),
            )
            pads_region.insert(arm2.to_itype(self.layout.dbu))
        else:
            # squid
            trans = pya.DCplxTrans(x, y)
            region_unetch = self.produce_squid(squid_cell, trans)
            pads_region.insert(region_unetch)
            # arm below
            arm1 = pya.DBox(
                pya.DPoint(x + 11 + extra_arm_length, y),
                pya.DPoint(x - 11 - extra_arm_length, y - arm_width),
            )
            pads_region.insert(arm1.to_itype(self.layout.dbu))
            arm2 = pya.DBox(
                pya.DPoint(x + arm_width/2, y),
                pya.DPoint(x - arm_width/2, y - self.pad_spacing/2),
            )
            pads_region.insert(arm2.to_itype(self.layout.dbu))
            # arm above
            arm3 = pya.DBox(
                trans*pos_rel_squid_top + pya.DVector(-arm_width/2, 0),
                trans*pos_rel_squid_top + pya.DVector(arm_width/2, self.pad_spacing/2),
            )
            pads_region.insert(arm3.to_itype(self.layout.dbu))
