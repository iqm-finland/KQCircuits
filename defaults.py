import pya

# human readable dictionary
# layer name as key, tuple of layer and tech as value
default_layers_dict = {
  "Optical lit. 1": (2,0),
  "Grid": (3,0),
  "New guidelines": (4,0),
  "Grid avoidance": (5,0),
  "Electron beam lit. 1": (7,0),
  "Electron beam lit. 2": (8,0),
  "Annotations": (9,0),   

}

# pya layer information
default_layers = {}
for name, index in default_layers_dict.items():
  default_layers[name] = pya.LayerInfo(index[0], index[1], name)
  
print(default_layers)