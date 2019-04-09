import pya
import math
from kqcircuit.pcells.kqcircuit_pcell import KQCirvuitPCell
from kqcircuit.defaults import default_layers

class AirBridge(KQCirvuitPCell):
  """
  The PCell declaration for an arbitrary waveguide
  """

  def __init__(self):
    super().__init__()
    self.param("lo2", self.TypeLayer, "AB bottom layer", 
      default = default_layers["Optical lit. 2"])      
    self.param("lo3", self.TypeLayer, "AB top layer", 
      default = default_layers["Optical lit. 3"])
    self.param("w", self.TypeDouble, "Pad width (um)", default = 30)
    self.param("h", self.TypeDouble, "Pad length (um)", default = 10)
    self.param("l", self.TypeDouble, "Bridge length (from pad to pad) (um)", default = 40)
    self.param("b", self.TypeDouble, "Bridge width (um)", default = 8)
    self.param("e", self.TypeDouble, "Bottom pad extra (um)", default = 1)

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "Airbridge(%s)".format(self.name)
      
  def coerce_parameters_impl(self):
    None

  def can_create_from_shape_impl(self):
    return False
  
  def parameters_from_shape_impl(self):
    None
    
  def transformation_from_shape_impl(self):
    return pya.Trans()    
  
  def produce_impl(self):
    # origin: geometric center
    # direction: from top to bottom

    # shorhand
    w = self.w
    h = self.h
    l = self.l
    b = self.b
    e = self.e

    # bottom layer top pad
    pts = [
      pya.DPoint(-w/2-e, h+l/2+e),
      pya.DPoint( w/2+e, h+l/2+e),
      pya.DPoint( w/2+e,   l/2-e),
      pya.DPoint(-w/2-e,   l/2-e),
    ]
    shape = pya.DPolygon(pts)    
    self.cell.shapes(self.layout.layer(self.lo2)).insert(shape)   
    
    # bottom layer bottom pad
    self.cell.shapes(self.layout.layer(self.lo2)).insert(pya.DTrans.M0*shape)   

    # protection layer
    self.cell.shapes(self.layout.layer(self.lp)).insert(shape)  
    self.cell.shapes(self.layout.layer(self.lp)).insert(pya.DTrans.M0*shape)   
        
    # top layer   
    pts = [
      pya.DPoint(-w/2, h+l/2),
      pya.DPoint( w/2, h+l/2),
      pya.DPoint( w/2,   l/2),
      pya.DPoint( b/2,   l/2),
      pya.DPoint( b/2,  -l/2),
      pya.DPoint( w/2,  -l/2),
      pya.DPoint( w/2,-h-l/2),
      pya.DPoint(-w/2,-h-l/2),
      pya.DPoint(-w/2,  -l/2),
      pya.DPoint(-b/2,  -l/2),
      pya.DPoint(-b/2,   l/2),
      pya.DPoint(-w/2,   l/2),
    ]
    shape = pya.DPolygon(pts)    
    self.cell.shapes(self.layout.layer(self.lo3)).insert(shape)   
    
