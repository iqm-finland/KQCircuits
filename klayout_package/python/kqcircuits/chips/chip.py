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
from autologging import logged

from kqcircuits.defaults import default_layers, default_squid_type, default_sampleholders
from kqcircuits.elements.chip_frame import ChipFrame
from kqcircuits.elements.element import Element
from kqcircuits.elements.launcher import Launcher
from kqcircuits.elements.launcher_dc import LauncherDC
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from, add_parameter
from kqcircuits.test_structures.junction_test_pads import JunctionTestPads
from kqcircuits.test_structures.stripes_test import StripesTest
from kqcircuits.util.groundgrid import make_grid
from kqcircuits.elements.f2f_connectors.tsvs.tsv import Tsv


@logged
@add_parameter(ChipFrame, "box", hidden=True)
@add_parameters_from(ChipFrame, "name_mask", "name_chip", "name_copy",
                     "with_grid", "dice_width", "dice_grid_margin", "marker_types")
class Chip(Element):
    """Base PCell declaration for chips.

    By default produces in face 0 the chip frame consisting of texts in pixel corners, dicing edge, markers and
    optionally grid. Production of the chip frames can be adjusted by overriding the produce_frames() method.

    Provides helpers to produce launchers and junction tests.
    """

    LIBRARY_NAME = "Chip Library"
    LIBRARY_DESCRIPTION = "Superconducting quantum circuit library for chips."
    LIBRARY_PATH = "chips"

    merge_base_metal_gap = Param(pdt.TypeBoolean, "Merge grid and other gaps into base_metal_gap layer", False)
    # Tsv grid parameters
    with_gnd_tsvs = Param(pdt.TypeBoolean, "Make ground TSVs", False)
    tsv_grid_spacing = Param(pdt.TypeDouble,"TSV grid distance (center to center)", 300, unit="μm")
    tsv_edge_to_tsv_edge_separation = \
        Param(pdt.TypeDouble, "Ground TSV clearance to manually placed TSVs (edge to edge)", 250, unit="μm")
    tsv_edge_to_nearest_element = Param(pdt.TypeDouble, "Ground TSV clearance to other elements (edge to edge)",
                                        100, unit="μm")
    edge_from_tsv = Param(pdt.TypeDouble, "Ground TSV center clearance to chip edge", 550, unit="μm")

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "{}".format(self.name_chip)

    def can_create_from_shape_impl(self):
        return self.shape.is_box()

    def parameters_from_shape_impl(self):
        self.box = pya.DBox(0, 0, self.shape.box_dwidth, self.shape.box_dheight)

    def transformation_from_shape_impl(self):
        return pya.Trans(self.shape.box_p1)

    @staticmethod
    def get_launcher_assignments(chip_cell):
        """Returns a dictionary of launcher assignments (port_id: launcher_id) for the chip.

        Args:
            chip_cell: Cell object of the chip
        """

        launcher_assignments = {}

        for inst in chip_cell.each_inst():
            port_name = inst.property("port_id")
            if port_name is not None:
                launcher_assignments[port_name] = inst.property("id")

        return launcher_assignments

    def produce_junction_tests(self, squid_type=default_squid_type):
        """Produces junction test pads in the chip.

        Args:
            squid_type: A string defining the type of SQUIDs used in the test pads.

        """
        junction_tests_w = self.add_element(JunctionTestPads,
                                            margin=50,
                                            area_height=1300,
                                            area_width=2500,
                                            junctions_horizontal=True,
                                            squid_type=squid_type,
                                            display_name="JunctionTestsHorizontal",
                                            )
        junction_tests_h = self.add_element(JunctionTestPads,
                                            margin=50,
                                            area_height=2500,
                                            area_width=1300,
                                            junctions_horizontal=True,
                                            squid_type=squid_type,
                                            display_name="JunctionTestsVertical",
                                            )
        self.insert_cell(junction_tests_h, pya.DTrans(0, False, .35e3, (10e3 - 2.5e3) / 2), "testarray_w")
        self.insert_cell(junction_tests_w, pya.DTrans(0, False, (10e3 - 2.5e3) / 2, .35e3), "testarray_s")
        self.insert_cell(junction_tests_h, pya.DTrans(0, False, 9.65e3 - 1.3e3, (10e3 - 2.5e3) / 2), "testarray_e")
        self.insert_cell(junction_tests_w, pya.DTrans(0, False, (10e3 - 2.5e3) / 2, 9.65e3 - 1.3e3), "testarray_n")

    def produce_opt_lit_tests(self):
        """Produces optical lithography test stripes at chip corners."""

        num_stripes = 20
        length = 100
        min_width = 1
        max_width = 15
        step = 3
        first_stripes_width = 2 * num_stripes * min_width

        combined_cell = self.layout.create_cell("Stripes")
        for i, width in enumerate(numpy.arange(max_width + 0.1 * step, min_width, -step)):
            stripes_cell = self.add_element(StripesTest, num_stripes=num_stripes, stripe_width=width,
                                            stripe_length=length)
            # horizontal
            combined_cell.insert(pya.DCellInstArray(stripes_cell.cell_index(),
                                                    pya.DCplxTrans(1, 0, False, -880, 2 * i * length +
                                                                   first_stripes_width - 200)))
            # vertical
            combined_cell.insert(pya.DCellInstArray(stripes_cell.cell_index(),
                                                    pya.DCplxTrans(1, 90, False,
                                                                   2 * i * length + length + first_stripes_width - 200,
                                                                   -880)))
            # diagonal
            diag_offset = 2 * num_stripes * width / numpy.sqrt(8)
            combined_cell.insert(pya.DCellInstArray(stripes_cell.cell_index(),
                                                    pya.DCplxTrans(1, -45, False, 250 + i * length - diag_offset,
                                                                   250 + i * length + diag_offset)))

        self.insert_cell(combined_cell, pya.DCplxTrans(1, 0, False, 1500, 1500))
        self.insert_cell(combined_cell, pya.DCplxTrans(1, 90, False, 8500, 1500))
        self.insert_cell(combined_cell, pya.DCplxTrans(1, 180, False, 8500, 8500))
        self.insert_cell(combined_cell, pya.DCplxTrans(1, 270, False, 1500, 8500))

    def produce_ground_grid(self):
        """Produces ground grid on the face of the element.

        This method is called in build(). Override this method to produce a different set of chip frames.
        """
        self.produce_ground_on_face_grid(self.box, 0)

    def produce_ground_on_face_grid(self, box, face_id):
        """Produces ground grid in the given face of the chip.

        Args:
            box: pya.DBox within which the grid is created
            face_id (str): ID of the face where the grid is created

        """
        grid_area = box * (1 / self.layout.dbu)
        protection = pya.Region(self.cell.begin_shapes_rec(self.get_layer("ground_grid_avoidance", face_id))).merged()
        grid_mag_factor = 1
        region_ground_grid = make_grid(grid_area, protection,
                                       grid_step=10 * (1 / self.layout.dbu) * grid_mag_factor,
                                       grid_size=5 * (1 / self.layout.dbu) * grid_mag_factor)
        self.cell.shapes(self.get_layer("ground_grid", face_id)).insert(region_ground_grid)

    def produce_frame(self, frame_parameters, trans=pya.DTrans()):
        """Produces a chip frame and markers for the given face.

        Args:
            frame_parameters: PCell parameters for the chip frame
            trans: DTrans for the chip frame, default=pya.DTrans()
        """
        self.insert_cell(ChipFrame, trans, **frame_parameters)

    def merge_layout_layers_on_face(self, face):
        """Creates "base_metal_gap" layer on given face.

         The layer shape is combination of three layers using subtract (-) and insert (+) operations:

            "base_metal_gap" = "base_metal_gap_wo_grid" - "base_metal_addition" + "ground_grid"
        """
        gaps = pya.Region(self.cell.begin_shapes_rec(self.layout.layer(face["base_metal_gap_wo_grid"])))
        metal = pya.Region(self.cell.begin_shapes_rec(self.layout.layer(face["base_metal_addition"])))
        grid = self.cell.begin_shapes_rec(self.layout.layer(face["ground_grid"]))
        res = self.cell.shapes(self.layout.layer(face["base_metal_gap"]))
        res.insert(gaps - metal)
        res.insert(grid)

    def merge_layout_layers(self):
        """Creates "base_metal_gap" layer.

         The layer shape is combination of three layers using subtract (-) and insert (+) operations:

            "base_metal_gap" = "base_metal_gap_wo_grid" - "base_metal_addition" + "ground_grid"

        This method is called in build(). Override this method to produce a different set of chip frames.
        """
        self.merge_layout_layers_on_face(self.face(0))

    def produce_structures(self):
        """Produces chip frame and possibly other structures before the ground grid.

        This method is called in build(). Override this method to produce a different set of chip frames.
        """
        b_frame_parameters = self.pcell_params_by_name(ChipFrame, use_face_prefix=False)
        self.produce_frame(b_frame_parameters)
        if self.with_gnd_tsvs:
            self._produce_ground_tsvs(face_id=0)

    def build(self):
        self.produce_structures()
        if self.with_grid:
            self.produce_ground_grid()
        if self.merge_base_metal_gap:
            self.merge_layout_layers()
        self._produce_instance_name_labels()

    def _produce_instance_name_labels(self):

        for inst in self.cell.each_inst():
            inst_id = inst.property("id")
            if inst_id:
                cell = self.layout.create_cell("TEXT", "Basic", {
                    "layer": default_layers["instance_names"],
                    "text": inst_id,
                    "mag": 400.0
                })
                label_trans = inst.dcplx_trans
                # prevent the label from being upside-down or mirrored
                if 90 < label_trans.angle < 270:
                    label_trans.angle += 180
                label_trans.mirror = False
                # optionally apply relative transformation to the label
                rel_label_trans_str = inst.property("label_trans")
                if rel_label_trans_str is not None:
                    rel_label_trans = pya.DCplxTrans.from_s(rel_label_trans_str)
                    label_trans = label_trans * rel_label_trans
                self.insert_cell(cell, label_trans)

    def produce_launchers(self, sampleholder_type, launcher_assignments=None, enabled=None):
        """Produces launchers for typical sample holders and sets chip size (``self.box``) accordingly.

        This is a wrapper around ``produce_n_launchers()`` to generate typical launcher configurations.

        Args:
            sampleholder_type: name of the sample holder type
            launcher_assignments: dictionary of (port_id: name) that assigns a name to some of the launchers
            enabled: list of enabled launchers, empty means all

        Returns:
            launchers as a dictionary :code:`{name: (point, heading, distance from chip edge)}`

        """

        if sampleholder_type == "SMA8":  # this is special: it has default launcher assignments
            if not launcher_assignments:
                launcher_assignments = {1: "NW", 2: "NE", 3: "EN", 4: "ES", 5: "SE", 6: "SW", 7: "WS", 8: "WN"}

        if sampleholder_type in default_sampleholders:
            return self.produce_n_launchers(**default_sampleholders[sampleholder_type],
                                            launcher_assignments=launcher_assignments, enabled=enabled)
        return {}

    def produce_n_launchers(self, n, launcher_type, launcher_width, launcher_gap, launcher_indent, pad_pitch,
                            launcher_assignments=None, enabled=None, chip_box=None):
        """Produces n launchers at default locations and optionally changes the chip size.

        Launcher pads are equally distributed around the chip. This may be overridden by specifying
        the number of pads desired per chip side if ``n`` is an array of 4 numbers.

        Pads not in ``launcher_assignments`` are disabled by default. The ``enabled`` argument may
        override this. If neither argument is defined then all pads are enabled with default names.

        Args:
            n: number of launcher pads or an array of pad numbers per side
            launcher_type: type of the launchers, "RF" or "DC"
            launcher_width: width of the launchers
            launcher_gap: pad to ground gap of the launchers
            launcher_indent: distance between the chip edge and pad port
            pad_pitch: distance between pad centers
            launcher_assignments: dictionary of (port_id: name) that assigns a name to some of the launchers
            enabled: optional list of enabled launchers
            chip_box: optionally changes the chip size (``self.box``)

        Returns:
            launchers as a dictionary :code:`{name: (point, heading, distance from chip edge)}`
        """

        if chip_box is not None:
            self.box = chip_box

        if launcher_type == "DC":
            launcher_cell = self.add_element(LauncherDC, width=launcher_width)
        else:
            launcher_cell = self.add_element(Launcher, s=launcher_width, l=launcher_width,
                                             a_launcher=launcher_width, b_launcher=launcher_gap)

        pads_per_side = n
        if not isinstance(n, tuple):
            n = int((n + n % 4) / 4)
            pads_per_side = [n, n, n, n]

        dirs = (90, 0, -90, 180)
        trans = (pya.DTrans(3, 0, self.box.p1.x, self.box.p2.y),
                 pya.DTrans(2, 0, self.box.p2.x, self.box.p2.y),
                 pya.DTrans(1, 0, self.box.p2.x, self.box.p1.y),
                 pya.DTrans(0, 0, self.box.p1.x, self.box.p1.y))
        _w = self.box.p2.x - self.box.p1.x
        _h = self.box.p2.y - self.box.p1.y
        sides = [_w, _h, _w, _h]

        launchers = {}  # dictionary of point, heading, distance from chip edge

        port_id = 0
        for np, dr, tr, si in zip(pads_per_side, dirs, trans, sides):
            for i in range(np):
                port_id += 1
                if launcher_assignments:
                    if port_id in launcher_assignments:
                        name = launcher_assignments[port_id]
                    else:
                        continue
                else:
                    name = str(port_id)

                if enabled and name not in enabled:
                    continue

                loc = tr * pya.DPoint(launcher_indent, si / 2 + pad_pitch * (i + 0.5 - np / 2))
                launchers[name] = (loc, dr, launcher_width)

                transf = pya.DCplxTrans(1, dr, False, loc)
                launcher_inst, launcher_refpoints = self.insert_cell(launcher_cell, transf, name)
                launcher_inst.set_property("port_id", port_id)
                self.add_port(name, launcher_refpoints["port"])

        return launchers

    def make_grid_locations(self, box, delta_x=100, delta_y=100):  # pylint: disable=no-self-use
        """
        Define the locations for a grid. This method returns the full grid.

        Args:
            box: DBox specifying a region for a grid
            delta_x: Int or float specifying the grid separation along the x dimension
            delta_y: Int or float specifying the grid separation along the y dimension

        Returns: list of DPoint coordinates for the grid.
        """

        # array size for bump creation
        n = int((box.p2 - box.p1).x / delta_x/2 )*2 # force even number
        m = int((box.p2 - box.p1).y / delta_y/2 )*2 # force even number

        locations = []
        for i in numpy.linspace(-n/2,n/2, n+1):
            for j in numpy.linspace(-m/2,m/2, m+1):
                locations.append(box.center() + pya.DPoint(i * delta_x, j * delta_y))
        return locations

    def get_ground_tsv_locations(self, tsv_box):
        """
        Define the locations for a grid. This method returns the full grid.

        Args:
            box: DBox specifying the region that should be filled with TSVs

        Returns: list of DPoint coordinates where a ground bump can be placed
        """
        return self.make_grid_locations(tsv_box, delta_x=self.tsv_grid_spacing, delta_y=self.tsv_grid_spacing)

    def _produce_ground_tsvs(self,
                             face_id =0,
                             tsv_box =  None):
        """Produces ground TSVs between bottom and top face.

         The TSVs avoid ground grid avoidance on both faces, and keep a minimum distance to any existing (manually
         placed) TSVs.
         """
        self.__log.info(f'Starting ground TSV generation on face { self.face_ids[face_id] }')
        tsv = self.add_element(Tsv, n=self.n, face_ids = [self.face_ids[face_id]])

        if tsv_box is None:
            tsv_box = self.box.enlarged(pya.DVector(-self.edge_from_tsv, -self.edge_from_tsv))

        def region_from_layer(layer_name):
            return pya.Region(self.cell.begin_shapes_rec(self.get_layer(layer_name, face_id))).merged()

        avoidance_region = (region_from_layer("ground_grid_avoidance") +
                            region_from_layer("through_silicon_via_avoidance")).merged()
        avoidance_existing_tsv_region = region_from_layer("through_silicon_via")
        existing_tsv_count = avoidance_existing_tsv_region.count()
        avoidance_to_element_region = (region_from_layer("base_metal_gap_wo_grid")
                                       + region_from_layer("indium_bump")).merged()

        locations = self.get_ground_tsv_locations(tsv_box)
        locations_itype = [pya.Vector(pos.to_itype(self.layout.dbu)) for pos in locations]

        # Determine the shape of the tsv from its through_silicon_via layer. Assumes that when merged the tsv
        # contains only one polygon.
        tsv_size_polygon = next(pya.Region(tsv.begin_shapes_rec(self.get_layer("through_silicon_via", face_id)))
                                .merged().each())

        def filter_locations(filter_region, separation, input_locations):
            sized_tsv = tsv_size_polygon.sized(separation / self.layout.dbu)
            test_region = pya.Region([sized_tsv.moved(pos) for pos in input_locations])
            test_region.merged_semantics = False
            pass_region = test_region.outside(filter_region)
            output_locations = [p.bbox().center() for p in pass_region]
            return output_locations

        locations_itype = filter_locations(avoidance_region, 0, locations_itype)
        locations_itype = filter_locations(avoidance_existing_tsv_region,
                                           self.tsv_edge_to_tsv_edge_separation, locations_itype)
        locations_itype = filter_locations(avoidance_to_element_region,
                                           self.tsv_edge_to_nearest_element, locations_itype)

        tsv_locations = [pos.to_dtype(self.layout.dbu) for pos in locations_itype]

        for location in tsv_locations:
            self.insert_cell(tsv, pya.DTrans(location))

        self.__log.info(f'Found {existing_tsv_count} existing TSVs and inserted {len(tsv_locations)} ground TSVs, '
                        + f'totalling {existing_tsv_count + len(tsv_locations)} TSVs.')
