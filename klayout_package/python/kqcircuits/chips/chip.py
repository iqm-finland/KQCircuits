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
# pylint: disable=R0904
# TODO: Consider refactoring to reduce number of public methods

import logging
import numpy

from kqcircuits.defaults import default_layers, default_junction_type, default_sampleholders, default_mask_parameters, \
    default_bump_parameters, default_marker_type
from kqcircuits.elements.chip_frame import ChipFrame
from kqcircuits.elements.element import Element
from kqcircuits.elements.launcher import Launcher
from kqcircuits.elements.launcher_dc import LauncherDC
from kqcircuits.pya_resolver import pya
from kqcircuits.util.merge import merge_layout_layers_on_face
from kqcircuits.util.parameters import Param, pdt, add_parameters_from, add_parameter
from kqcircuits.test_structures.junction_test_pads.junction_test_pads import JunctionTestPads
from kqcircuits.test_structures.stripes_test import StripesTest
from kqcircuits.util.groundgrid import make_grid
from kqcircuits.elements.tsvs.tsv import Tsv
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_dc import FlipChipConnectorDc
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf


@add_parameters_from(Tsv, "tsv_type")
@add_parameters_from(FlipChipConnectorRf, "connector_type")
@add_parameter(ChipFrame, "box", hidden=True)
@add_parameters_from(ChipFrame, "name_mask", "name_chip", "name_copy", "name_brand", "chip_dicing_in_base_metal",
                     "dice_grid_margin", marker_types=[default_marker_type] * 8)
