import pya
import math
from kqcircuit.pcells.kqcircuit_pcell import KQCirvuitPCell

    
class ChipFrame(KQCirvuitPCell):
  """
  The PCell declaration for an arbitrary waveguide
  """

  def __init__(self):
    super().__init__()
    self.param("box", self.TypeShape, "Border", default = pya.DBox(pya.DPoint(0,0),pya.DPoint(10000,10000)))
    self.param("dice_width", self.TypeDouble, "Dicing width (um)", default = 100)

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return("Chip(w=" + ('%.1f' % self.box.width()) + ",h=" + ('%.1f' % self.box.height()) + ")")
  
  def coerce_parameters_impl(self):
    None

  def can_create_from_shape_impl(self):
    return self.shape.is_box()
  
  def parameters_from_shape_impl(self):
    self.box.p1 = self.shape.p1
    self.box.p2 = self.shape.p2
    
  def transformation_from_shape_impl(self):
    return pya.Trans()    
  
  def produce_impl(self): 
    x_min = min(self.box.p1.x, self.box.p2.x)
    x_max = max(self.box.p1.x, self.box.p2.x)
    y_min = min(self.box.p1.y, self.box.p2.y)
    y_max = max(self.box.p1.y, self.box.p2.y)
  
    points = [
      pya.DPoint(x_min, y_min),
      pya.DPoint(x_max, y_min),
      pya.DPoint(x_max, y_max),
      pya.DPoint(x_min, y_max),
      pya.DPoint(x_min, y_min),
          
      pya.DPoint(x_min+self.dice_width, y_min+self.dice_width),
      pya.DPoint(x_min+self.dice_width, y_max-self.dice_width),
      pya.DPoint(x_max-self.dice_width, y_max-self.dice_width),
      pya.DPoint(x_max-self.dice_width, y_min+self.dice_width),      
      pya.DPoint(x_min+self.dice_width, y_min+self.dice_width),
    ]
         
    shape = pya.DPolygon(points)
    self.cell.shapes(self.layout.layer(self.lo)).insert(shape)