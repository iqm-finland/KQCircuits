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


from autologging import traced, logged
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.chips.chip import Chip
from kqcircuits.elements.chip_frame import ChipFrame
from kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector_dc import FlipChipConnectorDc
from kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf
from kqcircuits.defaults import default_mask_parameters, default_bump_parameters, default_marker_type


@traced
@logged
@add_parameters_from(FlipChipConnectorRf, "connector_type")
class MultiFace(Chip):
    """Base class for multi-face chips.

    Produces labels in pixel corners, dicing edge, markers and optionally grid for all chip faces. Contains methods for
    producing launchers in face 0, connectors between faces 0 and 1, and default routing waveguides from the
    launchers to the connectors.
    """

    a_capped = Param(pdt.TypeDouble, "Capped center conductor width", 10, unit="[μm]",
                     docstring="Width of center conductor in the capped region [μm]")
    b_capped = Param(pdt.TypeDouble, "Width of gap in the capped region ", 10, unit="[μm]")
    face1_box = Param(pdt.TypeShape, "Border of Face 1", pya.DBox(pya.DPoint(1500, 1500), pya.DPoint(8500, 8500)))
    with_face1_gnd_tsvs = Param(pdt.TypeBoolean, "Make ground TSVs on the top face", False)
    with_gnd_bumps = Param(pdt.TypeBoolean, "Make ground bumps", False)
    bump_grid_spacing = Param(
        pdt.TypeDouble, "Bump grid distance (center to center)",
        default_bump_parameters['bump_grid_spacing'], unit="[μm]")
    bump_edge_to_bump_edge_separation = Param(
        pdt.TypeDouble, "In bump clearance to manually placed Bumps (edge to edge)",
        default_bump_parameters['bump_edge_to_bump_edge_separation'], unit="[μm]")
    edge_from_bump = Param(pdt.TypeDouble, "Spacing between bump and chip edge",
                          default_bump_parameters['edge_from_bump'], unit="[μm]")
    face1_marker_types = Param(pdt.TypeList, "Marker type for each top face corner, starting from lower right and "
                                             "going anticlockwise", default=[default_marker_type] * 4)

    def produce_structures(self):
        # produce frame for face 0
        bottom_frame_parameters = self.pcell_params_by_name(
            ChipFrame,
            face_ids=self.face_ids[0],
            use_face_prefix=True,
        )
        self.produce_frame(bottom_frame_parameters)

        # produce frame for face 1
        t_frame_parameters = {
            "box": self.face1_box,
            "marker_dist": 1000,
            "marker_diagonals": 2,
            "face_ids": self.face_ids[1],
            "use_face_prefix": True,
            "dice_width": default_mask_parameters[self.face_ids[1]]["dice_width"],
            "text_margin": default_mask_parameters[self.face_ids[1]]["text_margin"],
            "marker_types": self.face1_marker_types
        }
        t_frame_trans = pya.DTrans(self.box.p2.x, 0) * pya.DTrans.M90
        self.produce_frame(t_frame_parameters, t_frame_trans)

        if self.with_gnd_tsvs:
            self._produce_ground_tsvs(face_id=0)
        if self.with_face1_gnd_tsvs:
            tsv_box = self.face1_box.enlarged(pya.DVector(-self.edge_from_tsv, -self.edge_from_tsv))
            self._produce_ground_tsvs(face_id=1, tsv_box=tsv_box)

        if self.with_gnd_bumps:
            self._produce_ground_bumps()

    def get_ground_bump_locations(self, bump_box):
        """
        Define the locations for a grid. This method returns the full grid.

        Args:
            box: DBox specifying the region that should be filled with ground bumps

        Returns: list of DPoint coordinates where a ground bump can be placed
        """
        return self.make_grid_locations(bump_box, delta_x=self.bump_grid_spacing, delta_y=self.bump_grid_spacing)

    def _produce_ground_bumps(self):
        """Produces ground bumps between bottom and top face.

        The bumps avoid ground grid avoidance on both faces, and keep a minimum distance to any existing (manually
        placed) bumps.
        """
        self.__log.info('Starting ground bump generation')
        bump = self.add_element(FlipChipConnectorDc)

        bump_box = self.face1_box.enlarged(pya.DVector(-self.edge_from_bump, -self.edge_from_bump))

        avoidance_layer_bottom = pya.Region(
            self.cell.begin_shapes_rec(self.get_layer("ground_grid_avoidance", 0))).merged()
        avoidance_layer_top = pya.Region(
            self.cell.begin_shapes_rec(self.get_layer("ground_grid_avoidance", 1))).merged()
        existing_bumps = pya.Region(
            self.cell.begin_shapes_rec(self.get_layer("indium_bump"))).merged()
        existing_bump_count = existing_bumps.count()
        avoidance_existing_bumps = existing_bumps.sized(self.bump_edge_to_bump_edge_separation
                                                        / self.layout.dbu)

        existing_tsvs_bottom = pya.Region(
            self.cell.begin_shapes_rec(self.get_layer("through_silicon_via",0))).merged()
        avoidance_existing_tsvs_bottom = existing_tsvs_bottom.\
            sized((self.tsv_edge_to_nearest_element) / self.layout.dbu)
        existing_tsvs_top = pya.Region(
            self.cell.begin_shapes_rec(self.get_layer("through_silicon_via",1))).merged()
        avoidance_existing_tsvs_top = existing_tsvs_top.sized(self.tsv_edge_to_nearest_element / self.layout.dbu)
        avoidance_region = (avoidance_layer_bottom + avoidance_layer_top + avoidance_existing_bumps +
                            avoidance_existing_tsvs_bottom + avoidance_existing_tsvs_top).merged()

        locations = self.get_ground_bump_locations(bump_box)

        # Determine the shape of the bump from its underbump metallization layer. Assumes that when merged the bump
        # contains only one polygon.
        bump_size_polygon = next(pya.Region(bump.begin_shapes_rec(self.get_layer("underbump_metallization")))
                                 .merged().each())

        # Use pya.Region logic to efficiently filter bumps which are inside the allowed region
        test_object_region = pya.Region([bump_size_polygon.moved(pya.Vector(pos.to_itype(self.layout.dbu)))
                                         for pos in locations])
        passed_object_region = test_object_region.outside(avoidance_region)
        bump_locations = [p.bbox().center().to_dtype(self.layout.dbu) for p in passed_object_region]

        for location in bump_locations:
            self.insert_cell(bump, pya.DTrans(location))

        self.__log.info(f'Found {existing_bump_count} existing bumps and inserted {len(bump_locations)} ground bumps, '
                        + f'totalling {existing_bump_count + len(bump_locations)} bumps.')

    def produce_ground_grid(self):
        """Produces ground grid on t and b faces."""
        for face_id, box in enumerate([self.box, self.face1_box]):
            self.produce_ground_on_face_grid(box, face_id)

    def merge_layout_layers(self):
        """Merges layers on t and b faces."""
        for i in range(int(2)):
            self.merge_layout_layers_on_face(self.face(i))
