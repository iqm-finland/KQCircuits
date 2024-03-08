# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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

# XSection process description file for KQC fabrication process

sim_layers = Hash.new

# parameters that can be sweeped

face_stack = []
substrate_height = []
ground_metal_height = 0.2
signal_metal_height = 0.2
airbridge_height = 3.4
vertical_over_etching = 0.0
ubm_height = 0.02
upper_box_height = 1000.0
lower_box_height = 0.0
chip_distance = []

# To allow sweeping for some parameters in this process description file for simulations,
# read such parameter values from an external file under $xs_params.
# This file also contains simulation layer information.

if File.exists? $xs_params
  require 'json'
  sweep_file_content = nil
  File.open($xs_params) do |file|
    sweep_file_content = file.read
  end
  if !!sweep_file_content
    sweep_parameters = JSON.parse(sweep_file_content)
    sweep_parameters.each do |param_name, param_value|
      # Only set variables that were introduced previously (for safety)
      if local_variables.include? param_name.to_sym
        if param_name == "sim_layers"
          sim_layers = param_value # Hash of simulation layers always expected
        else
          eval("#{param_name} = #{param_value}")
        end
      end
    end
  end
end

if face_stack.length() == 2
  is_flip_chip = true
elsif face_stack.length() == 1
  is_flip_chip = false
else
  raise "face_stack list has #{face_stack.length()} elements. Only 1- or 2-face cross-sections are supported"
end

_cd = chip_distance[0] + ground_metal_height * 2
# Basic options
if is_flip_chip
  depth(substrate_height[0] + _cd + substrate_height[1])
else
  depth(substrate_height[0])
end
# Declare the basic accuracy used to remove artefacts for example:
delta(5 * dbu)

# Input layers from layout

layer_b_gap = layer(sim_layers['b_gap'])
layer_b_ground = layer(sim_layers['b_ground'])
layer_b_signal = layer(sim_layers['b_signal'])
layer_b_SIS_junction = layer(sim_layers['b_SIS_junction'])
layer_b_SIS_shadow = layer(sim_layers['b_SIS_shadow'])
layer_b_airbridge_pads = layer(sim_layers['b_airbridge_pads'])
layer_b_airbridge_flyover = layer(sim_layers['b_airbridge_flyover'])
layer_b_underbump_metallization = layer(sim_layers['b_underbump_metallization'])
layer_b_indium_bump = layer(sim_layers['b_indium_bump'])

layer_t_gap = layer(sim_layers['t_gap'])
layer_t_ground = layer(sim_layers['t_ground'])
layer_t_signal = layer(sim_layers['t_signal'])
layer_t_SIS_junction = layer(sim_layers['t_SIS_junction'])
layer_t_SIS_shadow = layer(sim_layers['t_SIS_shadow'])
layer_t_airbridge_pads = layer(sim_layers['t_airbridge_pads'])
layer_t_airbridge_flyover = layer(sim_layers['t_airbridge_flyover'])
layer_t_underbump_metallization = layer(sim_layers['t_underbump_metallization'])
layer_t_indium_bump = layer(sim_layers['t_indium_bump'])


################# Bottom chip ##################

# substrate
material_b_substrate = bulk # creates a substrate with top edge at y=0

# XSection always creates the bulk (wafer, substrate) at the same position and it cannot be moved.
# In order to have two chips at different vertical positions, we thus have to remove the top part of
# the bottom wafer first, so that later a top chip can be created there.
if is_flip_chip
  etch(_cd + substrate_height[1], :into => material_b_substrate)
end

# deposit base metal
material_b_ground = mask(layer_b_ground).grow(ground_metal_height)
material_b_signal = mask(layer_b_signal).grow(signal_metal_height)
signal_materials = Hash.new
sim_layers.each do |layer_name, layer_id|
  if layer_name.start_with? "b_signal"
    signal_materials["#{layer_name}(#{layer_id})"] = mask(layer(layer_id)).grow(signal_metal_height)
  end
end
etched_materials = [ material_b_ground, material_b_signal, material_b_substrate ] + signal_materials.values

# etch substrate (gap layer already positive geometry for simulation layers)
mask(layer_b_gap).etch(vertical_over_etching, :into => etched_materials)

