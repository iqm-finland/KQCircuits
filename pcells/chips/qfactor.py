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
    self.param("res_lengths", self.TypeList, "Resonator lengths", default = [5434, 5429, 5374, 5412, 5493, 5589])
    self.param("n_fingers", self.TypeList, "Number of fingers of the coupler", default = [4, 4, 2, 4, 4, 4])
    self.param("l_fingers", self.TypeList, "Length of fingers", default = [23.1, 9.9, 14.1, 10, 21, 28,3])
    self.param("type_coupler", self.TypeList, "Coupler type", default = ["square","square","square","plate","plate","plate"])
    self.param("n_ab", self.TypeList, "Number of resonator airbridges", default = [5,0,5,5,5,5])
    self.param("res_term", self.TypeList, "Resonator termination type", default = ["galvanic","galvanic","galvanic","airbridge","airbridge","airbridge"])  
    
  def produce_impl(self): 
    # Interpretation of parameter lists    
    res_lengths = [float(foo) for foo in self.res_lengths]
    n_fingers = [int(foo) for foo in self.n_fingers]
    type_coupler = self.type_coupler
    n_ab = [int(foo) for foo in self.n_ab]
    l_fingers = [float(foo) for foo in self.l_fingers]
    res_term = self.res_term
        
    # Launchers
    launchers = self.produce_launchers_SMA8(enabled=["WN","EN"])    
    tl_start = launchers["WN"][0]
    tl_end = launchers["EN"][0]
    
    resonators = len(self.res_lengths)
    v_res_step = (tl_end-tl_start)*(1./resonators)
    cell_cross = self.layout.create_cell("Waveguide cross", "KQCircuit", {
      "length_extra_side": 2*self.a})
      
    pos_last_feedline = tl_start
    
    # Airbridge crossing resonators
    cell_ab_crossing = self.layout.create_cell("Airbridge", "KQCircuit", {
                      "bridge_length": self.b*2+self.a+4,
                      }) 
    # Airbridge for termination of a resonator
    cell_ab_terminate = self.layout.create_cell("Airbridge", "KQCircuit", {
                      "pad_width": self.a-2,
                      "pad_length": self.a*2, # BUG?
                      "bridge_length": self.b*1+4,
                      "bridge_width": self.a-2,
                      "pad_extra": 1
                      })   
    
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
      if res_term[i] == "airbridge":
        cell_res = self.layout.create_cell("Waveguide", "KQCircuit", {
        "path": pya.DPath([
                    pos_res_start, 
                    pos_res_end
                  ],1),
        "term2" : self.b,
        })
        pos_term_ab = pos_res_end+pya.DVector(0,-self.b/2)
        self.cell.insert(pya.DCellInstArray(cell_ab_terminate.cell_index(), pya.DTrans(0, False, pos_term_ab)))
      else:
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
      pos_last_feedline = cross_refpoints_abs["port_right"]\
      
      # Airbridges
      if n_ab[i]:
        ab_step = (pos_res_end-pos_res_start)*(1./n_ab[i])
        for j in range(n_ab[i]):
          pos_ab = pos_res_start+ab_step*(j+0.5)
          self.cell.insert(pya.DCellInstArray(cell_ab_crossing.cell_index(), pya.DTrans(1,False,pos_ab))) 
      
    # Last feedline
    cell_tl = self.layout.create_cell("Waveguide", "KQCircuit", {
    "path": pya.DPath([
                pos_last_feedline, 
                tl_end
              ],1),
    "term2" : 0,
    })   
    self.cell.insert(pya.DCellInstArray(cell_tl.cell_index(), pya.DTrans()))
    
    
    # Basis chip with possibly ground plane grid
    super().produce_impl()
    