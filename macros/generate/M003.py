import pya
import kqcircuit.macro_prepare as macroprep
from kqcircuit.pcells.chips.chip_base import produce_label 
from kqcircuit.defaults import default_layers

import glob
import os.path

from importlib import reload

reload(macroprep)
(layout, layout_view, cell_view) = macroprep.prep_empty_layout()

mask_name = "M003"
dice_width = 200
top_cell = layout.create_cell("Mask {}".format(mask_name)) # A new cell into the layout
cell_view.cell_name = top_cell.name     # Shows the new cell
with_grid = True

wafer_diam_inc = 6.
wafer_rad_um = wafer_diam_inc/2.*25400.
wafer_center = pya.DVector(wafer_rad_um-1200,-wafer_rad_um+1200)

mask_layout = [
["--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--"],
["--", "--", "--", "--", "--", "32", "32", "32", "41", "41", "--", "--", "--", "--", "--"],
["--", "--", "--", "31", "31", "32", "32", "32", "41", "41", "41", "41", "--", "--", "--"],
["--", "--", "R7", "31", "31", "31", "32", "32", "41", "41", "41", "41", "42", "--", "--"],
["--", "--", "R7", "31", "31", "31", "32", "32", "41", "41", "42", "42", "42", "--", "--"],
["--", "R7", "R7", "31", "31", "31", "32", "32", "41", "41", "42", "42", "42", "42", "--"],
["--", "R7", "R7", "31", "31", "31", "32", "32", "41", "41", "42", "42", "42", "42", "--"],
["--", "R7", "R7", "31", "31", "31", "32", "32", "41", "41", "42", "42", "42", "42", "--"],
["--", "R7", "R7", "31", "31", "31", "32", "32", "41", "41", "42", "42", "42", "42", "--"],
["--", "R7", "R7", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "R6", "--"],
["--", "--", "R7", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "X4", "--", "--"],
["--", "--", "R7", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "--", "--"],
["--", "--", "--", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "X3", "--", "--", "--"],
["--", "--", "--", "--", "--", "QD", "QD", "QD", "QD", "QD", "--", "--", "--", "--", "--"],
["--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--"],
]
#"R4","R7","R8","S1","ST","QDG"]

mask_parameters_for_chip = {
  "name_mask": mask_name,
  "name_copy": None,
  "dice_width": dice_width,
  "with_grid": with_grid,
  "r": 100,
  "lg": default_layers["Optical lit. 1"]
  }
  
# For quality factor test as on M001  
parameters_qd = {
  "res_lengths": [4649.6,4743.3,4869.9,4962.9,5050.7,5138.7,5139.,5257.,5397.4,5516.8,5626.6,5736.2,5742.9,5888.7,6058.3,6202.5,6350.,6489.4],
  "type_coupler": ["square","square","square","plate","plate","plate","square","square","square","plate","plate","plate","square","square","square","square","plate","plate"],
  "l_fingers": [19.9,54.6,6.7,9.7,22.8,30.5,26.1,14.2,18.2,10.9,19.8,26.4,34.2,19.9,25.3,8.,15.8,22.2],
  "n_fingers": [4,2,2,4,4,4,4,4,2,4,4,4,4,4,2,2,4,4]
}

# Load new cells from the files
imported = False
path_pixels_input = "/u/57/heinsoj1/unix/qcd/Johannes/Masks/M003/Pixels input"
if not 'imported' in globals() or not imported:
  for file_name in glob.glob(os.path.join(path_pixels_input,"*.gds")):
    print("Loading:",file_name)
    layout.read(file_name)
  imported = True
    
# Register the cells used on the mask
mask_map_legend = {
  "QD": layout.create_cell("Chip QFactor", "KQChip", {
          **parameters_qd,
          **mask_parameters_for_chip,
          "name_chip": "QDG",
          "n_ab": 18*[0],
          "res_term": 18*["galvanic"]
  }),    
  "R7": layout.cell("R07"),
  "X3": layout.cell("X03"),
  "X4": layout.cell("X04"),
  "31": layout.cell("X031"),
  "32": layout.cell("X032"),
  "41": layout.cell("X041"),
  "42": layout.cell("X042")
  }


# Picel placement steps on the mask
step_ver = pya.DVector(0,-1e4)
step_hor = pya.DVector(1e4,0)

text_margin = mask_map_legend["QD"].pcell_parameter("text_margin")
label_cell = layout.create_cell("ChipLabels") # A new cell into the layout
top_cell.insert(pya.DCellInstArray(label_cell.cell_index(),pya.DTrans()))

def pos_index_name(i, j):
  return chr(ord("A")+i)+("{:02d}".format(j))

