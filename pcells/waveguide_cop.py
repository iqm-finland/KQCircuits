import pya
import math
from kqcircuit.pcells.kqcircuit_pcell import KQCirvuitPCell
from kqcircuit.defaults import default_circuit_params
from kqcircuit.pcells.kqcircuit_pcell import coerce_parameters

def up_mod(a, per):
  # Finds remainder in the same direction as periodicity
  if (a*per>0):
    return a % per
  else:
    return a-per*math.floor(a/per)    
    
def arc(R, start, stop, n):
  pts = []
  last = start
  
  alpha_rel = up_mod(stop-start, math.pi * 2) # from 0 to 2 pi
  alpha_step = 2*math.pi/n*(-1 if alpha_rel > math.pi else 1) # shorter dir  n_steps = math.floor((2*math.pi-alpha_rel)/abs(alpha_step) if alpha_rel > math.pi else alpha_rel/abs(alpha_step))
  n_steps = math.floor((2*math.pi-alpha_rel)/abs(alpha_step) if alpha_rel > math.pi else alpha_rel/abs(alpha_step))
  
  alpha = start
    
  for i in range(0,n_steps+1):
    pts.append(pya.DPoint(R * math.cos(alpha), R * math.sin(alpha)))    
    alpha += alpha_step
    last = alpha
  
  if last != stop:
    alpha = stop
    pts.append(pya.DPoint(R * math.cos(alpha), R * math.sin(alpha)))
  
  return pts
     
class WaveguideCopStreight(KQCirvuitPCell):
  """
  The PCell declaration of a streight segment of a coplanar waveguide
  """

  def __init__(self):
    super().__init__()
    self.param("l", self.TypeDouble, "Length", default = math.pi)
    
  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "WaveguideCopStreight(a=" + ('%.1f' % self.a) + ",b=" + ('%.1f' % self.b) + ")"

  def coerce_parameters_impl(self):
    None

  def can_create_from_shape_impl(self):
    return False
  
  def parameters_from_shape_impl(self):
    None
          
  def produce_impl(self):
    # Refpoint in the first end   
    # Left gap
    pts = [
      pya.DPoint(0, self.a/2+0),
      pya.DPoint(self.l, self.a/2+0),
      pya.DPoint(self.l, self.a/2+self.b),
      pya.DPoint(0, self.a/2+self.b)
    ]
    shape = pya.DPolygon(pts)    
    self.cell.shapes(self.layout.layer(self.lo)).insert(shape)        
    # Right gap    
    pts = [
      pya.DPoint(0, -self.a/2+0),
      pya.DPoint(self.l, -self.a/2+0),
      pya.DPoint(self.l, -self.a/2-self.b),
      pya.DPoint(0, -self.a/2-self.b)
    ]
    shape = pya.DPolygon(pts)  
    self.cell.shapes(self.layout.layer(self.lo)).insert(shape)   
    # Protection layer
    w = self.a/2 + self.b + self.margin
    pts = [
      pya.DPoint(0, -w),
      pya.DPoint(self.l, -w),
      pya.DPoint(self.l, w),
      pya.DPoint(0, w)
    ]
    shape = pya.DPolygon(pts)  
    self.cell.shapes(self.layout.layer(self.lp)).insert(shape)   

class WaveguideCopCurve(KQCirvuitPCell):
  """
  The PCell declaration of a curved segment of a coplanar waveguide.
  
  Cordinate origin is left at the center of the arch.
  """

  def __init__(self):
    super().__init__()
    self.param("alpha", self.TypeDouble, "Curve angle (rad)", default = math.pi)
    self.param("length", self.TypeDouble, "Actual length (um)", default = 0, readonly = True)
   
  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "WaveguideCopCurve(a=" + ('%.1f' % self.a) + ",b=" + ('%.1f' % self.b) + ")"

  def coerce_parameters_impl(self):
    # Update length
    self.length = self.r*abs(self.alpha)

  def can_create_from_shape_impl(self):
    return False
  
  def parameters_from_shape_impl(self):
    None
          
  def produce_impl(self):
    # Refpoint in the center of the turn
    alphastart = 0
    alphastop = self.alpha
    
    # Left gap
    pts = []  
    R = self.r-self.a/2
    pts += arc(R,alphastart,alphastop,self.n)
    R = self.r-self.a/2-self.b
    pts += arc(R,alphastop,alphastart,self.n)     
    shape = pya.DPolygon(pts)
    self.cell.shapes(self.layout.layer(self.lo)).insert(shape)        
    # Right gap
    pts = []  
    R = self.r+self.a/2
    pts += arc(R,alphastart,alphastop,self.n)
    R = self.r+self.a/2+self.b
    pts += arc(R,alphastop,alphastart,self.n)
    shape = pya.DPolygon(pts)
    self.cell.shapes(self.layout.layer(self.lo)).insert(shape)   
    # Protection layer
    pts = []  
    R = self.r-self.a/2-self.b-self.margin
    pts += arc(R,alphastart,alphastop,self.n)
    R = self.r+self.a/2+self.b+self.margin
    pts += arc(R,alphastop,alphastart,self.n)     
    shape = pya.DPolygon(pts)
    self.cell.shapes(self.layout.layer(self.lp)).insert(shape)     

