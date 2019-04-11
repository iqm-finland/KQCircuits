import pya
import math
from kqcircuit.pcells.chips.chip_base import ChipBase
from kqcircuit.defaults import default_layers
from kqcircuit.coupler_lib import produce_library_capacitor

import sys
from importlib import reload
reload(sys.modules[ChipBase.__module__])

version = 1

class ChipQFactor(ChipBase):
  """
  The PCell declaration for an arbitrary waveguide
  """
  
  def __init__(self):
    super().__init__()
    self.param("crossings", self.TypeInt, "Number of double crossings", default = 10)

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return("QTest{}".format(version))
  
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
    # Basis chip
    super().produce_impl()
    
    # Launchers
    launchers = self.produce_launchers_SMA8()    
    tl_start = launchers["EN"][0]
    tl_end = launchers["WN"][0]
    
    resonators=6
    v_res_step = (tl_end-tl_start)*(1./resonators)
    cell_cross = self.layout.create_cell("Waveguide cross", "KQCircuit", {})
    crosses = []
    res_lengths = [5434, 5429, 5374, 5412, 5493, 5589]
    n_fingers = [4, 4, 2, 4, 4, 4]
    type_coupler = ["square","square","square","plate","plate","plate"]
    l_fingers = [23.1, 9.9, 14.1, 10, 21, 28,3]
    pos_last_feedline = tl_start
    
    for i in range(resonators):
      # Cross
      cross_trans = pya.DTrans(tl_start+v_res_step*(i+0.5))
      inst_cross = self.cell.insert(pya.DCellInstArray(cell_cross.cell_index(), cross_trans))
      cross_refpoints_abs = self.get_refpoints(cell_cross, inst_cross.dtrans)        

      # Coupler
      cplr = produce_library_capacitor(self.layout, n_fingers[i], l_fingers[i], type_coupler[i])
      cplr_refpoints_rel = self.get_refpoints(cplr)
      cplr_pos = cross_refpoints_abs["port_bottom"]-pya.DTrans.R90*cplr_refpoints_rel["port_b"]
      cplr_trans = pya.DTrans(1, False, cplr_pos.x, cplr_pos.y)
      self.cell.insert(pya.DCellInstArray(cplr.cell_index(), cplr_trans))
            
      # Resonator
      pos_res_start = cplr_pos+pya.DTrans.R90*cplr_refpoints_rel["port_a"]
      pos_res_end = cplr_pos+pya.DVector(0,-res_lengths[i])
      cell_res = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  pos_res_start, 
                  pos_res_end
                ],1),
      "term2" : 0,
      })   
      self.cell.insert(pya.DCellInstArray(cell_res.cell_index(), pya.DTrans()))
      
      # Feedline 
      cell_tl = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  pos_last_feedline, 
                  cross_refpoints_abs["port_left"]
                ],1),
      "term2" : 0,
      })   
      self.cell.insert(pya.DCellInstArray(cell_tl.cell_index(), pya.DTrans()))      
      pos_last_feedline = cross_refpoints_abs["port_right"]
      
    # Last feedline
    cell_tl = self.layout.create_cell("Waveguide", "KQCircuit", {
    "path": pya.DPath([
                pos_last_feedline, 
                tl_end
              ],1),
    "term2" : 0,
    })   
    self.cell.insert(pya.DCellInstArray(cell_tl.cell_index(), pya.DTrans()))
    