# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# https://www.gnu.org/licenses/gpl-3.0.html.
#
# The software distribution should follow IQM trademark policy for open-source software
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


# Example XSection process description file
# Can only render 1t1 and 2b1 faces

chip_distance = 10.0 # distance between bottom chip and top chip
wafer_thickness = 100.0

# Basic options
below(2.0) # default=2.0
depth(wafer_thickness*2 + chip_distance) # default=2.0
height(10.0) # default=2.0
# Declare the basic accuracy used to remove artefacts for example:
delta(5 * dbu)

# Input layers from layout

layer_1t1_base_metal_gap = layer("130/1")
layer_1t1_SIS_junction = layer("136/1")
layer_1t1_SIS_shadow = layer("137/1")
layer_1t1_airbridge_pads = layer("146/1")
layer_1t1_airbridge_flyover = layer("147/1")
layer_1t1_underbump_metallization = layer("148/1")
layer_1t1_indium_bump = layer("149/1")

layer_2b1_base_metal_gap = layer("2/2")
layer_2b1_SIS_junction = layer("8/2")
layer_2b1_SIS_shadow = layer("9/2")
layer_2b1_airbridge_pads = layer("18/2")
layer_2b1_airbridge_flyover = layer("19/2")
layer_2b1_underbump_metallization = layer("20/2")
layer_2b1_indium_bump = layer("21/2")

# general parameters

base_metal_height = 0.2
ubm_height = 0.02


################# Bottom chip ##################

# substrate
material_1t1_substrate = bulk # creates a substrate with top edge at y=0

# XSection always creates the bulk (wafer, substrate) at the same position and it cannot be moved.
# In order to have two chips at different vertical positions, we thus have to remove the top part of
# the bottom wafer first, so that later a top chip can be created there.
etch(wafer_thickness + chip_distance, :into => material_1t1_substrate)

# deposit base metal
material_1t1_base_metal = deposit(base_metal_height)
# etch base metal
mask(layer_1t1_base_metal_gap).etch(base_metal_height, -0.1, :mode => :round, :into => [ material_1t1_base_metal, material_1t1_substrate ])

# SIS
material_1t1_SIS_shadow = mask(layer_1t1_SIS_shadow).grow(0.1, 0.1, :mode => :round)
material_1t1_SIS_junction = mask(layer_1t1_SIS_junction).grow(0.1, 0.1, :mode => :round)

# create patterned resist for airbridges
material_1t1_airbridge_resist = mask(layer_1t1_airbridge_pads.inverted).grow(3.0, -50.0, :mode => :round)
planarize(:less => 0.3, :into => material_1t1_airbridge_resist)
# deposit metal for airbridges in patterned area
material_1t1_airbridge_metal = mask(layer_1t1_airbridge_pads.or(layer_1t1_airbridge_flyover)).grow(0.3, -0.2, :mode => :round)
# remove resist for airbridges
planarize(:downto => material_1t1_substrate, :into => material_1t1_airbridge_resist)

# deposit underbump metallization
material_1t1_underbump_metallization = mask(layer_1t1_underbump_metallization).grow(ubm_height, -0.1, :mode => :round)
# deposit indium bumps
material_1t1_indium_bump = mask(layer_1t1_indium_bump).grow(chip_distance/2 - ubm_height - base_metal_height, 0.1, :mode => :round)

# output the material data for bottom chip to the target layout
output("1t1_substrate", material_1t1_substrate)
output("1t1_base_metal", material_1t1_base_metal)
output("1t1_SIS_junction", material_1t1_SIS_junction)
output("1t1_SIS_shadow", material_1t1_SIS_shadow)
output("1t1_airbridge_resist", material_1t1_airbridge_resist)
output("1t1_airbridge_metal", material_1t1_airbridge_metal)
output("1t1_underbump_metallization", material_1t1_underbump_metallization)
output("1t1_indium_bump", material_1t1_indium_bump)

################# Top chip ##################

material_2b1_substrate = bulk # this creates a new substrate with top edge at y=0
flip()

# Remove the part of top chip substrate which is within bottom chip area (see earlier comment for bottom chip).
etch(wafer_thickness + chip_distance, :into => material_2b1_substrate)

# deposit base metal
material_2b1_base_metal = deposit(base_metal_height)
# etch base metal
mask(layer_2b1_base_metal_gap).etch(base_metal_height, -0.1, :mode => :round, :into => [ material_2b1_base_metal, material_2b1_substrate ])

# deposit underbump metallization
material_2b1_underbump_metallization = mask(layer_2b1_underbump_metallization).grow(ubm_height, -0.1, :mode => :round)
# deposit indium bumps
material_2b1_indium_bump = mask(layer_2b1_indium_bump).grow(chip_distance/2 - ubm_height - base_metal_height, 0.1, :mode => :round)

# output the material data for top chip to the target layout
output("2b1_substrate", material_2b1_substrate)
output("2b1_base_metal", material_2b1_base_metal)
output("2b1_underbump_metallization", material_2b1_underbump_metallization)
output("2b1_indium_bump", material_2b1_indium_bump)
