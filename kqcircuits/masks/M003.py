from autologging import logged, traced
import glob
import os.path

from kqcircuits.defaults import default_layers
from kqcircuits.chips.quality_factor import QualityFactor
from kqcircuits.masks.mask import Mask


@logged
@traced
class M003(Mask):
    """M003 mask.

    Spiral resonators and Xmons

    """

    def __init__(self, layout, version=1, with_grid=False):
        super().__init__(layout, "M003", version, with_grid)

    def build(self):

        self.mask_layout = [
            ["--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "32", "32", "32", "41", "41", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "31", "31", "32", "32", "32", "41", "41", "41", "41", "--", "--", "--"],
            ["--", "--", "R7", "31", "31", "31", "32", "32", "41", "41", "41", "41", "42", "--", "--"],
            ["--", "--", "R7", "31", "31", "31", "32", "32", "41", "41", "42", "42", "42", "--", "--"],
            ["--", "R7", "R7", "31", "31", "31", "32", "32", "41", "41", "42", "42", "42", "42", "--"],
            ["--", "R7", "R7", "31", "31", "31", "32", "32", "41", "41", "42", "42", "42", "42", "--"],
            ["--", "R7", "R7", "31", "31", "31", "32", "32", "41", "41", "42", "42", "42", "42", "--"],
            ["--", "R7", "R7", "31", "31", "31", "32", "32", "41", "41", "42", "42", "42", "42", "--"],
            ["--", "R7", "R7", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "R6", "--"],
            ["--", "--", "R7", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "--", "--"],
            ["--", "--", "R7", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "--", "--"],
            ["--", "--", "--", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "QD", "QD", "QD", "QD", "QD", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--"],
        ]
        # "R4","R7","R8","S1","ST","QDG"]

        mask_parameters_for_chip = {
            "name_mask": self.name,
            "name_copy": None,
            "with_grid": self.with_grid,
        }

        # For quality factor test as on M001
        parameters_qd = {
            "res_lengths": [4649.6, 4743.3, 4869.9, 4962.9, 5050.7, 5138.7, 5139., 5257., 5397.4, 5516.8, 5626.6, 5736.2,
                            5742.9, 5888.7, 6058.3, 6202.5, 6350., 6489.4],
            "type_coupler": ["square", "square", "square", "plate", "plate", "plate", "square", "square", "square", "plate",
                             "plate", "plate", "square", "square", "square", "square", "plate", "plate"],
            "l_fingers": [19.9, 54.6, 6.7, 9.7, 22.8, 30.5, 26.1, 14.2, 18.2, 10.9, 19.8, 26.4, 34.2, 19.9, 25.3, 8., 15.8,
                          22.2],
            "n_fingers": [4, 2, 2, 4, 4, 4, 4, 4, 2, 4, 4, 4, 4, 4, 2, 2, 4, 4],
            "res_beg": ["galvanic"]*18
        }

        # Load new cells from the files
        imported = False
        path_pixels_input = "/u/57/heinsoj1/unix/qcd/Johannes/Masks/M003/Pixels input"
        if not 'imported' in globals() or not imported:
            for file_name in glob.glob(os.path.join(path_pixels_input, "*.gds")):
                print("Loading:", file_name)
                self.layout.read(file_name)
            imported = True

        # Register the cells used on the mask
        self.mask_map_legend = {
            "QD": QualityFactor.create_cell(self.layout, {
                **parameters_qd,
                **mask_parameters_for_chip,
                "name_chip": "QDG",
                "n_ab": 18 * [0],
                "res_term": 18 * ["galvanic"]
            }),
            "R7": self.layout.create_cell("R07"),
            "X3": self.layout.create_cell("X03"),
            "X4": self.layout.create_cell("X04"),
            "31": self.layout.create_cell("X031"),
            "32": self.layout.create_cell("X032"),
            "41": self.layout.create_cell("X041"),
            "42": self.layout.create_cell("X042")
        }