# SIS
material_b_SIS_shadow = mask(layer_b_SIS_shadow).grow(0.1, 0.1, :mode => :round)
material_b_SIS_junction = mask(layer_b_SIS_junction).grow(0.1, 0.1, :mode => :round)

# create patterned resist for airbridges
material_b_airbridge_resist = mask(layer_b_airbridge_pads.inverted).grow(airbridge_height, -50.0, :mode => :round)
planarize(:less => 0.3, :into => material_b_airbridge_resist)
# deposit metal for airbridges in patterned area
material_b_airbridge_metal = mask(layer_b_airbridge_pads.or(layer_b_airbridge_flyover)).grow(0.3, -0.2, :mode => :round)
# remove resist for airbridges
planarize(:downto => material_b_substrate, :into => material_b_airbridge_resist)

# deposit underbump metallization
material_b_underbump_metallization = mask(layer_b_underbump_metallization).grow(ubm_height, -0.1, :mode => :round)
# deposit indium bumps
material_b_indium_bump = mask(layer_b_indium_bump).grow(_cd / 2 - ubm_height - ground_metal_height, 0.1, :mode => :round)

# output the material data for bottom chip to the target layout
output("b_substrate(#{sim_layers['b_substrate']})", material_b_substrate)
output("b_ground(#{sim_layers['b_ground']})", material_b_ground)
output("b_signal(#{sim_layers['b_signal']})", material_b_signal)
signal_materials.each do |layer_name, material|
  output(layer_name, material)
end
output("b_SIS_junction(#{sim_layers['b_SIS_junction']})", material_b_SIS_junction)
output("b_SIS_shadow(#{sim_layers['b_SIS_shadow']})", material_b_SIS_shadow)
# TODO: fix airbridge cross-sections with non-zero vertical_over_etching
#output("b_airbridge_resist(#{sim_layers['b_airbridge_resist']})", material_b_airbridge_resist)
output("b_airbridge_metal(#{sim_layers['b_airbridge_metal']})", material_b_airbridge_metal)
output("b_underbump_metallization(#{sim_layers['b_underbump_metallization']})", material_b_underbump_metallization)
output("b_indium_bump(#{sim_layers['b_indium_bump']})", material_b_indium_bump)

################# Top chip ##################

if is_flip_chip
  material_t_substrate = bulk # this creates a new substrate with top edge at y=0
  flip()

  # Remove the part of top chip substrate which is within bottom chip area (see earlier comment for bottom chip).
  etch(substrate_height[0] + _cd, :into => material_t_substrate)

  # deposit base metal
  material_t_ground = mask(layer_t_ground).grow(ground_metal_height)
  material_t_signal = mask(layer_t_signal).grow(signal_metal_height)
  signal_materials = Hash.new
  sim_layers.each do |layer_name, layer_id|
    if layer_name.start_with? "t_signal"
      signal_materials["#{layer_name}(#{layer_id})"] = mask(layer(layer_id)).grow(signal_metal_height)
    end
  end
  etched_materials = [ material_b_ground, material_b_signal, material_b_substrate ] + signal_materials.values

  # etch substrate
  mask(layer_t_gap).etch(vertical_over_etching, :into => [ material_t_ground, material_t_signal, material_t_substrate ])

  # deposit underbump metallization
  material_t_underbump_metallization = mask(layer_t_underbump_metallization).grow(ubm_height, -0.1, :mode => :round)
  # deposit indium bumps
  material_t_indium_bump = mask(layer_t_indium_bump).grow(_cd / 2 - ubm_height - ground_metal_height, 0.1, :mode => :round)

  # output the material data for top chip to the target layout
  output("t_substrate(#{sim_layers['t_substrate']})", material_t_substrate)
  output("t_ground(#{sim_layers['t_ground']})", material_t_ground)
  output("t_signal(#{sim_layers['t_signal']})", material_t_signal)
  signal_materials.each do |layer_name, material|
    output(layer_name, material)
  end
  output("t_underbump_metallization(#{sim_layers['t_underbump_metallization']})", material_t_underbump_metallization)
  output("t_indium_bump(#{sim_layers['t_indium_bump']})", material_t_indium_bump)
end
