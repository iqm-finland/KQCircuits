import pya

# human readable dictionary
# layer name as key, tuple of layer and tech as value
default_layers_dict = {
  "Optical lit. 1": (2,0),
  "Grid": (4,0),
  "Unetch 1": (5,0),
  "Electron beam lit. 1": (7,0),
  "Electron beam lit. 2": (8,0),
  "Annotations": (9,0),   
  "Grid avoidance": (11,0),
}


# pya layer information
default_layers = {}
for name, index in default_layers_dict.items():
  default_layers[name] = pya.LayerInfo(index[0], index[1], name)
    
default_circuit_params = {
  "a": 10, # Width of center conductor (um)
  "b": 6, # Width of gap (um)
  "r": 20, # Number of points on turns
  "n": 64, # Turn radius (um)
}
