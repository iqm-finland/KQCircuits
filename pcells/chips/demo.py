import pya
import math
from kqcircuit.pcells.chips.chip_base import ChipBase
from kqcircuit.defaults import default_layers

import sys
from importlib import reload
reload(sys.modules[ChipBase.__module__])

version = 1
    
class DemoChip(ChipBase):
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
    
    
    swissmon_refpoints_rel = self.get_refpoints(swissmon)        
        
    swissmon_pos_v = pya.DVector(2800-swissmon_refpoints_rel["port_drive"].y, 7200) 
    swissmon_instance = self.cell.insert(pya.DCellInstArray(swissmon.cell_index(), pya.DCplxTrans(1, -90, False, swissmon_pos_v)))

    print("Transformation:",pya.DCplxTrans(1, -90, False, swissmon_pos_v))
    swissmon_refpoints_abs = self.get_refpoints(swissmon, swissmon_instance.dtrans)        

    port_qubit_dr = swissmon_refpoints_abs["port_drive"]            
    port_qubit_fl = swissmon_refpoints_abs["port_flux"]
    port_qubit_ro = swissmon_refpoints_abs["port_cplr1"]
    
    # Driveline 
    driveline = self.layout.create_cell("Waveguide", "KQCircuit", {
      "term2" : self.b,
      "path": pya.DPath([
                  launchers[5][0], 
                  launchers[5][0]+pya.DVector(0,-self.r),         
                  port_qubit_dr+pya.DVector(0,self.r), 
                  port_qubit_dr
                ],1)
    })    
    self.cell.insert(pya.DCellInstArray(driveline.cell_index(), pya.DTrans()))
    
    # Fluxline
    fluxline = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  launchers[2][0], 
                  launchers[2][0]+pya.DVector(self.r,0),         
                  port_qubit_fl+pya.DVector(-self.r,0), 
                  port_qubit_fl
                ],1)
    })    
    self.cell.insert(pya.DCellInstArray(fluxline.cell_index(), pya.DTrans()))
        
    # Capacitor J
    capj = self.layout.create_cell("FingerCap", "KQCircuit", {
      "finger_number": 2
    })    
    capj_inst = self.cell.insert(pya.DCellInstArray(capj.cell_index(), pya.DTrans(pya.DVector(5400, 7200))))
    capj_refpoints_abs = self.get_refpoints(capj, capj_inst.dtrans)        
    print("capj_refpoints_abs",capj_refpoints_abs)
    
    # Capacitor kappa
    capk = self.layout.create_cell("FingerCap", "KQCircuit", {
      "finger_number": 8
    })    
    capk_inst = self.cell.insert(pya.DCellInstArray(capk.cell_index(), pya.DTrans(pya.DVector(7800, 7200))))
    capk_refpoints_abs = self.get_refpoints(capk, capk_inst.dtrans)  


    # Readout resonator    
    readout = self.layout.create_cell("Meander", "KQCircuit", {
      "start": port_qubit_ro,
      "end": capj_refpoints_abs["port_a"],
      "length": 8000,
      "meanders": 20
    })    
    self.cell.insert(pya.DCellInstArray(readout.cell_index(), pya.DTrans(pya.DVector(0, 0))))
    
    # Purcell filter
    purcell = self.layout.create_cell("Meander", "KQCircuit", {
      "start": capj_refpoints_abs["port_b"],
      "end": capk_refpoints_abs["port_a"],
      "length": 7500,
      "meanders": 20
    })    
    self.cell.insert(pya.DCellInstArray(purcell.cell_index(), pya.DTrans(pya.DVector(0, 0))))

    # Output line
    outputline = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  capk_refpoints_abs["port_b"], 
                  capk_refpoints_abs["port_b"]+pya.DVector(self.r,0),         
                  launchers[3][0]+pya.DVector(-self.r,0), 
                  launchers[3][0]+pya.DVector(0,0)
                ],1)
    })    
    self.cell.insert(pya.DCellInstArray(outputline.cell_index(), pya.DTrans()))