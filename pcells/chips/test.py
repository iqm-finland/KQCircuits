import pya
import math
from kqcircuit.pcells.chips.chip_base import ChipBase
from kqcircuit.defaults import default_layers

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
      (pya.DPoint(1800,7200),"W","Flux"),      
      (pya.DPoint(8200,7200),"E","OUT"),
      (pya.DPoint(2800,1800),"S","Unused"),      
      (pya.DPoint(2800,8200),"N","Drive"),      
      (pya.DPoint(7200,1800),"S","Unused"),      
      (pya.DPoint(7200,8200),"N","Unused")
    ]
    for launcher in launchers:
      self.produce_launcher(launcher[0],launcher[1],launcher[2])
          
    # Meander demo
    meander = self.layout.create_cell("Meander", "KQCircuit", {
      "start": launchers[0][0],
      "end": launchers[1][0],
      "length": 8000*2,
      "meanders": 10
    })    
    self.cell.insert(pya.DCellInstArray(meander.cell_index(), pya.DTrans(pya.DVector(0, 0))))
    
    # Swissmon      
    swissmon = self.layout.create_cell("Swissmon", "KQCircuit", {
      "cpl_length": [0,160,0]
    })  
    swissmon_pos_v = pya.DVector(2800, 7200)
    swissmon_instance = self.cell.insert(pya.DCellInstArray(swissmon.cell_index(), pya.DCplxTrans(1, -90, False, swissmon_pos_v)))
    
    swissmon_refpoints = {}    
    for shape in swissmon.shapes(self.layout.layer(default_layers["Annotations"])).each():
      print(shape.type())
      if shape.type()==pya.Shape.TText:
        swissmon_refpoints[shape.text_string] = swissmon_instance.trans.trans(shape.text_dpos)
        print(swissmon_refpoints[shape.text_string])
    port_qubit_dr = swissmon_refpoints["cplr_port0"]
    port_qubit_ro = swissmon_refpoints["cplr_port1"]

    # Driveline 
    waveguide1 = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([launchers[5][0], pya.DPoint(0, 0)+swissmon_pos_v+port_qubit_dr],1)
    })
    
    self.cell.insert(pya.DCellInstArray(waveguide1.cell_index(), pya.DCplxTrans(1, 0, False, pya.DVector(0, 0))))


