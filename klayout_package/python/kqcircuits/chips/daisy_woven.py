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


from kqcircuits.chips.chip import Chip
from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from

@add_parameters_from(Chip, frames_enabled=[0, 1])
class DaisyWoven(Chip):
    """Base PCell declaration for a Daisy Woven chip.

    Includes texts in pixel corners, dicing edge, launchers and manually-drawn daisy pattern.
    No input parameters on this class.
    """

    name_chip = Param(pdt.TypeString, "Name of the chip", "DC")

    def build(self):
        self._produce_daisy_face("Daisy_woven")

    def _produce_daisy_face(self, cell_name):
        # first create chip frame to change polarity of manual drawing
        super().produce_structures()

        # import daisy bottom cell
        daisy_cell = Element.create_cell_from_shape(self.layout, cell_name)

        # copy features for both faces
        for face_id in [0, 1]:
            box = pya.DPolygon(self.get_box(face_id))

            # create box
            x_min = min(self.box.p1.x, self.box.p2.x)
            x_max = max(self.box.p1.x, self.box.p2.x)
            y_min = min(self.box.p1.y, self.box.p2.y)
            y_max = max(self.box.p1.y, self.box.p2.y)

            # shorthand notation
            origin_offset_x = 1e3 * (x_max - x_min) / 2.
            origin_offset_y = 1e3 * (y_max - y_min) / 2.

            chip_region = pya.Region([box.to_itype(self.layout.dbu)])  # this is already the shape of the box

            # Using a static file, so use static layer indices
            daisy_shapes_base_metal_gap_wo_grid  = daisy_cell.shapes(self.layout.layer(11 + face_id * 30, 1))
            daisy_shapes_underbump_metallization = daisy_cell.shapes(self.layout.layer(32 + face_id * 30, 4))
            daisy_shapes_indium_bump             = daisy_cell.shapes(self.layout.layer(33 + face_id * 30, 4))

            protection = pya.Region(
                self.cell.begin_shapes_rec(self.get_layer("ground_grid_avoidance", face_id))).merged()
            self.cell.shapes(self.get_layer("ground_grid_avoidance", face_id)).insert(chip_region)

            # extract the bottom Nb layer
            pattern = pya.Region(daisy_shapes_base_metal_gap_wo_grid).moved(
                origin_offset_x, origin_offset_y)
            difference = chip_region - pattern - protection

            # copy design cell layers manually to DaisyWoven cell
            self.cell.shapes(self.get_layer("base_metal_gap_wo_grid", face_id)).insert(difference)
            self.cell.shapes(self.get_layer("underbump_metallization", face_id)).insert(
                pya.Region(daisy_shapes_underbump_metallization).moved(
                    origin_offset_x, origin_offset_y))
            self.cell.shapes(self.get_layer("indium_bump", face_id)).insert(
                pya.Region(daisy_shapes_indium_bump).moved(
                    origin_offset_x, origin_offset_y))
