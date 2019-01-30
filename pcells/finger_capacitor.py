import pya
import math
from kqcircuit.pcells.kqcircuit_pcell import KQCirvuitPCell

class FingerCapacitor(KQCirvuitPCell):
  """
  The PCell declaration for a finger capacitor
  """

  def __init__(self):
    super().__init__()
    self.param("finger_number", self.TypeInt, "Number of fingers", default = 5)
    self.param("finger_width", self.TypeDouble, "Width of a finger (um)", default = 5)
    self.param("finger_gap", self.TypeDouble, "Gap between the fingers (um)", default = 3)
    self.param("finger_length", self.TypeDouble, "Length of the fingers (um)", default = 20)
    self.param("taper_length", self.TypeDouble, "Length of the taper (um)", default = 60)
    self.param("corner_r", self.TypeDouble, "Corner radius (um)", default = 2)

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "fingercap(l={},n={})".format(self.finger_number, self.finger_length )
      
  def coerce_parameters_impl(self):
    None

  def can_create_from_shape_impl(self):
    return self.shape.is_path()
  
  def parameters_from_shape_impl(self):
    None
    
  def transformation_from_shape_impl(self):
    return pya.Trans()    
  
  def produce_impl(self):
    # shorthand
    n = self.finger_number
    w = self.finger_width
    l = self.finger_length
    g = self.finger_gap
    t = self.taper_length
    W = float(n)*(w+g)-g # total width
    a = self.a
    b = self.b
    
    region_ground = pya.Region([pya.DPolygon([    
      pya.DPoint( (l+g)/2, W*(b/a)+W/2),
      pya.DPoint( (l+g)/2+t, b+a/2),
      pya.DPoint( (l+g)/2+t,-b-a/2),
      pya.DPoint( (l+g)/2,-W*(b/a)-W/2),
      pya.DPoint(-(l+g)/2,-W*(b/a)-W/2),
      pya.DPoint(-(l+g)/2-t,-b-a/2),
      pya.DPoint(-(l+g)/2-t, b+a/2),   
      pya.DPoint(-(l+g)/2, W*(b/a)+W/2),      
    
    ]).to_itype(self.layout.dbu)])
        
    region_taper_right = pya.Region([pya.DPolygon([    
      pya.DPoint( (l+g)/2, W/2),
      pya.DPoint( (l+g)/2+t, a/2),
      pya.DPoint( (l+g)/2+t,-a/2),
      pya.DPoint( (l+g)/2,-W/2)  
    ]).to_itype(self.layout.dbu)])
    region_taper_left = region_taper_right.transformed(pya.Trans().M90)
    
    polys_fingers = []
    poly_finger = pya.DPolygon([
        pya.DPoint(l/2, w),
        pya.DPoint(l/2, 0),
        pya.DPoint(-l/2, 0),
        pya.DPoint(-l/2, w)
      ])
    for i in range(0,n):
      trans = pya.DTrans(pya.DVector(g/2,i*(g+w)-W/2)) if i%2 else  pya.DTrans(pya.DVector(-g/2,i*(g+w)-W/2))
      polys_fingers.append(trans*poly_finger)
    
    region_fingers = pya.Region([
      poly.to_itype(self.layout.dbu) for poly in polys_fingers
    ])
    region_etch = region_taper_left + region_taper_right + region_fingers
    region_etch.round_corners(self.corner_r/self.layout.dbu, self.corner_r/self.layout.dbu, self.n)
    
    
    region_taper_right_small = pya.Region([pya.DPolygon([    
      pya.DPoint( (l+g)/2+self.corner_r, (W/2-a/2)*(t-2*self.corner_r)/t+a/2),
      pya.DPoint( (l+g)/2+t, a/2),
      pya.DPoint( (l+g)/2+t,-a/2),
      pya.DPoint( (l+g)/2+self.corner_r,-(W/2-a/2)*(t-2*self.corner_r)/t-a/2)  
    ]).to_itype(self.layout.dbu)])
    region_taper_left_small = region_taper_right_small.transformed(pya.Trans().M90)    
    
    region = (region_ground-region_etch)-region_taper_right_small-region_taper_left_small
    
    self.cell.shapes(self.layout.layer(self.lo)).insert(region)
    
    # protection
    region_protection = region_ground.size(0, self.margin/self.layout.dbu, 2)
    self.cell.shapes(self.layout.layer(self.lp)).insert(region_protection)
    
    # ports
    port_ref = pya.DPoint(-(l+g)/2-t, 0)
    self.refpoints["port_a"] = port_ref
    port_ref = pya.DPoint((l+g)/2+t, 0)
    self.refpoints["port_b"] = port_ref
    
    
    # adds annotation based on refpoints calculated above
    super().produce_impl()
    