import pya
import math
from kqcircuit.pcells.kqcircuit_pcell import KQCirvuitPCell
from kqcircuit.defaults import default_layers

import sys
from importlib import reload
reload(sys.modules[KQCirvuitPCell.__module__])
    
class AirBridgeDC(KQCirvuitPCell):
  """
  The PCell declaration for an arbitrary waveguide
  """
  version = 2
  
  def __init__(self):
    super().__init__()
    self.param("lo2", self.TypeLayer, "AB bottom layer", 
      default = default_layers["Optical lit. 2"])      
    self.param("lo3", self.TypeLayer, "AB top layer", 
      default = default_layers["Optical lit. 3"])
    self.param("n", self.TypeInt, "Number of AB", default = 10)
    self.param("w", self.TypeDouble, "Pad width (um)", default = 30)
    self.param("h", self.TypeDouble, "Pad length (um)", default = 10)
    self.param("l", self.TypeDouble, "Bridge length (from pad to pad) (um)", default = 40)
    self.param("b", self.TypeDouble, "Bridge width (um)", default = 8)
    self.param("e", self.TypeDouble, "Bottom pad extra (um)", default = 1)

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return("AB_DC_Test")
  
  def coerce_parameters_impl(self):
    None

  def can_create_from_shape_impl(self):
    return self.shape.is_box()
  
  def parameters_from_shape_impl(self):
    None
    
  def transformation_from_shape_impl(self):
    return pya.Trans()                   

    
  def produce_impl(self):     
    cell_ab = self.layout.create_cell("Airbridge", "KQCircuit", {
                          "Pad width (um)": self.w,
                          "Pad length (um)": self.h,
                          "Bridge length (from pad to pad) (um)": self.l,
                          "Bridge width (um)": self.b,
                          "Bottom pad extra (um)": self.e
                          })
    
    m = 2 # margin for bottom Nb layer
    step = self.l + 2*self.h + 2*self.e + m
                        
    island = pya.DPolygon([
      pya.DPoint(-self.w-m, -self.h-2*m),
      pya.DPoint( self.w+m, -self.h-2*m),
      pya.DPoint( self.w+m, 0),
      pya.DPoint(-self.w-m, 0),
    ])
    lu = self.layout.layer(default_layers["Unetch 1"])
    for i in range(int(self.n)):                  
      self.cell.shapes(lu).insert(pya.DTrans(  2, False, pya.DVector(0,(i-1)*step))*island)  
      self.cell.shapes(lu).insert(pya.DTrans(  0, False, pya.DVector(0,i*step))*island)  
      self.cell.insert(pya.DCellInstArray(cell_ab.cell_index(),pya.DTrans(0, False, pya.DVector(0,(i-0.5)*step)))) 