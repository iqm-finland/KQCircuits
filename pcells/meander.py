import pya
import math
from kqcircuit.pcells.kqcircuit_pcell import KQCirvuitPCell

class MeanderCenter(KQCirvuitPCell):
  """
  The PCell declaration for an arbitrary waveguide
  """

  def __init__(self):
    super().__init__()
    self.param("start", self.TypeShape, "Start", default = pya.DPoint(0,0))
    self.param("end", self.TypeShape, "End", default = pya.DPoint(200,0))
    self.param("length", self.TypeDouble, "Length (um)", default = 400)
    self.param("meanders", self.TypeInt, "Number of meanders (at least 2)", default = 3)

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "Meander(m=%.1d,l=%.1f)".format(meanders,length)
      
  def coerce_parameters_impl(self):
    self.meanders = max(self.meanders,2)

  def can_create_from_shape_impl(self):
    return self.shape.is_path()
  
  def parameters_from_shape_impl(self):
    points = [pya.DPoint(point*self.layout.dbu) for point in self.shape.each_point()]
    self.start = points[0]
    self.end = points[-1]
    
  def transformation_from_shape_impl(self):
    return pya.Trans()    
  
  def produce_impl(self):          
    points = [pya.DPoint(0,0)]    
    l_direct = self.start.distance(self.end)    
    l_rest = l_direct - self.meanders*2*self.r
    l_single_meander = (l_direct - self.length + self.meanders*(math.pi-4)*self.r)/(2-2*self.meanders)
    
    points.append(pya.DPoint(l_rest/2,0))
    for i in range(self.meanders):      
      points.append(pya.DPoint(l_rest/2 + i*2*self.r, ((-1)**(i%2))*l_single_meander))
      points.append(pya.DPoint(l_rest/2 + (i+1)*2*self.r, ((-1)**(i%2))*l_single_meander))    
    points.append(pya.DPoint(l_direct-l_rest/2,0))
    points.append(pya.DPoint(l_direct,0))
    
    for point in points:
      print(type(point), point)
      #self.cell.shapes(self.layout.layer(9,0)).insert(pya.DText("meander",point.x,point.y))
      
    #self.cell.shapes(self.layout.layer(9,0)).insert(pya.DPath(points,1.))
    
    waveguide = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath(points,1.)
    })
      
    angle = 180/math.pi*math.atan2(self.end.y-self.start.y, self.end.x-self.start.x)
    transf = pya.DCplxTrans(1,angle,False,pya.DVector(self.start))    
    self.cell.insert(pya.DCellInstArray(waveguide.cell_index(),transf)) 
