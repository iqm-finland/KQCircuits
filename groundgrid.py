import numpy
import pya

def make_grid(boundbox, avoid_region, grid_step = 10, grid_size = 5):  
  """ Generates the ground grid. 
  
  Returns a `Region` covering `boundbox` with `Box`es not overlaping with
  the avoid `Region`.
  
  All arguments are in databse unit, not in micrometers!  
  
  """
  
  grid_region = pya.Region()
  for y in numpy.arange(boundbox.p1.x, boundbox.p2.x, grid_step):
    for x in numpy.arange(boundbox.p1.y, boundbox.p2.y, grid_step): 
      hole = pya.Box(x,y,x+grid_size,y+grid_size)
      grid_region.insert(hole)
  grid_masked_region = (grid_region-avoid_region).with_area(grid_size**2,None,False)
  
  return grid_masked_region