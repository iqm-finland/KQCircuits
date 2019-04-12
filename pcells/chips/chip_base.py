import pya
import math
from kqcircuit.pcells.kqcircuit_pcell import KQCirvuitPCell
from kqcircuit.defaults import default_layers
from kqcircuit.groundgrid import make_grid

import sys
from importlib import reload
reload(sys.modules[KQCirvuitPCell.__module__])


default_launchers_SMA8 = {
      "WS": (pya.DPoint(1800,2800),"W"),      
      "ES": (pya.DPoint(8200,2800),"E"),      
      "WN": (pya.DPoint(1800,7200),"W"),      
      "EN": (pya.DPoint(8200,7200),"E"),
      "SW": (pya.DPoint(2800,1800),"S"),      
      "NW": (pya.DPoint(2800,8200),"N"),      
      "SE": (pya.DPoint(7200,1800),"S"),      
      "NE": (pya.DPoint(7200,8200),"N")
    }
    
    
def produce_label(cell, label, location, origin, dice_width, margin, layer_optical, layer_protection):
    layout = cell.layout()
    dbu = layout.dbu    
    
    # text cell
    subcell = layout.create_cell("TEXT", "Basic", {
      "layer": layer_optical, 
      "text": label,
      "mag": 500.0
    })
    
    # relative placement with margin
    margin = margin / dbu
    dice_width = dice_width / dbu
    trans = pya.DTrans(location + {
        "bottomleft": pya.Vector(
          subcell.bbox().p1.x-margin-dice_width, 
          subcell.bbox().p1.y-margin-dice_width),      
        "topleft": pya.Vector(
          subcell.bbox().p1.x-margin-dice_width, 
          subcell.bbox().p2.y+margin+dice_width),
        "topright": pya.Vector(
          subcell.bbox().p2.x+margin+dice_width, 
          subcell.bbox().p2.y+margin+dice_width),
        "bottomright": pya.Vector(
          subcell.bbox().p2.x+margin+dice_width, 
          subcell.bbox().p1.y-margin-dice_width),
      }[origin]*dbu*(-1))
    cell.insert(pya.DCellInstArray(subcell.cell_index(), trans))
    
    # protection layer with margin
    protection = pya.DBox(pya.Point(
          subcell.bbox().p1.x-margin, 
          subcell.bbox().p1.y-margin)*dbu,
          pya.Point(
          subcell.bbox().p2.x+margin, 
          subcell.bbox().p2.y+margin)*dbu
        )
    cell.shapes(layout.layer(layer_protection)).insert(
      trans.trans(protection))
      
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
    self.param("with_grid", self.TypeBoolean, "Make ground plane grid", default = False)    
    self.param("lg", self.TypeLayer, "Layer ground plane grid", default = default_layers["Grid"])
    self.param("dice_width", self.TypeDouble, "Dicing width (um)", default = 100)
    self.param("name_mask", self.TypeString, "Name of the mask", default = "M99")
    self.param("name_chip", self.TypeString, "Name of the chip", default = "CTest")
    self.param("name_copy", self.TypeString, "Name of the copy", default = None) # Prevents Cell reuse on a mask
    self.param("text_margin", self.TypeDouble, "Margin for labels", default = 100, hidden = True)
    self.param("dice_grid_margin", self.TypeDouble, "Margin between dicing edge and ground grid", default = 100, hidden = True)

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return("{}".format(self.name_chip))
  
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
    transf = pya.DCplxTrans(1, direction, False, pos)    
    self.cell.insert(pya.DCellInstArray(subcell.cell_index(),transf)) 
  
  def produce_launchers_SMA8(self, enabled=["WS","WN","ES","EN","SW","SE","NW","NE"]):  
    launchers = default_launchers_SMA8
    for name in enabled:    
      self.produce_launcher(launchers[name][0], launchers[name][1], name)      
    return launchers
                
  def produce_label(self, label, location, origin):  
    produce_label(self.cell, label, location, origin, self.dice_width, self.text_margin, self.lo, self.lp)
    
  def produce_marker_sqr(self, trans):
    
    corner = pya.DPolygon([
      pya.DPoint(100,100),
      pya.DPoint( 10,100),
      pya.DPoint( 10, 80),
      pya.DPoint( 80, 80),
      pya.DPoint( 80, 10),
      pya.DPoint(100, 10),
    ])   
    
    sqr = pya.DBox(
      pya.DPoint( 10, 10),
      pya.DPoint(  2,  2),
    )
    
    lo = self.layout.layer(self.lo)
    lp = self.layout.layer(self.lp)
    
    # center boxes
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(1,  0, False, pya.DVector())*sqr))
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(1, 90, False, pya.DVector())*sqr))
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(1,180, False, pya.DVector())*sqr))
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(1,-90, False, pya.DVector())*sqr))
      
    # inner corners
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(1,  0, False, pya.DVector())*corner))
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(1, 90, False, pya.DVector())*corner))
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(1,180, False, pya.DVector())*corner))
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(1,-90, False, pya.DVector())*corner))
            
    # outer corners
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(2,  0, False, pya.DVector())*corner))
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(2, 90, False, pya.DVector())*corner))
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(2,180, False, pya.DVector())*corner))
    self.cell.shapes(lo).insert(
      trans*(pya.DCplxTrans(2,-90, False, pya.DVector())*corner))
    
    # protection for the box
    protection = pya.DBox(
                      pya.DPoint( 220, 220),
                      pya.DPoint(-220,-220)
                    )   
    self.cell.shapes(lp).insert(trans*protection)     
                      
    # marker diagonal    
    for i in range(5, 15):
      self.cell.shapes(lo).insert(
        trans*(pya.DCplxTrans(3,  0, False, pya.DVector(50*i-3*6, 50*i-3*6))*sqr))
      self.cell.shapes(lp).insert(
        trans*(pya.DCplxTrans(20,  0, False, pya.DVector(50*i-20*6, 50*i-20*6))*sqr))
    
    
    
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
                      self.dice_width+self.dice_grid_margin))   
    self.cell.shapes(self.layout.layer(self.lp)).insert(protection)                   

  def produce_impl(self): 
    self.produce_dicing_edge()    
    
    x_min = min(self.box.p1.x, self.box.p2.x)
    x_min = min(self.box.p1.x, self.box.p2.x)
    x_max = max(self.box.p1.x, self.box.p2.x)
    y_min = min(self.box.p1.y, self.box.p2.y)
    y_max = max(self.box.p1.y, self.box.p2.y)    
    
    ## Square markers
    self.produce_marker_sqr(pya.DTrans(x_min+1.5e3, y_min+1.5e3)*pya.DTrans.R180)
    self.produce_marker_sqr(pya.DTrans(x_max-1.5e3, y_min+1.5e3)*pya.DTrans.R270)
    self.produce_marker_sqr(pya.DTrans(x_min+1.5e3, y_max-1.5e3)*pya.DTrans.R90)
    self.produce_marker_sqr(pya.DTrans(x_max-1.5e3, y_max-1.5e3)*pya.DTrans.R0)
        
    ## Text in the corners        
    if self.name_mask:
      self.produce_label(self.name_mask, 
                      pya.DPoint(x_min, y_max), "topleft")
    if self.name_chip:
      self.produce_label(self.name_chip, 
                      pya.DPoint(x_max, y_max), "topright")
    if self.name_copy:
      self.produce_label(self.name_copy, 
                      pya.DPoint(x_max, y_min), "bottomright")
    if True:
      self.produce_label("A!", 
                      pya.DPoint(x_min, y_min), "bottomleft")
                      
    ## Ground grid
    if (self.with_grid):
      grid_area = self.cell.bbox()
      protection = pya.Region(self.cell.begin_shapes_rec(self.layout.layer(self.lp))).merged()    
      grid_mag_factor = 1
      region_ground_grid = make_grid(grid_area, protection, grid_step = 10*(1/self.layout.dbu)*grid_mag_factor, grid_size = 5*(1/self.layout.dbu)*grid_mag_factor )    
      self.cell.shapes(self.layout.layer(self.lg)).insert(region_ground_grid)
    