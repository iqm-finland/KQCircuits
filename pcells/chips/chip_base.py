import pya
import math
from kqcircuit.pcells.kqcircuit_pcell import KQCirvuitPCell

def border_points(x_min,x_max,y_min,y_max,w):
  points = [
    pya.DPoint(x_min, y_min),
    pya.DPoint(x_max, y_min),
    pya.DPoint(x_max, y_max),
    pya.DPoint(x_min, y_max),
    pya.DPoint(x_min, y_min),
        
    pya.DPoint(x_min+w, y_min+w),
    pya.DPoint(x_min+w, y_max-w),
    pya.DPoint(x_max-w, y_max-w),
    pya.DPoint(x_max-w, y_min+w),      
    pya.DPoint(x_min+w, y_min+w),
  ]
  return points
    
class ChipBase(KQCirvuitPCell):
  """
  The PCell declaration for an arbitrary waveguide
  """
  version = 2
  
  def __init__(self):
    super().__init__()
    self.param("box", self.TypeShape, "Border", default = pya.DBox(pya.DPoint(0,0),pya.DPoint(10000,10000)))
    self.param("dice_width", self.TypeDouble, "Dicing width (um)", default = 100)
    self.param("name_mask", self.TypeString, "Name of the mask", default = "M99")
    self.param("name_chip", self.TypeString, "Name of the chip", default = "CTest")
    self.param("name_copy", self.TypeString, "Name of the copy", default = "AA")
    self.text_margin = 100

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
  
  def produce_launcher(self, pos, direction, name=""):
    subcell = self.layout.create_cell("Launcher", "KQCircuit", 
                                    {"name": name})
    if isinstance(direction, str):
      direction = {"E": 0, "W": 180, "S": -90, "N": 90}[direction]
    print("Launcher:",direction,pos)
    transf = pya.DCplxTrans(1, direction, False, pos)    
    self.cell.insert(pya.DCellInstArray(subcell.cell_index(),transf)) 
    
  def produce_label(self, label, location, origin):  
    # text cell
    subcell = self.layout.create_cell("TEXT", "Basic", {
      "layer": self.lo, 
      "text": label,
      "mag": 500.0
    })
    
    # relative placement with margin
    margin = (self.dice_width + self.text_margin)/self.layout.dbu
    trans = pya.DTrans(location + {
        "bottomleft": pya.Vector(
          subcell.bbox().p1.x-margin, 
          subcell.bbox().p1.y-margin),      
        "topleft": pya.Vector(
          subcell.bbox().p1.x-margin, 
          subcell.bbox().p2.y+margin),
        "topright": pya.Vector(
          subcell.bbox().p2.x+margin, 
          subcell.bbox().p2.y+margin),
        "bottomright": pya.Vector(
          subcell.bbox().p2.x+margin, 
          subcell.bbox().p1.y-margin),
      }[origin]*self.layout.dbu*(-1))
    self.cell.insert(pya.DCellInstArray(subcell.cell_index(), trans))
    
    # protection layer with margin
    protection = pya.DBox(pya.Point(
          subcell.bbox().p1.x-margin, 
          subcell.bbox().p1.y-margin)*self.layout.dbu,
          pya.Point(
          subcell.bbox().p2.x+margin, 
          subcell.bbox().p2.y+margin)*self.layout.dbu
        )
    self.cell.shapes(self.layout.layer(self.lp)).insert(
      trans.trans(protection))
    
  def produce_dicing_edge(self):
    x_min = min(self.box.p1.x, self.box.p2.x)
    x_min = min(self.box.p1.x, self.box.p2.x)
    x_max = max(self.box.p1.x, self.box.p2.x)
    y_min = min(self.box.p1.y, self.box.p2.y)
    y_max = max(self.box.p1.y, self.box.p2.y)    
    
    shape = pya.DPolygon(border_points(
                      x_min,x_max,
                      y_min,y_max,
                      self.dice_width))                      
    self.cell.shapes(self.layout.layer(self.lo)).insert(shape)
    
    protection = pya.DPolygon(border_points(
                      x_min,x_max,
                      y_min,y_max,
                      self.dice_width+self.margin))   
    self.cell.shapes(self.layout.layer(self.lp)).insert(protection)                   

  def produce_impl(self): 
    self.produce_dicing_edge()    
    
    x_min = min(self.box.p1.x, self.box.p2.x)
    x_min = min(self.box.p1.x, self.box.p2.x)
    x_max = max(self.box.p1.x, self.box.p2.x)
    y_min = min(self.box.p1.y, self.box.p2.y)
    y_max = max(self.box.p1.y, self.box.p2.y)    
    
    self.produce_label(self.name_mask, 
                      pya.DPoint(x_min, y_max),"topleft")
    self.produce_label(self.name_chip, 
                      pya.DPoint(x_max, y_max),"topright")
    self.produce_label(self.name_copy, 
                      pya.DPoint(x_max, y_min),"bottomright")                      
    self.produce_label("AALTO", 
                      pya.DPoint(x_min, y_min),"bottomleft")
    