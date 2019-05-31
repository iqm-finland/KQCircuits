import pya
import math
from kqcircuit.pcells.chips.chip_base import ChipBase
from kqcircuit.defaults import default_layers
from kqcircuit.pcells.kqcircuit_pcell import coerce_parameters

import sys
from importlib import reload
reload(sys.modules[ChipBase.__module__])

version = 1

class ChipShaping(ChipBase):
  """
  The PCell declaration
  """
  
  def __init__(self):
    super().__init__()   
    self.r = 100

  def produce_mechanical_test(self, loc, distance, number, length, width):
    
    wg_len = number*(distance+width)
    wg_start = loc+pya.DVector(-wg_len/2,0)
    wg_end = loc+pya.DVector(+wg_len/2,0)
    v_step = pya.DVector(distance+width,0)
    
    # airbridge
    ab = self.layout.create_cell("Airbridge", "KQCircuit", {
                          "pad_width": 1.1*width,
                          "pad_length": 1*width,
                          "bridge_length": length,
                          "bridge_width": width,
                          "pad_extra": 1
                          }) 
    for i in range(number):
      ab_trans = pya.DCplxTrans(1, 0, False, wg_start+v_step*(i+0.5))
      self.cell.insert(pya.DCellInstArray(ab.cell_index(), ab_trans))
                          
    # waveguide
    wg = self.layout.create_cell("Waveguide", "KQCircuit", {
          "path": pya.DPath([wg_start,wg_end],1)     
        })    
    self.cell.insert(pya.DCellInstArray(wg.cell_index(), pya.DTrans()))
  
  def produce_crossing_waveguide(self, nodes, ab_length):
    # we assume the first node is not an airbridge
    tl_path = [nodes[0][1]]   
    tl_is_first = True
    
    # airbridge
    ab = self.layout.create_cell("Airbridge", "KQCircuit", {
                          "pad_width": self.a-1,
                          "pad_length": self.a*2, # BUG?
                          "bridge_length": ab_length,
                          "bridge_width": self.a-1,
                          "pad_extra": 1
                          }) 
    # conductor distanance
    cd = ab_length/2
    # neighbour airbridge distanance
    nad = self.b+self.a
     
    # we assume at least to nodes
    for node in nodes[1:]:
      if node[0] == "tl":
        # just a kink in the waveguide
        tl_path.append(node[1])
      else:
        # direction of the last waveguide segment
        v_dir = node[1]-tl_path[-1]
        v_ort = pya.DTrans.R90*v_dir
        alpha = math.atan2(v_dir.y,v_dir.x)
        # finish the waveguide
        tl_path.append(node[1]-v_dir*(cd/v_dir.length()))
        wg = self.create_sub_cell("Waveguide", {
          "path": pya.DPath(tl_path,1),
          "term1" : 0 if tl_is_first else self.b,         
          "term2" : self.b,         
        })    
        tl_is_first = False
        self.cell.insert(pya.DCellInstArray(wg.cell_index(), pya.DTrans()))
        # place the ab
        ab_trans = pya.DCplxTrans(1, alpha/math.pi*180.+90., False, node[1])
        self.cell.insert(pya.DCellInstArray(ab.cell_index(), ab_trans))
        ab_trans = pya.DCplxTrans(1, alpha/math.pi*180.+90., False, node[1]+v_ort*(nad/v_ort.length()))     
        self.cell.insert(pya.DCellInstArray(ab.cell_index(), ab_trans))    
        ab_trans = pya.DCplxTrans(1, alpha/math.pi*180.+90., False, node[1]-v_ort*(nad/v_ort.length()))     
        self.cell.insert(pya.DCellInstArray(ab.cell_index(), ab_trans))        
        # start new waveguide
        tl_path = [node[1]+v_dir*(cd/v_dir.length())]

    # finish the last waveguide
    wg = self.create_sub_cell("Waveguide", {
      "path": pya.DPath(tl_path,1),
      "term1" : self.b
    })
    self.cell.insert(pya.DCellInstArray(wg.cell_index(), pya.DTrans()))
  
  def produce_impl(self):  
    
    # Launcher
    launchers = self.produce_launchers_SMA8() 
        
    # Finnmon
    finnmon = self.layout.create_cell("Swissmon", "KQCircuit", {
      "fluxline": True,
      "arm_width": [30,23,30,23],
      "arm_length": [190,96,160,96],
      "gap_width": 89,
      "corner_r": 2,
      "cpl_length": [235,0,205],
      "cpl_width": [60,42,60],
      "cpl_gap": [110, 112, 110],
      "cl_offset": [150,150]
    })  
    finnmon_inst = self.cell.insert(pya.DCellInstArray(finnmon.cell_index(), pya.DTrans(3,False,4000,5000)))
    
    finnmon_refpoints_abs = self.get_refpoints(finnmon, finnmon_inst.dtrans)        
    port_qubit_dr = finnmon_refpoints_abs["port_drive"]            
    port_qubit_fl = finnmon_refpoints_abs["port_flux"]
    port_qubit_ro = finnmon_refpoints_abs["port_cplr0"]
    port_qubit_sh = finnmon_refpoints_abs["port_cplr2"]
    
    # Chargeline
    tl = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  launchers["WN"][0],
                  launchers["WN"][0]+pya.DVector(self.r,0),
                  port_qubit_dr-pya.DVector(self.r,0),
                  port_qubit_dr
                ],1),
      "r": self.r,
      "term2" : self.b,
    })    
    self.cell.insert(pya.DCellInstArray(tl.cell_index(), pya.DTrans()))
    
    # Fluxline
    fl = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  launchers["WS"][0],
                  launchers["WS"][0]+pya.DVector(self.r,0),
                  port_qubit_fl-pya.DVector(self.r,0),
                  port_qubit_fl
                ],1),
      "r": self.r
    })    
    self.cell.insert(pya.DCellInstArray(fl.cell_index(), pya.DTrans()))    
    
    # Readout resonator
    waveguide_length = 0    
    wg1_end = port_qubit_ro+pya.DVector(0,400)+pya.DVector(200,0)
    waveguide1 = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  port_qubit_ro,
                  port_qubit_ro+pya.DVector(0,self.r),
                  port_qubit_ro+pya.DVector(0,400),
                  wg1_end,
                ],1),
      "r": self.r
    })    
    inst = self.cell.insert(pya.DCellInstArray(waveguide1.cell_index(), pya.DTrans()))
    coerce_parameters(inst) # updates the internal parameters
    waveguide_length += inst.pcell_parameter("length")
    
    meander1_end = wg1_end+pya.DVector(400, 0)
    meander1 = self.layout.create_cell("Meander", "KQCircuit", {
      "start": wg1_end,
      "end": meander1_end,
      "length": 600,
      "meanders": 2,
      "r": self.r
    })    
    self.cell.insert(pya.DCellInstArray(meander1.cell_index(), pya.DTrans(pya.DVector(0, 0))))
  
    cross1 = self.layout.create_cell("Waveguide cross", "KQCircuit", {
      "length_extra_side": 2*self.a,
      "length_extra": 50,
      "r": self.r}) 
    cross1_refpoints_rel = self.get_refpoints(cross1, pya.DTrans(2,False,0,0))
    port_rel_cross1_wg1 = cross1_refpoints_rel["port_right"]            
    port_rel_cross1_wg2 = cross1_refpoints_rel["port_left"]
    port_rel_cross1_dr = cross1_refpoints_rel["port_bottom"]
    cross1_inst = self.cell.insert(pya.DCellInstArray(
      cross1.cell_index(), 
      pya.DTrans(2,False,meander1_end-port_rel_cross1_wg1)
      ))
    cross1_refpoints_abs = self.get_refpoints(cross1, cross1_inst.dtrans)
        
    meander2_end = meander1_end+port_rel_cross1_wg2+pya.DVector(400, 0)
    meander2 = self.layout.create_cell("Meander", "KQCircuit", {
      "start": meander1_end-port_rel_cross1_wg1+port_rel_cross1_wg2,
      "end": meander2_end,
      "length": 600,
      "meanders": 2,
      "r": self.r
    })    
    self.cell.insert(pya.DCellInstArray(meander2.cell_index(), pya.DTrans(pya.DVector(0, 0))))
    
    cross2_refpoints_rel = self.get_refpoints(cross1, pya.DTrans(0,False,0,0))
    port_rel_cross2_wg2 = cross2_refpoints_rel["port_left"]         
    port_rel_cross2_jcap = cross2_refpoints_rel["port_right"]
    port_rel_cross2_wg3 = cross2_refpoints_rel["port_bottom"]
    cross2_inst = self.cell.insert(pya.DCellInstArray(cross1.cell_index(), pya.DTrans(0,False,meander2_end-port_rel_cross2_wg2)))
    cross2_refpoints_rel = self.get_refpoints(cross1, cross2_inst.dtrans)
     
    # Capacitor J
    capj = self.layout.create_cell("FingerCapS", "KQCircuit", {
      "finger_number": 2
    })    
    port_rel_capj = self.get_refpoints(capj, pya.DTrans())  
    capj_inst = self.cell.insert(pya.DCellInstArray(capj.cell_index(), pya.DTrans(cross2_refpoints_rel["port_right"]-port_rel_capj["port_a"])))
 
    cross3_inst = self.cell.insert(pya.DCellInstArray(cross1.cell_index(), 
      pya.DTrans(0,False,cross2_refpoints_rel["port_right"]-port_rel_capj["port_a"]+port_rel_capj["port_b"]-port_rel_cross2_wg2)))
    port_abs_cross3 = self.get_refpoints(cross1, cross3_inst.dtrans)  
        
    meander3_end = port_abs_cross3["port_right"] + pya.DVector(1000, 0)
    meander3 = self.layout.create_cell("Meander", "KQCircuit", {
      "start": port_abs_cross3["port_right"],
      "end": meander3_end,
      "length": 3*600,
      "meanders": 6,
      "r": self.r
    })    
    self.cell.insert(pya.DCellInstArray(meander3.cell_index(), pya.DTrans(pya.DVector(0, 0))))
    
    waveguide2 = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  meander3_end,
                  meander3_end+pya.DVector(self.r,0),
                  meander3_end+pya.DVector(self.r,400),
                  meander3_end+pya.DVector(self.r,400+self.r),
                ],1),
      "r": self.r
    })  
    self.cell.insert(pya.DCellInstArray(waveguide2.cell_index(), pya.DTrans(pya.DVector(0, 0))))
        
    # Capacitor Kappa
    capk = self.layout.create_cell("FingerCapS", "KQCircuit", {
      "finger_number": 4
    })    
    port_rel_capk = self.get_refpoints(capk, pya.DTrans(1,False,0,0))  
    capk_inst = self.cell.insert(pya.DCellInstArray(capj.cell_index(), 
      pya.DTrans(1,False,meander3_end+pya.DVector(self.r,400+self.r)-port_rel_capk["port_a"])))
    port_abs_capk = self.get_refpoints(capk, capk_inst.dtrans)  
        
    waveguide3 = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  port_abs_capk["port_b"],
                  port_abs_capk["port_b"]+pya.DVector(0,self.r),
                  launchers["NE"][0]+pya.DVector(0,-self.r),
                  launchers["NE"][0]+pya.DVector(0,0),
                ],1),
      "r": self.r
    })  
    self.cell.insert(pya.DCellInstArray(waveguide3.cell_index(), pya.DTrans(pya.DVector(0, 0))))

    # Capacitor Kappa
    capi = self.layout.create_cell("FingerCapS", "KQCircuit", {
      "finger_number": 0
    })    
    port_rel_capi = self.get_refpoints(capk, pya.DTrans(1,False,0,0))  
    capi_inst = self.cell.insert(pya.DCellInstArray(capi.cell_index(), 
      pya.DTrans(1,False,cross1_refpoints_abs["port_bottom"]-port_rel_capk["port_a"])))
    port_abs_capi = self.get_refpoints(capi, capi_inst.dtrans)  
        
    waveguide4 = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  port_abs_capi["port_b"],
                  port_abs_capi["port_b"]+pya.DVector(0,self.r),
                  launchers["NW"][0]+pya.DVector(0,-self.r),
                  launchers["NW"][0]+pya.DVector(0,0),
                ],1),
      "r": self.r
    })  
    self.cell.insert(pya.DCellInstArray(waveguide4.cell_index(), pya.DTrans(pya.DVector(0, 0))))
        
    # chip frame and possibly ground plane grid
    super().produce_impl()