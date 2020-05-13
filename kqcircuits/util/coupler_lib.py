from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.finger_capacitor_taper import FingerCapacitorTaper


def produce_library_capacitor(layout, fingers, length, coupler_type="square"):
    # Capacitor
    if (coupler_type == "plate"):
        cap = FingerCapacitorSquare.create_cell(layout, {
            "finger_number": fingers,
            "finger_length": 0,
            "finger_gap_end": length,
            "finger_gap_side": 0,
            "finger_width": 10,
            "ground_padding": 10,
            #        "corner_r": 0
        })
    elif (coupler_type == "square"):
        cap = FingerCapacitorSquare.create_cell(layout, {
            "finger_number": fingers,
            "finger_length": length,
            "finger_gap_end": 5,
            "finger_gap_side": 5,
            "finger_width": 15,
            "ground_padding": 10
        })
    else:
        cap = FingerCapacitorTaper.create_cell(layout, {
            "finger_number": fingers,
            "finger_length": length,
            "finger_gap": 5,
            "finger_width": 15,
            "ground_padding": 10,
            "taper_length": (fingers * 20 - 5) / 2.  # 45 degree taper
        })
    return cap
