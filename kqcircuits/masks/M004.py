from autologging import logged, traced

from kqcircuits.defaults import default_layers
from kqcircuits.chips.airbridge_crossings import AirbridgeCrossings
from kqcircuits.chips.quality_factor import QualityFactor
from kqcircuits.masks.mask import Mask


@logged
@traced
class M004(Mask):
    """M004 mask.

    Q and AB tests

    """

    def __init__(self, layout, version=1, with_grid=False):
        super().__init__(layout, "M004", version, with_grid)

    def build(self):

        box_map = {"A": [
            ["AB1", "AB2", "QSG"],
            ["QSA", "QSC", "QDG"],
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
            "n_fingers": [4, 2, 2, 4, 4, 4, 4, 4, 2, 4, 4, 4, 4, 4, 2, 2, 4, 4],
            "res_beg": ["galvanic"]*18
        }

        parameters_qs = {
            "res_lengths": [4649.6, 4908.9, 5208.5, 5516.8, 5848.9, 6217.4],
            "type_coupler": ["square", "square", "square", "plate", "plate", "plate"],
            "l_fingers": [19.9, 7.3, 15.2, 10.9, 18.5, 23.6],
            "n_fingers": [4, 4, 2, 4, 4, 4],
            "res_beg": ["galvanic"]*6
        }

        self.mask_map_legend = {
            "AB1": AirbridgeCrossings.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "AB1",
                "crossings": 1
            }),
            "AB2": AirbridgeCrossings.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "AB2",
                "crossings": 10}),
            "QSG": QualityFactor.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "QSG",
                **parameters_qs,
                "n_ab": 6 * [0],
                "res_term": 6 * ["galvanic"]
            }),
            "QSA": QualityFactor.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "QSA",
                **parameters_qs,
                "n_ab": 6 * [0],
                "res_term": 6 * ["airbridge"]
            }),
            "QSC": QualityFactor.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "QSC",
                **parameters_qs,
                "n_ab": 6 * [5],
                "res_term": 6 * ["galvanic"]
            }),
            "QDG": QualityFactor.create_cell(self.layout, {
                **parameters_qd,
                **mask_parameters_for_chip,
                "name_chip": "QDG",
                "n_ab": 18 * [0],
                "res_term": 18 * ["galvanic"]
            }),
            "QDA": QualityFactor.create_cell(self.layout, {
                **mask_parameters_for_chip,
                **parameters_qd,
                "name_chip": "QDA",
                "n_ab": 18 * [0],
                "res_term": 18 * ["airbridge"]
            }),
            "QDC": QualityFactor.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "QDC",
                **parameters_qd,
                "n_ab": 18 * [5],
                "res_term": 18 * ["galvanic"]
            }),
            "QDD": QualityFactor.create_cell(self.layout, {
                **mask_parameters_for_chip,
                "name_chip": "QDD",
                **parameters_qd,
                "n_ab": 18 * [5],
                "res_term": 18 * ["galvanic"],
            }),
        }