def produce_label_wrap(i, j, loc, pixel_name = "", mask_name = "", company_name = ""):
  global dice_width, text_margin, default_layers
  produce_label(label_cell, pos_index_name(i, j), loc+pya.DVector(1e4, 0), "bottomright", 
                dice_width, text_margin, default_layers["Optical lit. 1"], default_layers["Grid avoidance"])
  if pixel_name:
    produce_label(label_cell, pixel_name, loc+pya.DVector(1e4, 1e4), "topright", 
                  dice_width, text_margin, default_layers["Optical lit. 1"], default_layers["Grid avoidance"])
  if mask_name:
    produce_label(label_cell, mask_name, loc+pya.DVector(0, 1e4), "topleft", 
                  dice_width, text_margin, default_layers["Optical lit. 1"], default_layers["Grid avoidance"])
  if company_name:
    produce_label(label_cell, company_name, loc+pya.DVector(0, 0), "bottomleft", 
                  dice_width, text_margin, default_layers["Optical lit. 1"], default_layers["Grid avoidance"])

dbu = layout.dbu
wafer_rad_dbu = wafer_rad_um / dbu
clip = -14.5e4
region_covered = pya.Region(
  (pya.DPolygon([
    pya.DPoint(
      wafer_center.x+math.cos(a/32*math.pi)*wafer_rad_um, 
      wafer_center.y+max(math.sin(a/32*math.pi)*wafer_rad_um,clip)
    ) 
    for a in range(0,64+1)
  ])).to_itype(dbu))

placed = 0
#for i in range(15):
#  print(i)
#  for j in range(15):
#    v = step_ver*(i+1)+step_hor*(j)

for (i, row) in enumerate(mask_layout):
  print(i)
  for (j, slot) in enumerate(row):
    v = step_ver*(i+1)+step_hor*(j)
    if ((v-step_ver*0.5+step_hor*0.5-wafer_center).length()-wafer_rad_um < -1e4): # center of the pixer 1 cm from the mask edge    
#      slot = pixel_list[placed]
#      placed += 1
      if slot in mask_map_legend.keys():
          v0 = -pya.DVector(mask_map_legend[slot].dbbox().p1)
          inst = top_cell.insert(pya.DCellInstArray(mask_map_legend[slot].cell_index(), pya.DTrans(v+v0))) 
          if inst.is_pcell():
            produce_label_wrap(i, j, v)
          else:
            produce_label_wrap(i, j, v, mask_name = mask_name, pixel_name = mask_map_legend[slot].basic_name(), company_name = "A!")
          region_covered-=pya.Region(inst.bbox())

maskextra_cell = layout.create_cell("MaskExtra") # A new cell into the layout

for layer, postfix in {"Optical lit. 1":"-1  .","Optical lit. 2":"- 2 .","Optical lit. 3":"-  3."}.items():
  cell_mask_name = layout.create_cell("TEXT", "Basic", {
    "layer": default_layers[layer], 
    "text": "QCD-"+mask_name+postfix,
    "mag": 5000.0
  })
  cell_mask_name_h = cell_mask_name.dbbox().height()
  cell_mask_name_w = cell_mask_name.dbbox().width()
  inst = maskextra_cell.insert(pya.DCellInstArray(cell_mask_name.cell_index(), pya.DTrans(wafer_center.x-cell_mask_name_w/2,-0.5e4-cell_mask_name_h/2)))
  region_covered-=pya.Region(inst.bbox()).extents(1e3/dbu)

cell_mask_outline = layout.create_cell("CIRCLE", "Basic", {
  "l": default_layers["Optical lit. 1"], 
  "r": 1.e9,
  "n": 64
})
circle = pya.DTrans(wafer_center)*pya.DPath([pya.DPoint(math.cos(a/32*math.pi)*wafer_rad_um, math.sin(a/32*math.pi)*wafer_rad_um) for a in range(0,64+1)],100)
maskextra_cell.shapes(layout.layer(default_layers["Annotations 2"])).insert(circle)

cell_marker = layout.create_cell("Marker", "KQCircuit", {"window": True})
x_min = 0
y_min = -15e4
x_max = 15e4
y_max = 0
marker_transes = [pya.DTrans(x_min+25e3, y_min+25e3)*pya.DTrans.R180,
  pya.DTrans(x_max-25e3, y_min+25e3)*pya.DTrans.R270,
  pya.DTrans(x_min+25e3, y_max-25e3)*pya.DTrans.R90,
  pya.DTrans(x_max-25e3, y_max-25e3)*pya.DTrans.R0]
for trans in marker_transes:
  inst = maskextra_cell.insert(pya.DCellInstArray(cell_marker.cell_index(), trans)) 
  region_covered-=pya.Region(inst.bbox()).extents(1e3/dbu)
  
  
maskextra_cell.shapes(layout.layer(default_layers["Optical lit. 1"])).insert(region_covered)
maskextra_cell.shapes(layout.layer(default_layers["Optical lit. 2"])).insert(region_covered)
maskextra_cell.shapes(layout.layer(default_layers["Optical lit. 3"])).insert(region_covered)

top_cell.insert(pya.DCellInstArray(maskextra_cell.cell_index(), pya.DTrans())) 