class WaveguideCopTCross(KQCirvuitPCell):
  """
  The PCell declaration of T-crossing of waveguides
  """

  def __init__(self):
    super().__init__()
    self.param("a2", self.TypeDouble, "Width of the side waveguide", default = default_circuit_params["a"])
    self.param("b2", self.TypeDouble, "Gap of the side waveguide", default = default_circuit_params["b"])
    self.param("length_extra", self.TypeDouble, "Extra length", default = 0)
    self.param("length_extra_side", self.TypeDouble, "Extra length of the side waveguide", default = 0)
    
  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "WaveguideT"

  def coerce_parameters_impl(self):
    None

  def can_create_from_shape_impl(self):
    return False
  
  def parameters_from_shape_impl(self):
    None
          
  def produce_impl(self):
    # Origin: Crossing of centers of the center conductors
    # Direction: Ports from left, right and bottom
    # Top gap
    
    l = self.length_extra
    l2 = self.length_extra_side
    a2 = self.a2
    b2 = self.b2
    a = self.a
    b = self.b
    
    pts = [
      pya.DPoint(-l-b2-a2/2, a/2+0),
      pya.DPoint( l+b2+a2/2, a/2+0),
      pya.DPoint( l+b2+a2/2, a/2+b),
      pya.DPoint(-l-b2-a2/2, a/2+b)
    ]
    shape = pya.DPolygon(pts)    
    self.cell.shapes(self.layout.layer(self.lo)).insert(shape)        
    # Left gap   
    pts = [
      pya.DPoint(-l-b2-a2/2,-a/2+0),
      pya.DPoint(     -a2/2,-a/2+0),
      pya.DPoint(     -a2/2,-a/2-b-l2),
      pya.DPoint(  -b2-a2/2,-a/2-b-l2),
      pya.DPoint(  -b2-a2/2,-a/2-b),
      pya.DPoint(-l-b2-a2/2,-a/2-b)
    ]
    shape = pya.DPolygon(pts)  
    self.cell.shapes(self.layout.layer(self.lo)).insert(shape)         
    # Right gap   
    self.cell.shapes(self.layout.layer(self.lo)).insert(pya.DTrans.M90*shape)
    # Protection layer
    m = self.margin
    pts = [
      pya.DPoint(-l-b2-a2/2-m,  a/2+b+m),      
      pya.DPoint( l+b2+a2/2+m,  a/2+b+m),
      pya.DPoint( l+b2+a2/2+m, -a/2-b-l2-m),
      pya.DPoint(-l-b2-a2/2-m, -a/2-b-l2-m),
    ]
    shape = pya.DPolygon(pts)  
    self.cell.shapes(self.layout.layer(self.lp)).insert(shape)   
        
    # annotation text
    self.refpoints["port_left"] = pya.DPoint(-l-b2-a2/2, 0)
    self.refpoints["port_right"] = pya.DPoint( l+b2+a2/2, 0)
    self.refpoints["port_bottom"] = pya.DPoint(0, -a/2-b-l2)
    super().produce_impl() # adds refpoints
    
