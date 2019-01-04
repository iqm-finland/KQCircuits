import pya
from kqcircuit.defaults import default_layers

class KQCirvuitPCell(pya.PCellDeclarationHelper):
  def __init__(self):
    # Important: initialize the super class
    super().__init__()
    print("Calling")
    # declare the parameters
    self.param("lo", self.TypeLayer, "Layer optical", default = default_layers["Optical lit. 1"])
    self.param("lp", self.TypeLayer, "Layer protection", default = default_layers["Grid avoidance"])
    self.param("la", self.TypeLayer, "Layer annotation", default = default_layers["Annotations"])

    self.param("a", self.TypeDouble, "Width of center conductor (um)", default = 6)
    self.param("b", self.TypeDouble, "Width of gap (um)", default = 10)
    self.param("n", self.TypeInt, "Number of points on turns", default = 64)   
    self.param("ru", self.TypeDouble, "Turn radius (um)", default = 20)
    
    self.refpoints = {"base":pya.DVector(0,0)}
