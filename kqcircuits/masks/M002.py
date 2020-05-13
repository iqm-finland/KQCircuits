from autologging import logged, traced
import glob
import os.path

from kqcircuits.defaults import default_layers
from kqcircuits.chips.shaping import Shaping
from kqcircuits.chips.quality_factor import QualityFactor
from kqcircuits.masks.mask import Mask


@logged
@traced
class M002(Mask):
    """M002 mask.

    Photon shaping and spiral resonators.

    """

    def __init__(self, layout, version=1, with_grid=False):
        super().__init__(layout, "M002", version, with_grid)

    def build(self):
        # 20*R4,
        # 15*R5,
        # 15*R6,
        # 20*R7,
        # 20*R8.
        # 4*QDG,
        # 20*S1,
        # 20*ST.

        # pixel_list = 10*["R4","R5","R6","R7","R8","S1","ST",
        # "R4","R5","R6","R7","R8","S1","ST",
        # "R4","R5","R6","R7","R8","S1","ST",
        # "R4","R7","R8","S1","ST","QDG"]

        self.mask_layout = [
            ["--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "R4", "R4", "R4", "R4", "R4", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "R7", "R7", "R4", "R4", "R4", "R4", "R4", "R8", "R8", "--", "--", "--"],
            ["--", "--", "R5", "R7", "R7", "R4", "R4", "R4", "R4", "R4", "R8", "R8", "R6", "--", "--"],
            ["--", "--", "R5", "R7", "R7", "R4", "R4", "R4", "R4", "R4", "R8", "R8", "R6", "--", "--"],
            ["--", "R5", "R5", "R7", "R7", "S1", "S1", "ST", "ST", "QD", "R8", "R8", "R6", "R6", "--"],
            ["--", "R5", "R5", "R7", "R7", "S1", "S1", "ST", "ST", "QD", "R8", "R8", "R6", "R6", "--"],
            ["--", "R5", "R5", "R7", "R7", "S1", "S1", "ST", "ST", "QD", "R7", "R8", "R6", "R6", "--"],
            ["--", "R5", "R5", "R7", "R7", "S1", "S1", "ST", "ST", "QD", "R8", "R8", "R6", "R6", "--"],
            ["--", "R5", "R5", "R7", "R7", "S1", "S1", "S1", "S1", "S1", "R8", "R8", "R6", "R6", "--"],
            ["--", "--", "R5", "R7", "R7", "ST", "ST", "ST", "S1", "S1", "R8", "R8", "R6", "--", "--"],
            ["--", "--", "R5", "R7", "R7", "ST", "ST", "ST", "S1", "S1", "R8", "R8", "R6", "--", "--"],
            ["--", "--", "--", "R7", "R7", "ST", "ST", "ST", "S1", "QD", "R8", "R8", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "ST", "ST", "ST", "S1", "QD", "--", "--", "--", "--", "--"],
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
        path_pixels_input = "/u/57/heinsoj1/unix/qcd/Johannes/Masks/M002/Pixels input"
        if not 'imported' in globals() or not imported:
            for file_name in glob.glob(os.path.join(path_pixels_input, "*.gds")):
                print("Loading:", file_name)
                self.layout.read(file_name)
            imported = True

        # Register the cells used on the mask
        self.mask_map_legend = {
            "S1": Shaping.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "S1",
                "tunable": False,
            }),
            "ST": Shaping.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "ST",
                "tunable": True,
            }),
            "QD": QualityFactor.create_cell(self.layout, {
                **parameters_qd,
                **mask_parameters_for_chip,
                "name_chip": "QDG",
                "n_ab": 18 * [0],
                "res_term": 18 * ["galvanic"]
            }),
            "R4": self.layout.create_cell("R04"),
            "R5": self.layout.create_cell("R05"),
            "R6": self.layout.create_cell("R06"),
            "R7": self.layout.create_cell("R07"),
            "R8": self.layout.create_cell("R08")
        }
