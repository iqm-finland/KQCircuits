import pya
import math
from kqcircuit.pcells.kqcircuit_pcell import KQCirvuitPCell

class Swissmon(KQCirvuitPCell):
  """
  The PCell declaration for a finger capacitor
  """

  def __init__(self):
    super().__init__()
    self.param("len_direct", self.TypeDouble, "Length between the ports (um)", default = 400)
    self.param("len_finger", self.TypeDouble, "Length of the fingers (um)", default = 50)
    self.param("fingers", self.TypeInt, "Number of fingers (at least 2)", default = 3)
    self.param("arm_length", self.TypeDouble, "Arm length (um)", default = 300./2)
    self.param("arm_width", self.TypeDouble, "Arm width (um)", default = 24)
    self.param("gap_width", self.TypeDouble, "Gap width (um)", default = 24)
    self.param("corner_r", self.TypeDouble, "Corner radius (um)", default = 5)

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "swissmon()".format()
      
  def coerce_parameters_impl(self):
    None

  def can_create_from_shape_impl(self):
    return self.shape.is_path()
  
  def parameters_from_shape_impl(self):
    None
    
  def transformation_from_shape_impl(self):
    return pya.Trans()    
  
  def produce_impl(self):
    w=self.arm_width/2
    l=self.arm_length
    cross_points = [
      pya.DPoint(w, w),
      pya.DPoint(l, w),
      pya.DPoint(l, -w),
      pya.DPoint(w, -w),
      pya.DPoint(w, -l),
      pya.DPoint(-w, -l),
      pya.DPoint(-w, -w),
      pya.DPoint(-l, -w),
      pya.DPoint(-l, w),
      pya.DPoint(-w, w),
      pya.DPoint(-w, l),
      pya.DPoint(w, l),
    ] 
    
    s=self.gap_width
    f = float(self.gap_width+self.arm_width/2)/self.arm_width/2
    cross = pya.DPolygon([
              p+pya.DVector(math.copysign(s, p.x),math.copysign(s, p.y)) for p in cross_points
              ])    
    cross.insert_hole(cross_points)
    #cross_rounded = cross.round_corners(self.corner_r/self.layout.dbu, self.corner_r/self.layout.dbu, self.n)
    cross_rounded = cross.round_corners(self.corner_r-self.gap_width/2, self.corner_r+self.gap_width/2, self.n)
    self.cell.shapes(self.layout.layer(self.lo)).insert(cross_rounded)
    self.cell.shapes(self.layout.layer(self.la)).insert(cross)
    
    cross_protection = pya.DPolygon([
                        p+pya.DVector(math.copysign(s+self.margin, p.x),math.copysign(s+self.margin, p.y)) for p in cross_points
                        ])    
    self.cell.shapes(self.layout.layer(self.lp)).insert(cross_protection)
