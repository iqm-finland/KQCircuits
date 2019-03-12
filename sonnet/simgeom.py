import copy
import pya
import kqcircuit.sonnet.parser as parser
from kqcircuit.defaults import default_layers

class Port():
  def __init__(self, sonnet_nr, location):  
    self.sonnet_nr = sonnet_nr
    self.ref_location = location
    
  def location(self):
    return self.ref_location
    
class SidePort(Port):
  def __init__(self, sonnet_nr, location, side, termination = False):
    super().__init__(sonnet_nr, location)
    self.side = {
      "l": "LEFT",
      "r": "RIGHT",
      "t": "TOP", # TODO Check from Sonnet documentation, if the keyword is correct!
      "b": "BOTTOM", # TODO Check from Sonnet documentation, if the keyword is correct!
    }[side]
    self.termination = termination # width of the ground plane gap in the end for the transmission line
    self.dbox = None
  
  def location(self):
    dbox = self.dbox
    return {
      "LEFT": pya.DVector(dbox.p1.x, self.ref_location.y),
      "RIGHT": pya.DVector(dbox.p2.x, self.ref_location.y),
      "TOP": pya.DVector(self.ref_location.x, dbox.p2.y),
      "BOTTOM": pya.DVector(self.ref_location.x, dbox.p1.y),
    }[self.side]
    


def simple_region(region):
  return pya.Region([poly.to_simple_polygon() for poly in region.each()])
  
def add_sonnet_geometry(
      cell, 
      simualtion_safety = 300, # microns
      ports = [],
      grid_size = 1, # microns
      symmetry = False # top-bottom symmetry for sonnet 
    ):
  layout = cell.layout()
  dbu = layout.dbu
  layer_opt = layout.layer(default_layers["Optical lit. 1"])
  layer_son = layout.layer(default_layers["Sonnet export"])
  region_neg = pya.Region(cell.begin_shapes_rec(layer_opt))

  # safety ground 
  region_pos = cell.dbbox_per_layer(layer_opt)
  region_pos = pya.Region(region_pos.enlarge(
                      simualtion_safety, 
                      simualtion_safety + (region_pos.height() % 2)/2 # also esnure summetry for 1 um grid
                      ).to_itype(dbu))

  # add port feedlines
  for port in ports:    
    if isinstance(port, SidePort):      
      port.dbox = region_pos.bbox().to_dtype(dbu)
      
      cell.shapes(layer_son).insert(pya.DText("port {}".format(port.sonnet_nr),pya.DTrans(port.location())))
      driveline = layout.create_cell("Waveguide", "KQCircuit", {
        "path": pya.DPath([
                    port.ref_location,
                    port.location()
                  ],1),
        "term1": port.termination
      })
      region_neg = region_neg + pya.Region(driveline.begin_shapes_rec(layer_opt))
    else:
      cell.shapes(layer_son).insert(pya.DText("port {}".format(port.sonnet_nr),pya.DTrans(port.location())))
  region_pos -= region_neg
  simregion = simple_region(region_pos);
  cell.shapes(layer_son).insert(simregion) 
  
  # find port edges  
  # to preserv the port edge indexes the geometry must not be changed after this
  sstring_ports = ""
  refplane_dirs = []
  for port in ports:        
    refplane_dirs += port.side
    print("Looking for parts 2")
    sstring_ports += poly_and_edge_indeces(simregion, dbu, port)
  
  return {  
      "polygons": parser.polygons(simregion, cell.dbbox().p1*(-1), dbu),
      "box": parser.box_from_cell(cell, 1),
      "ports": sstring_ports,
      "refpalnes": parser.refplanes(refplane_dirs, simualtion_safety),
      "symmetry": parser.symmetry(symmetry),
  }

def poly_and_edge_indeces(region, dbu, port):
  # port location
  port_loc = port.location()
    
  print("Looking for parts")
  # port polygon and edge
  for i, poly in enumerate(region.each()):
    for j, edge in enumerate(poly.each_edge()):
      if edge.to_dtype(dbu).contains(port_loc):
        print(i, j)
        return parser.port(
          ipolygon = i, 
          portnum = port.sonnet_nr, 
          ivertex = j)
  raise ValueError("No edge found for Sonnet port {}".format(port.sonnet_nr))
  return ""
