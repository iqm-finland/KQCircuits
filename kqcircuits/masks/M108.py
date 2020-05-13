from autologging import logged, traced

from kqcircuits.chips.airbridge_crossings import AirbridgeCrossings
from kqcircuits.chips.quality_factor import QualityFactor
from kqcircuits.masks.mask import Mask


@logged
@traced
class M108(Mask):
    """M108 mask.

    Q and AB tests.

    """

    def __init__(self, layout, version=1, with_grid=False):
        super().__init__(layout, "M108", version, with_grid)

    def build(self):

        box_map = {"A": [
            ["AB1", "AB2", "QHG"],
            ["QDA", "QDC", "QDG"],
            ["QDA", "QDC", "QDD"],
        ]}

        mask_map = [
            ["A", "A", "A", "A", "A"],
            ["A", "A", "A", "A", "A"],
            ["A", "A", "A", "A", "A"],
            ["A", "A", "A", "A", "A"],
            ["A", "A", "A", "A", "A"],
        ]

        self.mask_layout = Mask.mask_layout_from_box_map(box_map, mask_map)

        mask_parameters_for_chip = {
            "name_mask": self.name,
            "name_copy": None,
            "with_grid": self.with_grid,
        }

        parameters_qd = {
            "res_lengths": [4649.6, 4743.3, 4869.9, 4962.9, 5050.7, 5138.7, 5139., 5257., 5397.4, 5516.8, 5626.6, 5736.2,
                            5742.9, 5888.7, 6058.3, 6202.5, 6350., 6489.4],
            "type_coupler": ["square", "square", "square", "plate", "plate", "plate", "square", "square", "square", "plate",
                             "plate", "plate", "square", "square", "square", "square", "plate", "plate"],
            "l_fingers": [19.9, 54.6, 6.7, 9.7, 22.8, 30.5, 26.1, 14.2, 18.2, 10.9, 19.8, 26.4, 34.2, 19.9, 25.3, 8., 15.8,
                          22.2],
            "n_fingers": [4, 2, 2, 4, 4, 4, 4, 4, 2, 4, 4, 4, 4, 4, 2, 2, 4, 4]
        }

        parameters_qh = {
            "res_lengths": [4727.6, 4804.7, 4884.3, 4966.4, 5051.2, 5139.0, 5229.2, 5323.6, 5421.4, 5522.6, 5627.6,
                            5736.5,
                            5848.9, 5967.2, 6090.1, 6217.9, 6351.0, 6490.0],
            "type_coupler": ["plate", "plate", "plate", "plate", "plate", "plate", "plate", "plate", "plate", "plate",
                             "plate", "plate", "plate", "plate", "plate", "plate", "plate", "plate"],
            "l_fingers": [25.0, 32.7, 54.3, 64.7, 79.9, 92.7, 21.7, 29.2, 49.7, 59.7, 73.9, 86.0, 18.5, 25.0, 44.5,
                          53.9,
                          67.8, 78.9],
            "n_fingers": [4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]
        }

        self.mask_map_legend = {
            "AB1": AirbridgeCrossings.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "AB1",
                "crossings": 1,
                "b_number": 5,
            }),

            "AB2": AirbridgeCrossings.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "AB2",
                "crossings": 10,
                "b_number": 5,
            }),
            "QDG": QualityFactor.create_cell(self.layout, {
                **parameters_qd,
                **mask_parameters_for_chip,
                "name_chip": "QDG",
                "n_ab": 18 * [0],
                "res_term": 18 * ["galvanic"],
                "res_beg": 18 * ["galvanic"],
            }),
            "QDA": QualityFactor.create_cell(self.layout, {
                **mask_parameters_for_chip,
                **parameters_qd,
                "name_chip": "QDA",
                "n_ab": 18 * [0],
                "res_term": 18 * ["airbridge"],
                "res_beg": 18 * ["galvanic"],
            }),
            "QDC": QualityFactor.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "QDC",
                **parameters_qd,
                "n_ab": 18 * [5],
                "res_term": 18 * ["galvanic"],
                "res_beg": 18 * ["galvanic"],
            }),
            "QDD": QualityFactor.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "QDD",
                **parameters_qd,
                "n_ab": 18 * [15],
                "res_term": 18 * ["galvanic"],
                "res_beg": 18 * ["galvanic"],
            }),
            "QHG": QualityFactor.create_cell(self.layout, {
                **parameters_qh,
                **mask_parameters_for_chip,
                "name_chip": "QHG",
                "n_ab": 18 * [0],
                "res_term": 18 * ["galvanic"],
                "res_beg": 18 * ["galvanic"],
            }),
        }
