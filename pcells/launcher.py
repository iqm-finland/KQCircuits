import pya
import math
from kqcircuit.pcells.kqcircuit_pcell import KQCirvuitPCell

class Launcher(KQCirvuitPCell):
  """
  The PCell declaration for an arbitrary waveguide
  """

  def __init__(self):
    super().__init__()
    self.param("s", self.TypeDouble, "Pad width (um)", default = 500)
    self.param("l", self.TypeDouble, "Tapering length (um)", default = 500)
    self.param("name", self.TypeString, "Name shown on annotation layer", default = "")

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "Launcher(%s)".format(self.name)
      
  def coerce_parameters_impl(self):
    None

  def can_create_from_shape_impl(self):
    return False
  
  def parameters_from_shape_impl(self):
    None
    
  def transformation_from_shape_impl(self):
    return pya.Trans()    
  
  def produce_impl(self):
    # optical layer

    # keep the a/b ratio the same, but scale up a and b          
    f = self.s/float(self.a)
    
    # shape for the inner conductor    
    pts = [
      pya.DPoint(0, self.a/2+0),
      pya.DPoint(self.l, f*(self.a/2)),
      pya.DPoint(self.l+self.s, f*(self.a/2)),
      pya.DPoint(self.l+self.s, -f*(self.a/2)),      
      pya.DPoint(self.l, -f*(self.a/2)),
      pya.DPoint(0, -self.a/2+0)
    ]

    shifts = [
      pya.DVector(0, self.b),
      pya.DVector(0, self.b*f),
      pya.DVector(self.b*f, self.b*f),
      pya.DVector(self.b*f, -self.b*f),
      pya.DVector(0, -self.b*f),
      pya.DVector(0, -self.b),
    ]  
    pts2 = [p+s for p,s in zip(pts,shifts)]
    pts.reverse()    
    shape = pya.DPolygon(pts+pts2)    
    self.cell.shapes(self.layout.layer(self.lo)).insert(shape)   

    # protection layer
    shifts = [
      pya.DVector(0, self.margin),
      pya.DVector(0, self.margin),
      pya.DVector(self.margin, self.margin),
      pya.DVector(self.margin, -self.margin),
      pya.DVector(0, -self.margin),
      pya.DVector(0, -self.margin),
    ]    
    pts2 = [p+s for p,s in zip(pts2,shifts)]    
    shape = pya.DPolygon(pts2)    
    self.cell.shapes(self.layout.layer(self.lp)).insert(shape)   
    
    # annotation text
    if self.name:
      label = pya.DText(self.name, 1.5*self.l, 0)
      self.cell.shapes(self.layout.layer(self.la)).insert(label)
