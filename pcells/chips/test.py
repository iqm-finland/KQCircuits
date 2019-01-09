import pya
import math
from kqcircuit.pcells.chips.chip_base import ChipBase

version = 1
    
class TestChip(ChipBase):
  """
  The PCell declaration for an arbitrary waveguide
  """
  
  def __init__(self):
    super().__init__()
    self.param("freqQ1", self.TypeDouble, "Frequency QB1 (GHz)", default = 100)
    self.param("freqRR1", self.TypeDouble, "Frequency RR1 (GHz)", default = 100)
    self.margin = 100

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return("TestChipV%.2D".format(version))
  
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
    super().produce_impl()
    
    
    # Launcher
    launcher_positions = [
      (pya.DPoint(1000,3000),"w"),      
      (pya.DPoint(9000,3000),"e"),
    ]
    
    # Waveguide
    guideline = pya.DPath([launcher_positions[0][0],launcher_positions[1][0]],1)
    #waveguide1 = self.layout.create_cell("Waveguide", "KQCircuit", {
    #  "path": gudieline
    #})
    #self.cell.insert(waveguide1)
    
    
    c1 = self.layout.create_cell("Meander", "KQCircuit", {
      "start": launcher_positions[0][0],
      "end": launcher_positions[1][0],
      "length": 8000*2
    })
      
    #self.cell.shapes(self.layout.layer(self.lo)).insert(guideline)
    self.cell.insert(pya.DCellInstArray(c1.cell_index(), pya.DTrans(pya.DVector(0, 0))))