class WaveguideCop(KQCirvuitPCell):
  """
  The PCell declaration for an arbitrary coplanar waveguide
  """

  def __init__(self):
    super().__init__()
    self.param("path", self.TypeShape, "TLine", default = pya.DPath([pya.DPoint(0,0),pya.DPoint(100,0)],0))
    self.param("term1", self.TypeDouble, "Termination length start (um)", default = 0)
    self.param("term2", self.TypeDouble, "Termination length end (um)", default = 0)
    self.param("length", self.TypeDouble, "Actual length (um)", default = 0, readonly = True)

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "Waveguide l={}".format(self.length)
  
  def coerce_parameters_impl(self):
    # Even if it does nothing here, actually the parameters are synced between internal structures! 
    self.produce_waveguide(has_cell = False) # this recalculates self.length
    None  

  def can_create_from_shape_impl(self):
    return self.shape.is_path()
  
  def parameters_from_shape_impl(self):
    points = [pya.DPoint(point*self.layout.dbu) for point in self.shape.each_point()]
    self.path = pya.DPath(points, 1)
    
  def transformation_from_shape_impl(self):
    return pya.Trans()
  
  def produce_end_termination(self, i_point_1, i_point_2, term_len):
    # Termination is after point2. Point1 determines the direction.
    # Negative term_len does not make any sense.
    points = [point for point in self.path.each_point()]
    a = self.a
    
    b = self.b  
    
    v = (points[i_point_2]-points[i_point_1])*(1/points[i_point_1].distance(points[i_point_2]))
    u = pya.DTrans.R270.trans(v)
    shift_start = pya.DTrans(pya.DVector(points[i_point_2]))
    
    if term_len>0:
      poly = pya.DPolygon([u*(a/2+b),u*(a/2+b)+v*(term_len),u*(-a/2-b)+v*(term_len),u*(-a/2-b)])
      self.cell.shapes(self.layout.layer(self.lo)).insert(poly.transform(shift_start))
    
    # protection
    term_len+= self.margin
    poly2 = pya.DPolygon([u*(a/2+b+self.margin),u*(a/2+b+self.margin)+v*(term_len),u*(-a/2-b-self.margin)+v*(term_len),u*(-a/2-b-self.margin)])
    self.cell.shapes(self.layout.layer(self.lp)).insert(poly2.transform(shift_start))
  
  def produce_waveguide(self, has_cell = True):
    points = [point for point in self.path.each_point()]
    length = 0
    
    # Termination before the first segment
    if (has_cell):
      self.produce_end_termination(1, 0, self.term1)
    
    # For each segment except the last
    segment_last = points[0]
    self.l_temp = 0
    for i in range(0, len(points)-2):
      # Corner coordinates
      v1 = points[i+1]-points[i]
      v2 = points[i+2]-points[i+1]
      crossing = points[i+1]
      alpha1 = math.atan2(v1.y,v1.x)
      alpha2 = math.atan2(v2.y,v2.x)
      alphacorner = (((math.pi-(alpha2 - alpha1))/2)+alpha2)
      distcorner = v1.vprod_sign(v2)*self.r / math.sin((math.pi-(alpha2-alpha1))/2)
      corner = crossing + pya.DVector(math.cos(alphacorner)*distcorner, math.sin(alphacorner)*distcorner)
      #self.cell.shapes(self.layout.layer(self.la)).insert(pya.DText("%f, %f, %f" % (alpha2-alpha1,distcorner,v1.vprod_sign(v2)),corner.x,corner.y))  
            
      # Streight segment before the corner
      segment_start = segment_last
      segment_end = points[i+1]
      cut = v1.vprod_sign(v2)*self.r / math.tan((math.pi-(alpha2-alpha1))/2)
      l = segment_start.distance(segment_end)-cut
      length += l      
      angle = 180/math.pi*math.atan2(segment_end.y-segment_start.y, segment_end.x-segment_start.x)
      subcell = self.layout.create_cell("Waveguide streight", "KQCircuit", {
        "a": self.a,
        "b": self.b,
        "l": l # TODO: Finish the list
      })
      self.l_temp += subcell.pcell_parameters_by_name()["l"]
      transf = pya.DCplxTrans(1,angle,False,pya.DVector(segment_start))
      if has_cell:
        self.cell.insert(pya.DCellInstArray(subcell.cell_index(),transf))
      segment_last = points[i+1]+v2*(1/v2.abs())*cut
      
      # Curve at the corner
      subcell = self.layout.create_cell("Waveguide curved", "KQCircuit", {
        "a": self.a,
        "b": self.b,
        "alpha": alpha2-alpha1, # TODO: Finish the list,
        "n": self.n,
        "r": self.r
      })      
      transf = pya.DCplxTrans(1, alpha1/math.pi*180.0-v1.vprod_sign(v2)*90, False, corner)
      #coerce_parameters(subcell) # updates the internal parameters
      #length += inst.pcell_parameter("length")
      length += self.r*abs(alpha2-alpha1)
            
      if has_cell:
        inst = self.cell.insert(pya.DCellInstArray(subcell.cell_index(), transf))
    
    # Last segement
    segment_start = segment_last
    segment_end = points[-1]
    l = segment_start.distance(segment_end)  
    length += l
    self.length = length
    angle = 180/math.pi*math.atan2(segment_end.y-segment_start.y, segment_end.x-segment_start.x)
    
    # Terminate the end
    if has_cell:
      self.produce_end_termination(-2, -1, self.term2)

    subcell = self.layout.create_cell("Waveguide streight", "KQCircuit", {
      "a": self.a,
      "b": self.b,
      "l": l # TODO: Finish the list
    })
    transf = pya.DCplxTrans(1,angle,False,pya.DVector(segment_start))   
    if has_cell: 
      self.cell.insert(pya.DCellInstArray(subcell.cell_index(),transf)) 
    
  def produce_impl(self):      
    self.produce_waveguide()
     
