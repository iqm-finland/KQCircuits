import sys
from importlib import reload
from autologging import logged, traced

from kqcircuits.pya_resolver import pya
from kqcircuits.chips.multi_face.multi_face import MultiFace
from kqcircuits.elements.element import Element

reload(sys.modules[Element.__module__])

@traced
class DaisyWoven(MultiFace):
    """Base PCell declaration for a Daisy Woven chip.

    Includes texts in pixel corners, dicing edge, launchers and manually-drawn daisy pattern.
    No input parameters on this class.
    """

    PARAMETERS_SCHEMA ={
        "name_chip": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Name of the chip",
            "default": "DC"}
        }

    def produce_impl(self):
        self._produce_daisy_face("Daisy_woven")
        super().produce_impl()

    def _produce_daisy_face(self, cell_name):
        # first create chip frame to change polarity of manual drawing
        super().produce_structures()

        # import daisy bottom cell
        daisy_cell = Element.create_cell_from_shape(self.layout, cell_name)

        # copy features for both faces
        for face_id in [0, 1]:
            if face_id == 0:
                box = pya.DPolygon(self.box)  # this is already the shape of the box
            else:
                box = pya.DPolygon(self.face1_box)  # this is already the shape of the box

            # create box
            x_min = min(self.box.p1.x, self.box.p2.x)
            x_max = max(self.box.p1.x, self.box.p2.x)
            y_min = min(self.box.p1.y, self.box.p2.y)
            y_max = max(self.box.p1.y, self.box.p2.y)

            # shorthand notation
            origin_offset_x = 1e3 * (x_max - x_min) / 2.
            origin_offset_y = 1e3 * (y_max - y_min) / 2.

            chip_region = pya.Region([box.to_itype(self.layout.dbu)])  # this is already the shape of the box

            protection = pya.Region(
                self.cell.begin_shapes_rec(self.get_layer("ground grid avoidance", face_id))).merged()
            self.cell.shapes(self.get_layer("ground grid avoidance", face_id)).insert(chip_region)

            # extract the bottom Nb layer
            pattern = pya.Region(daisy_cell.shapes(self.get_layer("base metal gap wo grid", face_id))).moved(
                origin_offset_x, origin_offset_y)
            difference = chip_region - pattern - protection

            # copy design cell layers manually to DaisyWoven cell
            self.cell.shapes(self.get_layer("base metal gap wo grid", face_id)).insert(difference)
            self.cell.shapes(self.get_layer("underbump metallization", face_id)).insert(
                pya.Region(daisy_cell.shapes(self.get_layer("underbump metallization", face_id))).moved(
                    origin_offset_x, origin_offset_y))
            self.cell.shapes(self.get_layer("indium bump", face_id)).insert(
                pya.Region(daisy_cell.shapes(self.get_layer("indium bump", face_id))).moved(
                    origin_offset_x, origin_offset_y))
