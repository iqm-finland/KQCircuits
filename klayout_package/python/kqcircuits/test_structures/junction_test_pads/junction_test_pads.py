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


import numpy

from kqcircuits.qubits.qubit import Qubit
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.test_structures.test_structure import TestStructure
from kqcircuits.defaults import default_junction_test_pads_type
from kqcircuits.test_structures.junction_test_pads import junction_test_pads_type_choices
from kqcircuits.junctions.manhattan import Manhattan
from kqcircuits.junctions.junction import Junction


@add_parameters_from(Manhattan)
@add_parameters_from(Qubit, "junction_type", "junction_width", "loop_area", "mirror_squid",
                     "junction_parameters", "_junction_parameters")
class JunctionTestPads(TestStructure):
    """Base class for junction test structures."""

    default_type = default_junction_test_pads_type

    pad_width = Param(pdt.TypeDouble, "Pad width", 500, unit="μm")
    area_height = Param(pdt.TypeDouble, "Area height", 1900, unit="μm")
    area_width = Param(pdt.TypeDouble, "Area width", 1300, unit="μm")
    junctions_horizontal = Param(pdt.TypeBoolean, "Horizontal (True) or vertical (False) junctions", True)
    pad_spacing = Param(pdt.TypeDouble, "Spacing between different pad pairs", 100, unit="μm")
    only_pads = Param(pdt.TypeBoolean, "Only produce pads, no junctions", False)
    pad_configuration = Param(pdt.TypeString, "Pad configuration", "2-port", choices=["2-port", "4-port"])
    junction_width_steps = Param(pdt.TypeList, "Automatically generate junction widths [start, step]", [0, 0],
                                 unit="μm, μm")
    junction_widths = Param(pdt.TypeList, "Optional junction widths for individual junctions", [],
                            docstring="Override the junction widths with these values.")
    junction_test_pads_type = Param(pdt.TypeString, "Type of junction test pads", default_type,
                                    choices=junction_test_pads_type_choices)

    junction_test_pads_parameters = Param(pdt.TypeString, "Extra JunctionTestPads Parameters", "{}")
    _junction_test_pads_parameters = Param(pdt.TypeString, "Previous state of *_parameters", "{}", hidden=True)

    produce_squid = Qubit.produce_squid

    @classmethod
    def create(cls, layout, library=None, junction_test_pads_type=None, **parameters):
        """Create a JunctionTestPads cell in layout."""
        return cls.create_subtype(layout, library, junction_test_pads_type, **parameters)[0]

    def coerce_parameters_impl(self):
        self.sync_parameters(Junction)
        self.sync_parameters(JunctionTestPads)

    def _produce_impl(self):
        if self.pad_configuration == "2-port":
            self._produce_two_port_junction_tests()
        if self.pad_configuration == "4-port":
            self._produce_four_port_junction_tests()

    def _next_junction_width(self, idx):
        """Get the next junction width

        Try first the `junction_widths` list, if available, if not then generate it based on `start`
        and `step`, unless `step` is 0, in this case just use the default `junction_width`.
        """
        start, step = [float(x) for x in self.junction_width_steps]
        if idx < len(self.junction_widths) and self.junction_widths[idx] != '':
            return float(self.junction_widths[idx])
        elif not (start == 0 and step == 0):
            return start + idx * step
        return self.junction_width

    def _produce_two_port_junction_tests(self):

        pads_region = pya.Region()
        pad_step = self.pad_spacing + self.pad_width
        arm_width = 8

        junction_idx = 0
        y_flip = -1 if self.face_ids[0] == '2b1' else 1
        if self.junctions_horizontal:
            for x in numpy.arange(self.pad_spacing*1.5 + self.pad_width, self.area_width - pad_step, 2*pad_step,
                                  dtype=numpy.double):
                for y in numpy.arange(self.pad_spacing + self.pad_width*0.5, self.area_height - self.pad_width / 2,
                                      pad_step, dtype=numpy.double):
                    self.produce_pad(x - pad_step / 2, y, pads_region, self.pad_width, self.pad_width)
                    self.produce_pad(x + pad_step / 2, y, pads_region, self.pad_width, self.pad_width)
                    self._next_width = self._next_junction_width(junction_idx)
                    self._produce_junctions(x, y, pads_region, arm_width, junction_idx)
                    self.refpoints["probe_{}_l".format(junction_idx)] = pya.DPoint(x - pad_step * y_flip / 2, y)
                    self.refpoints["probe_{}_r".format(junction_idx)] = pya.DPoint(x + pad_step * y_flip/ 2, y)
                    junction_idx += 1
        else:
            for y in numpy.arange(self.pad_spacing*1.5 + self.pad_width, self.area_height - pad_step, 2*pad_step,
                                  dtype=numpy.double):
                for x in numpy.arange(self.pad_spacing + self.pad_width*0.5, self.area_width - self.pad_width / 2,
                                      pad_step, dtype=numpy.double):
                    self.produce_pad(x, y - pad_step / 2, pads_region, self.pad_width, self.pad_width)
                    self.produce_pad(x, y + pad_step / 2, pads_region, self.pad_width, self.pad_width)
                    self._next_width = self._next_junction_width(junction_idx)
                    self._produce_junctions(x, y, pads_region, arm_width, junction_idx)
                    self.refpoints["probe_{}_l".format(junction_idx)] = pya.DPoint(x, y - pad_step / 2)
                    self.refpoints["probe_{}_r".format(junction_idx)] = pya.DPoint(x, y + pad_step / 2)
                    junction_idx += 1

        self.produce_etched_region(pads_region, pya.DPoint(self.area_width / 2, self.area_height / 2), self.area_width,
                                   self.area_height)

    def _produce_junctions(self, x, y, pads_region, arm_width, index):

        if not self.only_pads:
            self._produce_squid_and_arms(x, y, pads_region, arm_width, index)

    def _produce_four_port_junction_tests(self):

        pads_region = pya.Region()
        junction_idx = 0
        step = 2 * (self.pad_width + self.pad_spacing)

        for x in numpy.arange(self.pad_spacing*1.5 + self.pad_width, self.area_width - step / 2, step,
                              dtype=numpy.double):
            for y in numpy.arange(self.pad_spacing*1.5 + self.pad_width, self.area_height - step / 2, step,
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
                    self._next_width = self._next_junction_width(junction_idx)
                    self._produce_junctions(x, y, pads_region, 5, junction_idx)

                junction_idx += 1

        self.produce_etched_region(pads_region, pya.DPoint(self.area_width / 2, self.area_height / 2), self.area_width,
                                   self.area_height)

    def _produce_squid_and_arms(self, x, y, pads_region, arm_width, index, only_arms=False):
        """Produces a squid and arms for connecting it to pads.

        The squid is inserted as a subcell. The arm shapes are inserted to pads_region, and their shape depends on
        arm_width and self.junctions_horizontal.

        Args:
           x: x-coordinate of squid origin
           y: y-coordinate of squid origin
           pads_region: Region to which the arm shapes are inserted
           arm_width: width of the arms
           only_arms: Boolean argument that allows to choose whether to create the arms and the squid device or
                            only the arms
        """

        arm_length = 11
        junction_spacing = self.junction_spacing

        # squid
        trans = pya.DCplxTrans(x, y - junction_spacing)
        if not self.junctions_horizontal:
            trans = pya.DCplxTrans(x - junction_spacing, y)
        squid_ref_rel = self.produce_squid(trans, only_arms=only_arms, junction_width=self._next_width,
                                           squid_index=index)
        if "right_side" in squid_ref_rel:
            arm_length = squid_ref_rel["right_side"].x - 0.5
        pos_rel_squid_top = squid_ref_rel["port_common"]

        if self.junctions_horizontal:
            # arm below
            arm1 = pya.DBox(
                pya.DPoint(x + arm_length, y - junction_spacing),
                pya.DPoint(x - self.pad_spacing / 2, y - arm_width - junction_spacing),
            )
            pads_region.insert(arm1.to_itype(self.layout.dbu))
            # arm above
            arm2 = pya.DBox(
                trans*pos_rel_squid_top + pya.DVector(-4, 0),
                trans*pos_rel_squid_top + pya.DVector(self.pad_spacing / 2, arm_width),
            )
            pads_region.insert(arm2.to_itype(self.layout.dbu))
        else:
            # arm below
            arm1 = pya.DBox(
                pya.DPoint(x + arm_length - junction_spacing, y),
                pya.DPoint(x - arm_length - junction_spacing, y - arm_width),
            )
            pads_region.insert(arm1.to_itype(self.layout.dbu))
            arm2 = pya.DBox(
                pya.DPoint(x + arm_width / 2 - junction_spacing, y),
                pya.DPoint(x - arm_width / 2 - junction_spacing, y - self.pad_spacing / 2),
            )
            pads_region.insert(arm2.to_itype(self.layout.dbu))
            # arm above
            arm3 = pya.DBox(
                trans*pos_rel_squid_top + pya.DVector(-arm_width / 2, 0),
                trans*pos_rel_squid_top + pya.DVector(arm_width / 2, self.pad_spacing / 2),
            )
            pads_region.insert(arm3.to_itype(self.layout.dbu))
