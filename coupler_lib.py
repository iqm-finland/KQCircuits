import pya

def produce_library_capacitor(layout, fingers, length, coupler_type = "square"):
  # Capacitor
  if (coupler_type=="plate"):    
    cap = layout.create_cell("FingerCapS", "KQCircuit", {
      "finger_number": fingers,
      "finger_length": 0,
      "finger_gap_end": length,
      "finger_gap_side": 0,
      "finger_width": 10,
      "ground_padding": 10,
#        "corner_r": 0
    })    
  elif (coupler_type=="square"):
    cap = layout.create_cell("FingerCapS", "KQCircuit", {
      "finger_number": fingers,
      "finger_length": length,
      "finger_gap_end": 5,
      "finger_gap_side": 5,
      "finger_width": 15,
      "ground_padding": 10
    })
  else:
    cap = layout.create_cell("FingerCapT", "KQCircuit", {
      "finger_number": fingers,
      "finger_length": length,
      "finger_gap": 5,
      "finger_width": 15,
      "ground_padding": 10,
      "taper_length": (fingers*20-5)/2. # 45 degree taper
    })
  return cap