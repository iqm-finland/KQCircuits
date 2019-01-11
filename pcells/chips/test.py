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

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return("TestChipV{}".format(version))
  
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
    launchers = [
      (pya.DPoint(1800,2800),"W","IN"),      
      (pya.DPoint(8200,2800),"E","OUT"),      
      (pya.DPoint(1800,7200),"W","IN"),      
      (pya.DPoint(8200,7200),"E","OUT"),
      (pya.DPoint(2800,1800),"S","Unused"),      
      (pya.DPoint(2800,8200),"N","Unused"),      
      (pya.DPoint(7200,1800),"S","Unused"),      
      (pya.DPoint(7200,8200),"N","Unused")
    ]
    for launcher in launchers:
      self.produce_launcher(launcher[0],launcher[1],launcher[2])
    
    # Waveguide
    #guideline = pya.DPath([launchers[0][0],launchers[1][0]],1)
    #waveguide1 = self.layout.create_cell("Waveguide", "KQCircuit", {
    #  "path": gudieline
    #})
    #self.cell.insert(waveguide1)
    #self.cell.shapes(self.layout.layer(self.lo)).insert(guideline)
      
    # Meander
    meander = self.layout.create_cell("Meander", "KQCircuit", {
      "start": launchers[0][0],
      "end": launchers[1][0],
      "length": 8000*2,
      "meanders": 10
    })    
    self.cell.insert(pya.DCellInstArray(meander.cell_index(), pya.DTrans(pya.DVector(0, 0))))
    
    # Swissmon      
    swissmon = self.layout.create_cell("Swissmon", "KQCircuit", {})  
    self.cell.insert(pya.DCellInstArray(swissmon.cell_index(), pya.DTrans(pya.DVector(5000, 5000))))
      


