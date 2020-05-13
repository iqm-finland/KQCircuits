# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import sys
from importlib import reload
from autologging import logged, traced

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element
from kqcircuits.elements.launcher import Launcher
from kqcircuits.test_structures.junction_test_pads import JunctionTestPads
from kqcircuits.util.library_helper import LIBRARY_NAMES
from kqcircuits.elements.chip_frame import ChipFrame
from kqcircuits.util.groundgrid import make_grid

reload(sys.modules[Element.__module__])


@logged
@traced
class Chip(Element):
    """Base PCell declaration for chips.

    By default produces in face 0 the chip frame consisting of texts in pixel corners, dicing edge, markers and
    optionally grid. Production of the chip frames can be adjusted by overriding the produce_frames() method.

    Provides helpers to produce launchers and junction tests.
    """
    version = 2

    LIBRARY_NAME = LIBRARY_NAMES["Chip"]
    LIBRARY_DESCRIPTION = "Superconducting quantum circuit library for chips."

    PARAMETERS_SCHEMA = {
        "box": {
            "type": pya.PCellParameterDeclaration.TypeShape,
            "description": "Border",
            "default": pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000))
        },
        "with_grid": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Make ground plane grid",
            "default": False
        },
        "dice_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Dicing width (um)",
            "default": 200
        },
        "name_mask": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Name of the mask",
            "default": "M99"
        },
        "name_chip": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Name of the chip",
            "default": "CTest"
        },
        "name_copy": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Name of the copy"
        },
        "text_margin": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Margin for labels",
            "default": 100,
            "hidden": True
        },
        "dice_grid_margin": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Margin between dicing edge and ground grid",
            "default": 100,
            "hidden": True
        },
    }

    def __init__(self):
        super().__init__()

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return ("{}".format(self.name_chip))

    def can_create_from_shape_impl(self):
        return self.shape.is_box()

    def parameters_from_shape_impl(self):
        self.box.p1 = self.shape.p1
        self.box.p2 = self.shape.p2

    def produce_launcher(self, pos, direction, name="", width=300):
        """Wrapper function for launcher PCell placement at `pos` with `direction`, `name` and `width`.
        """
        subcell = Launcher.create_cell(self.layout, {"name": name, "s": width, "l": width})
        if isinstance(direction, str):
            direction = {"E": 0, "W": 180, "S": -90, "N": 90}[direction]
        transf = pya.DCplxTrans(1, direction, False, pos)
        self.insert_cell(subcell, transf)

    def produce_launchers_SMA8(self, enabled=["WS", "WN", "ES", "EN", "SW", "SE", "NW", "NE"]):
        """Produces enabled launchers for SMA8 sample holder default locations

        Args:
            enabled: List of enabled standard launchers from set ("WS", "WN", "ES", "EN", "SW", "SE", "NW", "NE")

        Effect:
            launchers PCells added to the class parent cell.

        Returns:
            launchers dictionary, where keys are launcher names and values are tuples of (point, heading, distance from
            chip edge)
        """
        # dictionary of point, heading, distance from chip edge
        launchers = {
            "WS": (pya.DPoint(800, 2800), "W", 300),
            "ES": (pya.DPoint(9200, 2800), "E", 300),
            "WN": (pya.DPoint(800, 7200), "W", 300),
            "EN": (pya.DPoint(9200, 7200), "E", 300),
            "SW": (pya.DPoint(2800, 800), "S", 300),
            "NW": (pya.DPoint(2800, 9200), "N", 300),
            "SE": (pya.DPoint(7200, 800), "S", 300),
            "NE": (pya.DPoint(7200, 9200), "N", 300)
        }
        for name in enabled:
            self.produce_launcher(launchers[name][0], launchers[name][1], name)
        return launchers

    def produce_launchers_ARD24(self):
        """Produces enabled launchers for ARD24 sample holder default locations

        Effect:
            launchers PCells added to the class parent cell.

        Returns:
            launchers dictionary, where keys are launcher names and values are tuples of (point, heading, distance from
            chip edge)
        """
        launchers = {}  # dictionary of point, heading, distance from chip edge
        launchers_specs = []
        for direction, rot, trans in (
                ("N", pya.DTrans.R270, pya.DTrans(3, 0, 0, 10e3)), ("E", pya.DTrans.R180, pya.DTrans(2, 0, 10e3, 10e3)),
                ("S", pya.DTrans.R90, pya.DTrans(1, 0, 10e3, 0)), ("W", pya.DTrans.R0, pya.DTrans(0, 0, 0, 0))):
            for i in range(6):
                loc = pya.DPoint(780, (7500 - 2500) / 5. * i + 2500)
                launchers_specs.append((trans * loc, direction, 240))
        for i, spec in enumerate(launchers_specs):
            launchers[str(i)] = spec
        for name, launcher in launchers.items():
            self.produce_launcher(launcher[0], launcher[1], name, width=launcher[2])
        return launchers

    def produce_junction_tests(self, squid_name="QCD1"):
        """Produces junction test pads in the chip.

        Args:
            squid_name: A string defining the type of SQUIDs used in the test pads.
                        QCD1 | QCD2 | QCD3 | SIM1

        """
        junction_tests_w = JunctionTestPads.create_cell(self.layout, {
            "margin": 50,
            "area_height": 1300,
            "area_width": 2500,
            "junctions_horizontal": True,
            "squid_name": squid_name
        })
        junction_tests_h = JunctionTestPads.create_cell(self.layout, {
            "margin": 50,
            "area_height": 2500,
            "area_width": 1300,
            "junctions_horizontal": True,
            "squid_name": squid_name
        })
        self.insert_cell(junction_tests_h, pya.DTrans(0, False, .35e3, (10e3 - 2.5e3) / 2), "testarray_w")
        self.insert_cell(junction_tests_w, pya.DTrans(0, False, (10e3 - 2.5e3) / 2, .35e3), "testarray_s")
        self.insert_cell(junction_tests_h, pya.DTrans(0, False, 9.65e3 - 1.3e3, (10e3 - 2.5e3) / 2), "testarray_e")
        self.insert_cell(junction_tests_w, pya.DTrans(0, False, (10e3 - 2.5e3) / 2, 9.65e3 - 1.3e3), "testarray_n")

    def produce_ground_grid(self, box, face):
        """Produces ground grid in the given face of the chip.

        Args:
            box: pya.DBox within which the grid is created
            face: dictionary containing key "id" for the face ID and keys for all the available layers in that face

        """
        if self.with_grid:
            grid_area = box * (1 / self.layout.dbu)
            protection = pya.Region(
                self.cell.begin_shapes_rec(self.layout.layer(face["ground grid avoidance"]))).merged()
            grid_mag_factor = 1
            region_ground_grid = make_grid(grid_area, protection,
                                           grid_step=10 * (1 / self.layout.dbu) * grid_mag_factor,
                                           grid_size=5 * (1 / self.layout.dbu) * grid_mag_factor)
            self.cell.shapes(self.layout.layer(face["ground grid"])).insert(region_ground_grid)

    def produce_frame_and_grid(self, frame_parameters, box, face, trans=pya.DTrans()):
        """"Produces a chip frame and ground grid (if self.with_grid) for the given face.

        Args:
            frame_parameters: PCell parameters for the chip frame
            box: bounding box for the ground grid
            face: dictionary containing key "id" for the face ID and keys for all the available layers in that face
            trans: DTrans for the chip frame, default=pya.DTrans()
        """
        frame_cell = ChipFrame.create_cell(self.layout, frame_parameters)
        self.insert_cell(frame_cell, trans)
        self.produce_ground_grid(box, face)

    def produce_frames(self):
        """Produces chip frame and grid for face 0.

        This method is called in produce_impl(). Override this method to produce a different set of chip frames.
        """
        b_frame_parameters = {
            **self.pcell_params_by_name(whitelist=ChipFrame.PARAMETERS_SCHEMA),
            "use_face_prefix": False
        }
        self.produce_frame_and_grid(b_frame_parameters, self.box, self.face(0))

    def produce_impl(self):
        self.produce_frames()
        # unique names to probepoints of subcells
        self._probepoints_copy_and_prefix()
        super().produce_impl()

    def _probepoints_copy_and_prefix(self):
        # copies probing refpoints to chip level with unique names using subcell id property

        for i, inst in enumerate(self.cell.each_inst()):
            refpoints_abs = self.get_refpoints(inst.cell, inst.dtrans)

            inst_id = inst.property("id")
            if not inst_id:
                inst_id = "inst_{}".format(i)

            for name, pos in refpoints_abs.items():
                if name.startswith("probe"):
                    new_name = "{}_{}".format(inst_id, name)
                    self.refpoints[new_name] = pos
