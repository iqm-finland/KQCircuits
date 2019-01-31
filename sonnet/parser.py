import pya

def polygon_head(
      nvertices,# number of vertices of the polygon
      debugid, # unique number for sonnet internal debugging 
      ilevel= 0, # sonnet layer number
      mtype= -1, # metallization type index, -1 for lossless
      filltype="N", # N for staircase, T for diagonal, V for conformal
      xmin= 1, # minimum subsection size
      ymin= 1, # minimum subsection size
      xmax= 100, # maximum subsection size
      ymax= 100, # maximum subsection size
      conmax= 0, # maximum length for conformal mesh subsection, 0 for auto
      res= 0, # reserved for sonnet future
      edge_mesh= "Y" # edge mesh on (Y) or off (N)
    ):
  
  return "{ilevel} {nvertices} {mtype} {filltype} {debugid} {xmin} {ymin} {xmax} {ymax} {conmax} {res} {res} {edge_mesh}\n".format(**locals())

def box(cell: pya.Cell, cell_size):
  bbox = cell.dbbox()  
  
  return box(
    xwidth = bbox.width,
    ywidth = bbox.height,
    xcells = int(bbox.width/cells_size),
  )

def box(
      nlev : int = 1, # number of sonnet levels
      xwidth : float = 8000.,
      ywidth : float = 8000.,
      xcells : int = 8000,
      ycells : int = 8000
    ):

  xcells2 = 2*xcells
  ycells2 = 2*ycells
  nsubs = 20, # placeholder for depricated parameter
  eeff = 0, # placeholder for depricated parameter
  
  return "BOX {nlev} {xwidth} {ywidth} {xcells2} {ycells2} {nsubs} {eeff}\n3000 1 1 0 0 0 0 \"vacuum\"\n500 11.7 1 0 0 0 0 \"Silicon (intrinsic)\"".format(**locals())

def refplane(
    position : str, # "LEFT" | "RIGHT" | "TOP" | "BOTTOM",
    length : int = 0
  ):
  return "DRP1 {position} FIX {length}".format(**locals())
  
  
def refplanes(postitions, length):  
  sonnet_str = ""
  for side in postitions:
    sonnet_str = refplane(side, length)
  return sonnet_str 

  
def port(
    portnum,
    ipolygon,
    ivertex,
    port_type = "STD", # STD for standard | AGND autogrounded | CUP cocalibrated
    xcord = 0,
    ycord = 0
  ):
  return "POR1 {port_type}\nPOLY {ipolygon} 1\n{ivertex}\n{portnum} 50 0 0 0".format(**locals()) # {xcord} {ycord} [reftype rpcallen]

def ports(shapes):
  sonnet_str = ""
  polygons = 0
  
  # FIXME Maybe the shapes will not have the same indexes as polygons in the region!
  for shape in shapes.each():
    if shape:
      polygons += 1
      ivertex = shape.property("sonnet_port_edge")
      portnum = shape.property("sonnet_port_nr")
      if ivertex and portnum:
        sonnet_str += port(ipolygon=polygons, portnum=portnum, ivertex=ivertex)
  
  return sonnet_str


def polygons(shapes, dbu=1):
  
  reg = pya.Region(shapes)
  
  
  # v = pya.Vector(-bbox.p1.x, -bbox.p1.y) # TODO
  
  #cell.shapes(0).insert(reg)
  
  sonnet_str = 'NUM {}\n'.format(len([p for p in reg.each()]))
  for i, shape in enumerate(shapes.each()):
    if shape.is_polygon:
      poly = shape.dpolygon
      if poly.holes():
        raise NotImplementedError    
      sonnet_str += polygon_head(nvertices=poly.num_points_hull()+1, debugid=i)
      for j, point in enumerate(poly.each_point_hull()):
        sonnet_str += "{} {}\n".format(point.x, point.y)
      point = next(poly.each_point_hull()) # first point again to close the polygon
      sonnet_str += "{} {}\n".format(point.x, point.y)
    
  return sonnet_str