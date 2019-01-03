import pya
import math

class Circle(pya.PCellDeclarationHelper):
  """
  The PCell declaration for the circle
  """

  def __init__(self):

    # Important: initialize the super class
    super(Circle, self).__init__()

    # declare the parameters
    self.param("l", self.TypeLayer, "Layer", default = pya.LayerInfo(1, 0))
    self.param("s", self.TypeShape, "", default = pya.DPoint(0, 0))
    self.param("r", self.TypeDouble, "Radius", default = 0.1)
    self.param("n", self.TypeInt, "Number of points", default = 64)     
    # this hidden parameter is used to determine whether the radius has changed
    # or the "s" handle has been moved
    self.param("ru", self.TypeDouble, "Radius", default = 0.0, hidden = True)
    self.param("rd", self.TypeDouble, "Double radius", readonly = True)

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "Circle(L=" + str(self.l) + ",R=" + ('%.3f' % self.r) + ")"
  
  def coerce_parameters_impl(self):
  
    # We employ coerce_parameters_impl to decide whether the handle or the 
    # numeric parameter has changed (by comparing against the effective 
    # radius ru) and set ru to the effective radius. We also update the 
    # numerical value or the shape, depending on which on has not changed.
    rs = None
    if isinstance(self.s, pya.DPoint): 
      # compute distance in micron
      rs = self.s.distance(pya.DPoint(0, 0))
    if rs != None and abs(self.r-self.ru) < 1e-6:
      self.ru = rs
      self.r = rs 
    else:
      self.ru = self.r
      self.s = pya.DPoint(-self.r, 0)
    
    self.rd = 2*self.r
    
    # n must be larger or equal than 4
    if self.n <= 4:
      self.n = 4
  
  def can_create_from_shape_impl(self):
    # Implement the "Create PCell from shape" protocol: we can use any shape which 
    # has a finite bounding box
    return self.shape.is_box() or self.shape.is_polygon() or self.shape.is_path()
  
  def parameters_from_shape_impl(self):
    # Implement the "Create PCell from shape" protocol: we set r and l from the shape's 
    # bounding box width and layer
    self.r = self.shape.bbox().width() * self.layout.dbu / 2
    self.l = self.layout.get_info(self.layer)
  
  def transformation_from_shape_impl(self):
    # Implement the "Create PCell from shape" protocol: we use the center of the shape's
    # bounding box to determine the transformation
    return pya.Trans(self.shape.bbox().center())
  
  def produce_impl(self):
  
    # This is the main part of the implementation: create the layout
    print("Joonistab")
    
    # fetch the parameters
    ru_dbu = self.ru / self.layout.dbu
    
    # compute the circle
    pts = []
    da = math.pi * 2 / self.n
    for i in range(0, self.n):
      pts.append(pya.Point.from_dpoint(pya.DPoint(ru_dbu * math.cos(i * da), ru_dbu * math.sin(i * da))))
    
    # create the shape
    self.cell.shapes(self.l_layer).insert(pya.Polygon(pts))
