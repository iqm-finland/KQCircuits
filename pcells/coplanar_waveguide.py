import pya
import math

def TLineSegment(a, b, l):
  # Refpoint in the first end   
  pts = [
    pya.DPoint(0, a/2+0),
    pya.DPoint(l, a/2+0),
    pya.DPoint(l, a/2+b),
    pya.DPoint(0, a/2+b)
  ]
  shape1 = pya.DPolygon(pts)
  
  pts = [
    pya.DPoint(0, -a/2+0),
    pya.DPoint(l, -a/2+0),
    pya.DPoint(l, -a/2-b),
    pya.DPoint(0, -a/2-b)
  ]
  shape2 = pya.DPolygon(pts)

  return [shape1, shape2]

def up_mod(a, per):
  # Finds remindider in the same direction as periodicity
  if (a*per>0):
    return a % per
  else:
    return a-per*math.floor(a/per)
    
    
    
def Arc(R, start, stop, n):
  pts = []
  last = start
  
  #for alpha in numpy.arange(start, stop, 2*math.pi/n):
  alpha_rel = up_mod(stop-start, math.pi * 2) # from 0 to 2 pi
  alpha_step = 2*math.pi/n*(-1 if alpha_rel > math.pi else 1) # shorter dir
  n_steps = math.floor((2*math.pi-alpha_rel)/abs(alpha_step) if alpha_rel > math.pi else alpha_rel/abs(alpha_step))
  alpha = start
  print(alpha)
  for i in range(0,n_steps):
    pts.append(pya.DPoint(R * math.cos(alpha), R * math.sin(alpha)))    
    alpha += alpha_step
    last = alpha
  if last != stop:
    alpha = stop
    pts.append(pya.DPoint(R * math.cos(alpha), R * math.sin(alpha)))
  
  return pts
    
def TLineArc(a, b, r, alphastart, alphastop, n):
  # Refpoint in the center of the turn
  pts = []  
  R = r-a/2
  pts += Arc(R,alphastart,alphastop,n)
  print(pts)
  R = r-a/2-b
  pts += Arc(R,alphastop,alphastart,n)
  shape1 = pya.DPolygon(pts)
  
  pts = []  
  R = r+a/2
  pts += Arc(R,alphastart,alphastop,n)
  R = r+a/2+b
  pts += Arc(R,alphastop,alphastart,n)
  shape2 = pya.DPolygon(pts)
  
  return [shape1,shape2]
  
class TLine(pya.PCellDeclarationHelper):
  """
  The PCell declaration for the circle
  """

  def __init__(self):

    # Important: initialize the super class
    super(TLine, self).__init__()

    # declare the parameters
    self.param("lo", self.TypeLayer, "Layer optical", default = pya.LayerInfo(1, 0))
    self.param("lp", self.TypeLayer, "Layer protection", default = pya.LayerInfo(2, 0))
    self.param("path", self.TypeShape, "TLine", default = pya.DPath([pya.DPoint(0,0),pya.DPoint(1,0)],1))
    self.param("a", self.TypeDouble, "Width of center conductor (um)", default = 6)
    self.param("b", self.TypeDouble, "Width of gap (um)", default = 10)
    self.param("n", self.TypeInt, "Number of points on turns", default = 64)     
    # this hidden parameter is used to determine whether the radius has changed
    # or the "s" handle has been moved
    self.param("ru", self.TypeDouble, "Turn radius (um)", default = 20)
    self.num_points = 0

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "TLine(a=" + ('%.1f' % self.a) + ",b=" + ('%.1f' % self.b) + ")"
  
  def coerce_parameters_impl(self):
    
    # We employ coerce_parameters_impl to decide whether the handle or the 
    # numeric parameter has changed (by comparing against the effective 
    # radius ru) and set ru to the effective radius. We also update the 
    # numerical value or the shape, depending on which on has not changed.
    None

  def can_create_from_shape_impl(self):
    # Implement the "Create PCell from shape" protocol: we can use any shape which 
    # has a finite bounding box
    return self.shape.is_path()
  
  def parameters_from_shape_impl(self):
    # Implement the "Create PCell from shape" protocol: we set r and l from the shape's 
    # bounding box width and layer
    #self.r = self.shape.bbox().width() * self.layout.dbu / 2
    #self.l = self.layout.get_info(self.layer)
    #self.start = self.shape.bbox
    print("Creating from excisting path")
    points = [pya.DPoint(point*self.layout.dbu) for point in self.shape.each_point()]
    print("Points",points)
    self.path = pya.DPath(points, 1)
    
  def transformation_from_shape_impl(self):
    # Implement the "Create PCell from shape" protocol: we use the center of the shape's
    # bounding box to determine the transformation
    return pya.Trans()
    
  
  def produce_impl(self):      
    points = [point for point in self.path.each_point()]
    
    # For each segment except the last
    segment_last = points[0]
    for i in range(0, len(points)-2):
      # Corner coordinates
      v1 = points[i+1]-points[i]
      v2 = points[i+2]-points[i+1]
      crossing = points[i+1]
      alpha1 = math.atan2(v1.y,v1.x)
      alpha2 = math.atan2(v2.y,v2.x)
      alphacorner = (((math.pi-(alpha2 - alpha1))/2)+alpha2)
      distcorner = v1.vprod_sign(v2)*self.ru / math.sin((math.pi-(alpha2-alpha1))/2)
      corner = crossing + pya.DVector(math.cos(alphacorner)*distcorner, math.sin(alphacorner)*distcorner)
      self.cell.shapes(self.layout.layer(self.lp)).insert(pya.DText("%f, %f" % (alphacorner*180/math.pi,distcorner),corner.x,corner.y))        
            
      # Segment before the corner
      segment_start = segment_last
      segment_end = points[i+1]
      cut = v1.vprod_sign(v2)*self.ru / math.tan((math.pi-(alpha2-alpha1))/2)
      l = segment_start.distance(segment_end)-cut
      angle = 180/math.pi*math.atan2(segment_end.y-segment_start.y, segment_end.x-segment_start.x)
      shapes = TLineSegment(self.a,self.b,l)
      for shape in shapes:
        transf = pya.DCplxTrans(1,angle,False,pya.DVector(segment_start))
        shape.transform(transf)
        self.cell.shapes(self.layout.layer(self.lo)).insert(shape)
      segment_last = points[i+1]+v2*(1/v2.abs())*cut
      
      # Arc
      shapes = TLineArc(self.a, self.b, self.ru, alpha1-math.copysign(math.pi/2,distcorner), alpha2-math.copysign(math.pi/2,distcorner), self.n )
      print(shapes)
      for shape in shapes:
        transf = pya.DCplxTrans(1,0,False,corner)
        shape.transform(transf)
        self.cell.shapes(self.layout.layer(self.lo)).insert(shape)
    
    # Last segement
    segment_start = segment_last
    segment_end = points[-1]
    l = segment_start.distance(segment_end)
    angle = 180/math.pi*math.atan2(segment_end.y-segment_start.y, segment_end.x-segment_start.x)
    shapes = TLineSegment(self.a,self.b,l)
    for shape in shapes:
      transf = pya.DCplxTrans(1,angle,False,pya.DVector(segment_start))
      shape.transform(transf)
      self.cell.shapes(self.layout.layer(self.lo)).insert(shape)
     