class Chip(Element):
    """Base PCell declaration for chips.

    Produces labels in pixel corners, dicing edge, markers and optionally grid for all chip faces.
    Contains methods for producing launchers in face 0 and connectors between faces 0 and 1.
    """

    LIBRARY_NAME = "Chip Library"
    LIBRARY_DESCRIPTION = "Superconducting quantum circuit library for chips."
    LIBRARY_PATH = "chips"

    with_grid = Param(pdt.TypeBoolean, "Make ground plane grid", False)
    merge_base_metal_gap = Param(pdt.TypeBoolean, "Merge grid and other gaps into base_metal_gap layer", False)
    a_capped = Param(pdt.TypeDouble, "Capped center conductor width", 10, unit="μm",
                     docstring="Width of center conductor in the capped region (μm)")
    b_capped = Param(pdt.TypeDouble, "Width of gap in the capped region ", 10, unit="μm")

    # TSV grid parameters
    with_gnd_tsvs = Param(pdt.TypeBoolean, "Make a grid of through-silicon vias (TSVs)", False)
    with_face1_gnd_tsvs = Param(pdt.TypeBoolean, "Make a grid of TSVs on top chip", False)
    tsv_grid_spacing = Param(pdt.TypeDouble, "TSV grid spacing (center to center)", 300, unit="μm")
    edge_from_tsv = Param(pdt.TypeDouble, "TSV grid clearance to chip edge (center to edge)", 550, unit="μm")
    tsv_edge_to_tsv_edge_separation = Param(pdt.TypeDouble, "TSV grid clearance to existing TSVs (edge to edge)", 250,
                                            unit="μm")
    tsv_edge_to_nearest_element = Param(pdt.TypeDouble, "TSV grid clearance to other elements (edge to edge)", 100,
                                        unit="μm")

    # Bump grid parameters
    with_gnd_bumps = Param(pdt.TypeBoolean, "Make a grid of indium bumps", False)
    bump_grid_spacing = Param(pdt.TypeDouble, "Bump grid spacing (center to center)",
                              default_bump_parameters['bump_grid_spacing'], unit="μm")
    edge_from_bump = Param(pdt.TypeDouble, "Bump grid clearance to chip edge (center to edge)",
                           default_bump_parameters['edge_from_bump'], unit="μm")
    bump_edge_to_bump_edge_separation = Param(pdt.TypeDouble, "Bump grid clearance to existing bumps (edge to edge)",
                                              default_bump_parameters['bump_edge_to_bump_edge_separation'], unit="μm")

    frames_enabled = Param(pdt.TypeList, "List of face ids (integers) for which a ChipFrame is drawn", [0])
    frames_marker_dist = Param(pdt.TypeList, "Marker distance from edge for each chip frame", [1500, 1000], unit="[μm]")
    frames_diagonal_squares = Param(pdt.TypeList, "Number of diagonal marker squares for each chip frame", [10, 2])
    frames_mirrored = Param(pdt.TypeList,
                            "List of booleans specifying if the frame is mirrored for each chip frame", [False, True])
    frames_dice_width = Param(pdt.TypeList, "Dicing street width for each chip frame", [200, 140], unit="[μm]")

    face_boxes = Param(
        pdt.TypeShape,
        "List of chip frame sizes (type DBox) for each face. None uses the chips box parameter.",
        default=[None, pya.DBox(pya.DPoint(1500, 1500), pya.DPoint(8500, 8500))],
        hidden=True)

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

    def produce_junction_tests(self, junction_type=default_junction_type):
        """Produces junction test pads in the chip.

        Args:
            junction_type: A string defining the type of junction used in the test pads.

        """
        junction_tests_w = self.add_element(JunctionTestPads,
                                            margin=50,
                                            area_height=1300,
                                            area_width=2500,
                                            junctions_horizontal=True,
                                            junction_type=junction_type,
                                            display_name="JunctionTestsHorizontal",
                                            )
        junction_tests_h = self.add_element(JunctionTestPads,
                                            margin=50,
                                            area_height=2500,
                                            area_width=1300,
                                            junctions_horizontal=True,
                                            junction_type=junction_type,
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
        """Produces ground grid on all faces with ChipFrames.

        This method is called in build(). Override this method to produce a different set of chip frames.
        """
        for face in self.frames_enabled:
            self.produce_ground_on_face_grid(self.get_box(int(face)), int(face))

    def produce_ground_on_face_grid(self, box, face_id):
        """Produces ground grid in the given face of the chip.

        Args:
            box: pya.DBox within which the grid is created
            face_id (int): ID of the face where the grid is created

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

    def merge_layout_layers_on_face(self, face, tolerance=0.004):
        """Creates "base_metal_gap" layer on given face.

        The layer shape is combination of three layers using subtract (-) and insert (+) operations:

            "base_metal_gap" = "base_metal_gap_wo_grid" - "base_metal_addition" + "ground_grid"

        Args:
            face: face dictionary containing layer names as keys and layer info objects as values
            tolerance: gap length to be ignored while merging (µm)
        """
        merge_layout_layers_on_face(self.layout, self.cell, face, tolerance)

    def merge_layout_layers(self):
        """Creates "base_metal_gap" layers on all faces.

         The layer shape is combination of three layers using subtract (-) and insert (+) operations:

            "base_metal_gap" = "base_metal_gap_wo_grid" - "base_metal_addition" + "ground_grid"

        This method is called in build(). Override this method to produce a different set of chip frames.
        """
        for i in range(len(self.face_ids)):
            self.merge_layout_layers_on_face(self.face(i))

    def produce_structures(self):
        """Produces chip frame and possibly other structures before the ground grid.

        This method is called in post_build(). Override this method to produce a different set of chip frames.
        """

        for i, face in enumerate(self.frames_enabled):
            face = int(face)
            frame_box = self.get_box(face)
            frame_parameters = self.pcell_params_by_name(
                ChipFrame,
                box=frame_box,
                face_ids=[self.face_ids[face]],
                use_face_prefix=len(self.frames_enabled) > 1,
                dice_width=float(self.frames_dice_width[i]),
                text_margin=default_mask_parameters[self.face_ids[face]]["text_margin"],
                marker_dist=float(self.frames_marker_dist[i]),
                diagonal_squares=int(self.frames_diagonal_squares[i]),
                marker_types=self.marker_types[i * 4:(i + 1) * 4]
            )

            if str(self.frames_mirrored[i]).lower() == 'true':  # Accept both boolean and string representation
                frame_trans = pya.DTrans(frame_box.center()) * pya.DTrans.M90 * pya.DTrans(-frame_box.center())
            else:
                frame_trans = pya.DTrans(0, 0)
            self.produce_frame(frame_parameters, frame_trans)

        if self.with_gnd_tsvs:
            self._produce_ground_tsvs(faces=[0, 2])
        if self.with_face1_gnd_tsvs:
            tsv_box = self.get_box(1).enlarged(pya.DVector(-self.edge_from_tsv, -self.edge_from_tsv))
            self._produce_ground_tsvs(faces=[3, 1], tsv_box=tsv_box)

    def get_box(self, face=0):
        """
        Get the chip frame box for the specified face, correctly resolving defaults.

        Args:
            face: Integer specifying face, default 0

        Returns: pya.DBox box for the specified face
        """
        box = self.face_boxes[face]
        return box if box is not None else self.box

    def get_filter_regions(self, filter_layer_list):
        """Transforms the filter_layer_list into filter_regions dictionary.

        Args:
            filter_layer_list: tuple (layer_name, face, distance) specifying the distances to filtering layers

        Returns:
            dict with distances as keys and filtering regions as values
        """
        filter_regions = {distance: pya.Region() for _, _, distance in filter_layer_list}
        for layer, face, distance in filter_layer_list:
            if layer in self.face(face):
                filter_regions[distance] += pya.Region(self.cell.begin_shapes_rec(self.get_layer(layer, face)))
        return {distance: region for distance, region in filter_regions.items() if not region.is_empty()}

    def insert_filtered_elements(self, element_cell, shape_layers, filter_regions, locations, rotation=0):
        """Inserts elements into given locations filtered by filter_regions.

        Args:
            element_cell: pya.Cell specifying the element to be repeated in the grid
            shape_layers: tuple (layer_name, face) specifying the shape layers on the element_cell
            filter_regions: dict with distances as keys and filtering regions as values
            locations: list of grid element locations as DPoints
            rotation: element rotation in degrees

        Returns:
            list of filtered grid element locations
        """
        # Get element shape
        shape = pya.Region()
        for shape_layer in shape_layers:
            shape += pya.Region(element_cell.begin_shapes_rec(self.get_layer(*shape_layer)))
        shape.transform(pya.ICplxTrans(1, rotation, False, 0, 0))

        # Filter locations
        locations_itype = [pya.Vector(pos.to_itype(self.layout.dbu)) for pos in locations]
        for distance, filter_region in filter_regions.items():
            # Create expanded shape polygon
            shape_polygons = list(shape.sized(distance / self.layout.dbu).merged().each())
            if len(shape_polygons) == 1:
                shape_polygon = shape_polygons[0]  # use actual element shape
            elif len(shape_polygons) > 1:
                shape_polygon = pya.Polygon(shape.bbox())  # use bounding box if shape consists of multiple polygons
            else:
                shape_polygon = pya.Polygon(pya.Box(2))  # use small box around origin if shape_region is empty
            shape_center = shape_polygon.bbox().center()

            # Filter locations
            test_region = pya.Region([shape_polygon.moved(pos) for pos in locations_itype])
            test_region.merged_semantics = False
            pass_region = test_region.outside(filter_region)
            locations_itype = [p.bbox().center() - shape_center for p in pass_region]

        # Insert elements into filtered locations
        passed_locations = [pos.to_dtype(self.layout.dbu) for pos in locations_itype]
        for passed_location in passed_locations:
            self.insert_cell(element_cell, pya.DCplxTrans(1, rotation, False, passed_location))
        return passed_locations

    def get_ground_bump_locations(self, bump_box):
        """
        Define the locations for a grid. This method returns the full grid.

        Args:
            bump_box: DBox specifying the region that should be filled with ground bumps

        Returns: list of DPoint coordinates where a ground bump can be placed
        """
        return self.make_grid_locations(bump_box, delta_x=self.bump_grid_spacing, delta_y=self.bump_grid_spacing)

    def _produce_ground_bumps(self, faces=[0, 1]):  # pylint: disable=dangerous-default-value
        """Produces a grid of indium bumps between given faces.

        The bumps avoid ground grid avoidance on both faces, and keep a minimum distance to existing bumps.
        """
        logging.info('Starting bump grid generation')

        # Count existing bump count for logging purpose
        existing_bump_region = pya.Region()
        for face in faces:
            existing_bump_region += pya.Region(self.cell.begin_shapes_rec(self.get_layer("indium_bump", face)))
        existing_bump_count = existing_bump_region.merged().count()

        # Specify bump element, filter regions, and locations
        bump = self.add_element(FlipChipConnectorDc, face_ids=[self.face_ids[face] for face in faces])
        shape_layers = [("underbump_metallization", face) for face in faces]
        filter_regions = self.get_filter_regions(
            [("ground_grid_avoidance", face, 0) for face in faces] +
            [("indium_bump", face, self.bump_edge_to_bump_edge_separation) for face in faces] +
            [("through_silicon_via", face, self.tsv_edge_to_nearest_element) for face in faces])
        bump_box = self.get_box(1).enlarged(pya.DVector(-self.edge_from_bump, -self.edge_from_bump))
        locations = self.get_ground_bump_locations(bump_box)

        # Produce bump grid
        if isinstance(locations, dict):
            # bumps are grouped by rotation
            bump_locations = []
            for rotation, locs in locations.items():
                bump_locations += self.insert_filtered_elements(bump, shape_layers, filter_regions, locs, rotation)
        else:
            # Use default rotation for all bumps
            bump_locations = self.insert_filtered_elements(bump, shape_layers, filter_regions, locations)

        logging.info(f'Found {existing_bump_count} existing bumps and inserted {len(bump_locations)} bumps on grid, '
                     f'totalling {existing_bump_count + len(bump_locations)} bumps.')
        return bump_locations

    def post_build(self):
        self.produce_structures()
        if self.with_gnd_bumps:
            self._produce_ground_bumps()
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

    def produce_launchers(self, sampleholder_type, launcher_assignments=None, enabled=None, face_id=0):
        """Produces launchers for typical sample holders and sets chip size (``self.box``) accordingly.

        This is a wrapper around ``produce_n_launchers()`` to generate typical launcher configurations.

        Args:
            sampleholder_type: name of the sample holder type
            launcher_assignments: dictionary of (port_id: name) that assigns a name to some of the launchers
            enabled: list of enabled launchers, empty means all
            face_id: index of face_ids in which to insert the launchers

        Returns:
            launchers as a dictionary :code:`{name: (point, heading, distance from chip edge)}`

        """

        if sampleholder_type == "SMA8":  # this is special: it has default launcher assignments
            if not launcher_assignments:
                launcher_assignments = {1: "NW", 2: "NE", 3: "EN", 4: "ES", 5: "SE", 6: "SW", 7: "WS", 8: "WN"}

        if sampleholder_type in default_sampleholders:
            return self.produce_n_launchers(**default_sampleholders[sampleholder_type],
                                            launcher_assignments=launcher_assignments, enabled=enabled, face_id=face_id)
        return {}

    def produce_n_launchers(self, n, launcher_type, launcher_width, launcher_gap, launcher_indent, pad_pitch,
                            launcher_assignments=None, port_id_remap=None, launcher_frame_gap=None, enabled=None,
                            chip_box=None, face_id=0):
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
            launcher_frame_gap: gap of the launcher pad at the frame
            launcher_assignments: dictionary of (port_id: name) that assigns a name to some of the launchers
            port_id_remap: by default, left-most top edge launcher has port_id set to 1 and port_ids
                increment for other launchers in clockwise order.
                port_id_remap is a dictionary [1..n] -> [1..n] such that for port_id_remap[x] = y,
                x is the port_id of the launcher in default order and y is the port_id of that launcher
                in your desired order.
                For example, to flip the launcher order by chip's y-axis, set port_id_remap to
                ``{i+1: ((n - i + n/4-1) % n) + 1 for i in range(n)}``
            enabled: optional list of enabled launchers
            chip_box: optionally changes the chip size (``self.box``)
            face_id: index of face_ids in which to insert the launchers

        Returns:
            launchers as a dictionary :code:`{name: (point, heading, distance from chip edge)}`
        """

        if launcher_frame_gap is None:
            launcher_frame_gap = launcher_gap

        if chip_box is not None:
            self.box = chip_box

        if launcher_type == "DC":
            launcher_cell = self.add_element(LauncherDC, width=launcher_width, face_ids=[self.face_ids[face_id]])
        else:
            launcher_cell = self.add_element(Launcher, s=launcher_width, l=launcher_width,
                                             a_launcher=launcher_width, b_launcher=launcher_gap,
                                             launcher_frame_gap=launcher_frame_gap, face_ids=[self.face_ids[face_id]])

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

        return self._insert_launchers(dirs, enabled, launcher_assignments, port_id_remap, launcher_cell,
                                      launcher_indent, launcher_width, pad_pitch, pads_per_side, sides, trans,
                                      face_id=face_id)

    def _insert_launchers(self, dirs, enabled, launcher_assignments, port_id_remap, launcher_cell, launcher_indent,
                          launcher_width, pad_pitch, pads_per_side, sides, trans, face_id):
        """Inserts launcher cell at predefined parameters and returns launcher cells

        """
        launcher_order_idx, launchers = 0, {}
        for np, dr, tr, si in zip(pads_per_side, dirs, trans, sides):
            for i in range(np):
                launcher_order_idx += 1
                if port_id_remap:
                    port_id = port_id_remap.get(launcher_order_idx, launcher_order_idx)
                else:
                    port_id = launcher_order_idx

                if launcher_assignments:
                    if port_id not in launcher_assignments:
                        continue
                    name = launcher_assignments[port_id]

                else:
                    name = str(port_id)

                if enabled and name not in enabled:
                    continue

                loc = tr * pya.DPoint(launcher_indent, si / 2 + pad_pitch * (i + 0.5 - np / 2))
                launchers[name] = (loc, dr, launcher_width)

                transf = pya.DCplxTrans(1, dr, False, loc)
                launcher_inst, launcher_refpoints = self.insert_cell(launcher_cell, transf, name)
                launcher_inst.set_property("port_id", port_id)
                self.add_port(name, launcher_refpoints["port"], face_id=face_id)
        return launchers

    def make_grid_locations(self, box, delta_x=100, delta_y=100, x0=0, y0=0):  # pylint: disable=no-self-use
        """
        Define the locations for a grid. This method returns the full grid.

        Args:
            box: DBox specifying a region for a grid
            delta_x: Int or float specifying the grid separation along the x dimension
            delta_y: Int or float specifying the grid separation along the y dimension
            x0: Int or float specifying the center point displacement along the x-axis
            y0: Int or float specifying the center point displacement along the y-axis

        Returns: list of DPoint coordinates for the grid.
        """

        # array size for grid creation
        x_neg = int((box.width() / 2 + x0) / delta_x)
        x_pos = int((box.width() / 2 - x0) / delta_x)
        y_neg = int((box.height() / 2 + y0) / delta_y)
        y_pos = int((box.height() / 2 - y0) / delta_y)

        locations = []
        for i in numpy.linspace(-x_neg, x_pos, x_neg + x_pos + 1):
            for j in numpy.linspace(-y_neg, y_pos, y_neg + y_pos + 1):
                locations.append(box.center() + pya.DPoint(x0 + i * delta_x, y0 + j * delta_y))
        return locations

    def get_ground_tsv_locations(self, tsv_box):
        """
        Define the locations for a grid. This method returns the full grid.

        Args:
            box: DBox specifying the region that should be filled with TSVs

        Returns: list of DPoint coordinates where a ground bump can be placed
        """
        return self.make_grid_locations(tsv_box, delta_x=self.tsv_grid_spacing, delta_y=self.tsv_grid_spacing)

    def _produce_ground_tsvs(self, faces=[0, 2], tsv_box=None):  # pylint: disable=dangerous-default-value
        """Produces a grid of TSVs between given faces.

         The TSVs avoid ground grid avoidance on both faces, and keep a distance to existing elements.
         """
        logging.info(f'Starting TSV grid generation on face(s) {[self.face_ids[face] for face in faces]}')

        # Count existing TSV count for logging purpose
        existing_tsv_region = pya.Region()
        for face in faces:
            existing_tsv_region += pya.Region(self.cell.begin_shapes_rec(self.get_layer("through_silicon_via", face)))
        existing_tsv_count = existing_tsv_region.merged().count()

        # Specify tsv element, filter regions, and locations
        tsv = self.add_element(Tsv, face_ids=[self.face_ids[face] for face in faces])
        shape_layers = [("through_silicon_via", face) for face in faces]
        filter_regions = self.get_filter_regions(
            [("ground_grid_avoidance", face, 0) for face in faces] +
            [("through_silicon_via_avoidance", face, 0) for face in faces] +
            [("indium_bump", face, self.tsv_edge_to_nearest_element) for face in faces] +
            [("base_metal_gap_wo_grid", face, self.tsv_edge_to_nearest_element) for face in faces] +
            [("through_silicon_via", face, self.tsv_edge_to_tsv_edge_separation) for face in faces])
        locations = self.get_ground_tsv_locations(tsv_box if tsv_box is not None else
                                                  self.box.enlarged(-self.edge_from_tsv))

        # Produce TSV grid
        if isinstance(locations, dict):
            # TSVs are grouped by rotation
            tsv_locations = []
            for rotation, locs in locations.items():
                tsv_locations += self.insert_filtered_elements(tsv, shape_layers, filter_regions, locs, rotation)
        else:
            # Use default rotation for all TSVs
            tsv_locations = self.insert_filtered_elements(tsv, shape_layers, filter_regions, locations)

        logging.info(f'Found {existing_tsv_count} existing TSVs and inserted {len(tsv_locations)} TSVs on grid, '
                     f'totalling {existing_tsv_count + len(tsv_locations)} TSVs.')
        return tsv_locations
