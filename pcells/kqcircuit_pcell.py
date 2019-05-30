import pya
from kqcircuit.defaults import default_layers
from kqcircuit.defaults import default_circuit_params

def coerce_parameters(inst):
  layout = inst.cell.library().layout()
  params = inst.pcell_parameters()
  declaration = inst.pcell_declaration()
  newparams = declaration.coerce_parameters(layout, params)
  inst.change_pcell_parameters(newparams)

def get_refpoints(layer, cell, cell_transf = pya.DTrans()):
  refpoints = {}
  shapes_iter = cell.begin_shapes_rec(layer)
  while not shapes_iter.at_end():
    shape = shapes_iter.shape()
    if shape.type() in (pya.Shape.TText, pya.Shape.TTextRef):
      refpoints[shape.text_string] = cell_transf*(shapes_iter.dtrans()*(pya.DPoint(shape.text_dpos)))
    shapes_iter.next()
    
  return refpoints
  
class KQCirvuitPCell(pya.PCellDeclarationHelper):
  def __init__(self):
    # Important: initialize the super class
    super().__init__()
    # declare the parameters
    self.param("lo", self.TypeLayer, "Layer optical", 
      default = default_layers["Optical lit. 1"])
    self.param("lp", self.TypeLayer, "Layer protection", 
      default = default_layers["Grid avoidance"])
    self.param("la", self.TypeLayer, "Layer annotation", 
      default = default_layers["Annotations"])

    self.param("a", self.TypeDouble, "Width of center conductor (um)", 
      default = default_circuit_params["a"])
    self.param("b", self.TypeDouble, "Width of gap (um)", 
      default = default_circuit_params["b"])
    self.param("n", self.TypeInt, "Number of points on turns", 
      default = default_circuit_params["n"])  
    self.param("r", self.TypeDouble, "Turn radius (um)", 
      default = default_circuit_params["r"])
    
    # margin for protection layer
    self.margin = 5 # this can have a different meaning for different cells
    
    self.refpoints = {"base":pya.DVector(0,0)}
  
  def create_sub_cell(self, pcell_name, parameters, library_name = "KQCircuit"):
    return self.layout.create_cell(pcell_name, library_name, {**self.cell.pcell_parameters_by_name(), **parameters})

    
  def produce_impl(self):
    # call the super.produce_impl once all the refpoints have been added to self.refpoints
    # add all ref points to user properties and draw to annotations    
    for name, refpoint in self.refpoints.items():
      self.cell.set_property(name, refpoint)      
      #self.cell.shapes(self.layout.layer(self.la)).insert(pya.DPath([pya.DPoint(0,0),pya.DPoint(0,0)+refpoint],1))
      text = pya.DText(name, refpoint.x, refpoint.y)
      self.cell.shapes(self.layout.layer(self.la)).insert(text)
    self.cell.refpoints = self.refpoints


  def get_refpoints(self, cell, cell_transf = pya.DTrans()):
    return get_refpoints(self.layout.layer(default_layers["Annotations"]), cell, cell_transf)