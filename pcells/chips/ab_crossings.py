import pya
import math
from kqcircuit.pcells.chips.chip_base import ChipBase
from kqcircuit.defaults import default_layers

import sys
from importlib import reload
reload(sys.modules[ChipBase.__module__])

version = 1

class ABCrossings(ChipBase):
  """
  The PCell declaration for an arbitrary waveguide
  """
  
  def __init__(self):
    super().__init__()
    self.param("crossings", self.TypeInt, "Number of double crossings", default = 10)

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

#    port_qubit_dr = swissmon_refpoints_abs["port_drive"]            
#    port_qubit_fl = swissmon_refpoints_abs["port_flux"]
#    port_qubit_ro = swissmon_refpoints_abs["port_cplr1"]
    
    # Left transmission line 
    tl_1 = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  launchers["NW"][0], 
                  launchers["SW"][0]
                ],1)
    })    
    self.cell.insert(pya.DCellInstArray(tl_1.cell_index(), pya.DTrans()))
    
    # Right transmission line
    tl_2 = self.layout.create_cell("Waveguide", "KQCircuit", {
      "path": pya.DPath([
                  launchers["NE"][0], 
                  launchers["SE"][0]
                ],1)
    })    
    self.cell.insert(pya.DCellInstArray(tl_2.cell_index(), pya.DTrans()))
    
    # Crossing transmission line
    nodes = [("tl",launchers["WN"][0])]
    ref_x = launchers["NW"][0].x
    last_y = launchers["WN"][0].y
    crossings = self.crossings # must be even
    step = (launchers["WN"][0].y-launchers["WS"][0].y)/(crossings-0.5)/2
    wiggle = 250
    for i in range(crossings):
      nodes.append(("tl",pya.DPoint(ref_x-wiggle, last_y)))
      nodes.append(("ab",pya.DPoint(ref_x, last_y)))
      nodes.append(("tl",pya.DPoint(ref_x+wiggle, last_y)))
      last_y -= step 
      nodes.append(("tl",pya.DPoint(ref_x+wiggle, last_y)))
      nodes.append(("ab",pya.DPoint(ref_x, last_y)))
      nodes.append(("tl",pya.DPoint(ref_x-wiggle, last_y)))   
      last_y -= step  
    nodes.append(("tl",launchers["WS"][0]))
    self.produce_crossing_waveguide(nodes,self.b*4+self.a+10)
    
    # TL without crossings
    nodes = [("tl",launchers["EN"][0])]
    ref_x = launchers["NE"][0].x+2*wiggle+50
    last_y = launchers["EN"][0].y
    for i in range(crossings):
      nodes.append(("tl",pya.DPoint(ref_x+wiggle, last_y)))
      nodes.append(("tl",pya.DPoint(ref_x-wiggle, last_y)))
      last_y -= step 
      nodes.append(("tl",pya.DPoint(ref_x-wiggle, last_y)))
      nodes.append(("tl",pya.DPoint(ref_x+wiggle, last_y)))   
      last_y -= step  
    nodes.append(("tl",launchers["ES"][0]))
    self.produce_crossing_waveguide(nodes, self.b*4+self.a+10)
    
    # Mechanical test array
    p_test_origin = pya.DPoint(3600, 9000)
    v_distance_step = pya.DVector(0,-2000)
    v_length_step = pya.DVector(0,-100)
    v_width_step = pya.DVector(400,0)
    
    for i, length in enumerate(range(22,60,2)):
      for j, width in enumerate(range(5,20,2)):
        for k, distance in enumerate(range(2,22,5)):
          loc = p_test_origin + v_length_step*i + v_width_step*j + v_distance_step*k
          self.produce_mechanical_test(loc, distance, 10, length, width)
          
    # chip frame and possibly ground plane grid
    super().produce_impl()