# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


import abc
import ast
from typing import List

from autologging import logged

from kqcircuits.defaults import default_faces
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.port import Port, InternalPort, EdgePort
from kqcircuits.util.geometry_helper import region_with_merged_polygons, region_with_merged_points
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.simulations.export.util import find_edge_from_point_in_cell
from kqcircuits.simulations.export.util import get_enclosing_polygon
from kqcircuits.util.groundgrid import make_grid
from kqcircuits.junctions.sim import Sim


simulation_layer_dict = dict()


def get_simulation_layer_by_name(layer_name):
    """Returns layer info of given name. If layer doesn't exist, a new layer is created.
    New layers are created with data type = 0 and layer numbering starts from 1000."""
    if layer_name not in simulation_layer_dict:
        simulation_layer_dict[layer_name] = pya.LayerInfo(len(simulation_layer_dict) + 1000, 0, layer_name)
    return simulation_layer_dict[layer_name]


@logged
@add_parameters_from(Element)
@add_parameters_from(Sim, "junction_total_length")
class Simulation:
    """Base class for simulation geometries.

    Generally, this class is intended to be subclassed by a specific simulation implementation; the
    implementation defines the simulation geometry ad ports in `build`.

    A convenience class method `Simulation.from_cell` is provided to create a Simulation from an
    existing cell. In this case no ports will be added.

    Basically, 3D layout is built of substrates, which are separated from each other by vacuum boxes, however, this rule
    is modifiable by setting substrate and vacuum thicknesses to zero. In principle, one can stack faces on any of the
    imaginable surface of a substrate. If substrate or vacuum thickness is set to zero, then there can be two
    faces touching each other. Faces can be stacked on bottom or top surface of the substrates.

    Number of substrate and vacuum boxes are determined with parameters face_stack and lower_box_height:
    - If lower_box_height > 0, there will be a vacuum box below the lowest substrate, and the counting of faces will
    start from the bottom surface of the lowest substrate. Otherwise, the lowest substrate will be below the lowest
    vacuum box, and the counting of faces will start from the top surface of the lowest substrate.
    - Length of face_stack list describes how many surfaces are taken into account in the simulation.

    The terms in the face_stack indicate in which order the klayout faces are stacked in the 3D layout. Faces are
    counted from the lowest substrate surface to the highest. One can also introduce face_stack as list of lists.
    If a term in face_stack is a list, then all the faces given in the list are piled up on the corresponding surface
    in the respective order. That means, the first term in the inner list indicates the face that is closest to the
    surface of the substrate. One can use empty list in face_stack to leave certain surface
    without metallization.

    Heights of substrates (substrate_height) and vacuum boxes between surfaces (chip_distance) can be determined
    individually from bottom to top or with single value. Any of the heights can be left zero, to indicate that there
    is no vacuum between the substrates or substrate between the vacuum boxes. Also, the metal thickness (metal_height)
    can be set to zero, but that means the metal layer is modelled as infinitely thin sheet. The insulator dielectric
    can be set on any metal layer if non-zero dielectric_height is given.
    """
    # The samples below show, how the layout is changed according to the parameters. Number of faces is unlimited:
    #
    # len(face_stack) = 1             len(face_stack) = 2             len(face_stack) = 2
    # lower_box_height = 0            lower_box_height = 0            lower_box_height > 0
    # |-------------------------|     |-------------------------|     |-------------------------|
    # |                         |     |/////////////////////////|     |                         |
    # |                         |     |///substrate_height[1]///|     |    upper_box_height     |
    # |    upper_box_height     |     |/////////////////////////|     |                         |
    # |                         |     |----- face_stack[1] -----|     |----- face_stack[1] -----|
    # |                         |     |                         |     |/////////////////////////|
    # |----- face_stack[0] -----|     |    chip_distance[0]     |     |///substrate_height[0]///|
    # |/////////////////////////|     |                         |     |/////////////////////////|
    # |/////////////////////////|     |----- face_stack[0] -----|     |----- face_stack[0] -----|
    # |///substrate_height[0]///|     |/////////////////////////|     |                         |
    # |/////////////////////////|     |///substrate_height[0]///|     |    lower_box_height     |
    # |/////////////////////////|     |/////////////////////////|     |                         |
    # |-------------------------|     |-------------------------|     |-------------------------|

    LIBRARY_NAME = None  # This is needed by some methods inherited from Element.

    # Metadata associated with simulation
    ports: List[Port]

    # Parameters
    box = Param(pdt.TypeShape, "Boundary box", pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000)))
    ground_grid_box = Param(pdt.TypeShape, "Border", pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000)))
    with_grid = Param(pdt.TypeBoolean, "Make ground plane grid", False)
    name = Param(pdt.TypeString, "Name of the simulation", "Simulation")

    use_ports = Param(pdt.TypeBoolean, "Turn off to disable all ports (for debugging)", True)
    use_internal_ports = Param(pdt.TypeBoolean, "Use internal (lumped) ports. The alternative is wave ports.", True)
    port_size = Param(pdt.TypeDouble, "Width and height of wave ports", 400.0, unit="µm")

    upper_box_height = Param(pdt.TypeDouble, "Height of vacuum above top substrate", 1000.0, unit="µm")
    lower_box_height = Param(pdt.TypeDouble, "Height of vacuum below bottom substrate", 0, unit="µm",
                             docstring="Set > 0 to start face counting from substrate bottom layer.")
    face_stack = Param(pdt.TypeList, "Face IDs on the substrate surfaces from bottom to top", ["1t1"],
                       docstring="The parameter can be set as list of lists to enable multi-face stack-up on substrate "
                                 "surfaces. Set term to empty list to not have metal on the surface.")
    substrate_height = Param(pdt.TypeList, "Height of the substrates", [550.0, 375.0], unit="[µm]",
                             docstring="The value can be scalar or list of scalars. Set as list to use individual "
                                       "substrate heights from bottom to top.")
    substrate_material = Param(pdt.TypeList, "Material of the substrates.", ['silicon'],
                               docstring="Value can be string or list of strings. Use only keywords introduced in "
                                         "material_dict. Set as list to use individual materials from bottom to top.")
    material_dict = Param(pdt.TypeString, "Dictionary of dielectric materials", "{'silicon': {'permittivity': 11.45}}",
                          docstring="Material property keywords follow Ansys Electromagnetics property names. "
                                    "For example 'permittivity', 'dielectric_loss_tangent', etc.")
    chip_distance = Param(pdt.TypeList, "Height of vacuum between two substrates", [8.0], unit="[µm]",
                          docstring="The value can be scalar or list of scalars. Set as list to use individual chip "
                                    "distances from bottom to top.")
    ground_metal_height = Param(pdt.TypeDouble, "Height of the grounded metal (in Xsection tool)", 0.2, unit="µm",
                                docstring="Only used in Xsection tool and doesn't affect the 3D model")
    signal_metal_height = Param(pdt.TypeDouble, "Height of the trace metal (in Xsection tool)", 0.2, unit="µm",
                                docstring="Only used in Xsection tool and doesn't affect the 3D model")

    airbridge_height = Param(pdt.TypeDouble, "Height of airbridges.", 3.4, unit="µm")
    metal_height = Param(pdt.TypeList, "Height of metal sheet on each face.", [0.0], unit="µm")
    dielectric_height = Param(pdt.TypeList, "Height of insulator dielectric on each face.", [0.0], unit="µm")
    dielectric_material = Param(pdt.TypeList, "Material of insulator dielectric on each face.", ['silicon'], unit="µm")

    waveguide_length = Param(pdt.TypeDouble, "Length of waveguide stubs or distance between couplers and waveguide "
                                             "turning point", 100, unit="µm")
    over_etching = Param(pdt.TypeDouble, "Expansion of metal gaps (negative to shrink the gaps).", 0, unit="μm")
    vertical_over_etching = Param(pdt.TypeDouble, "Vertical over-etching into substrates at gaps.", 0, unit="μm")
    hollow_tsv = Param(pdt.TypeBoolean, "Make TSVs hollow with vacuum inside and thin metal boundary.", False)

    participation_sheet_distance = Param(pdt.TypeDouble, "Distance to non-model TLS interface sheet.", 0.0, unit="µm")
    participation_sheet_thickness = Param(pdt.TypeDouble, "Thickness of non-model TLS interface sheet.", 0.0, unit="µm")

    minimum_point_spacing = Param(pdt.TypeDouble, "Tolerance for merging adjacent points in polygon", 0.01, unit="µm")
    polygon_tolerance = Param(pdt.TypeDouble, "Tolerance for merging adjacent polygons in a layer", 0.004, unit="µm")

    extra_json_data = Param(pdt.TypeNone, "Extra data in dict form to store in resulting JSON", None,
        docstring="This field may be used to store 'virtual' parameters useful for your simulations")

    def __init__(self, layout, **kwargs):
        """Initialize a Simulation.

        The initializer parses parameters, creates a top cell, and then calls `self.build` to create
        the simulation geometry, followed by `self.create_simulation_layers` to process the geometry
        so it is ready for exporting.

        Args:
            layout: the layout on which to create the simulation

        Keyword arguments:
            `**kwargs`:
                Any parameter can be passed as a keyword argument.

                In addition, `cell` can be passed as keyword argument. If `cell` is supplied, it will be
                used as the top cell for the simulation. Otherwise, a new cell will be created. See
                `Simulation.from_cell` for creating simulations from existing cells.
        """
        self.refpoints = {}
        if layout is None or not isinstance(layout, pya.Layout):
            error_text = "Cannot create simulation with invalid or nil layout."
            error = ValueError(error_text)
            self.__log.exception(error_text, exc_info=error)
            raise error

        self.layout = layout
        schema = type(self).get_schema()

        # Apply kwargs or default value
        # TODO: Validation? Could reuse the validation for Element
        for parameter, item in schema.items():
            if parameter in kwargs:
                setattr(self, parameter, kwargs[parameter])
            else:
                setattr(self, parameter, item.default)

        self.name = self.name.replace(" ", "").replace(",", "__")  # no spaces or commas in filenames

        self.ports = []
        if 'cell' in kwargs:
            self.cell = kwargs['cell']
        else:
            self.cell = layout.create_cell(self.name)

        self.layers = dict()
        self.build()
        self.create_simulation_layers()

    @classmethod
    def from_cell(cls, cell, margin=300, grid_size=1, **kwargs):
        """Create a Simulation from an existing cell.

        Arguments:
            cell: existing top cell for the Simulation
            margin: distance (μm) to expand the simulation box (ground plane) around the bounding
                box of the cell If the `box` keyword argument is given, margin is ignored.
            grid_size: size of the simulation box will be rounded to this resolution
                If the `box` keyword argument is given, grid_size is ignored.
            `**kwargs`: any simulation parameters passed

        Returns:
            Simulation instance
        """
        extra_kwargs = {}

        if 'box' not in kwargs:
            box = cell.dbbox().enlarge(margin, margin)
            if grid_size > 0:
                box.left = round(box.left / grid_size) * grid_size
                box.right = round(box.right / grid_size) * grid_size
                box.bottom = round(box.bottom / grid_size) * grid_size
                box.top = round(box.top / grid_size) * grid_size
            extra_kwargs['box'] = box

        return cls(cell.layout(), cell=cell, **kwargs, **extra_kwargs)

    @abc.abstractmethod
    def build(self):
        """Build simulation geometry.

        This method is to be overridden, and the overriding method should create the geometry to be
        simulated and add any ports to `self.ports`.
        """
        return

    # Inherit specific methods from Element
    get_schema = classmethod(Element.get_schema.__func__)
    face = Element.face
    insert_cell = Element.insert_cell
    get_refpoints = Element.get_refpoints
    add_element = Element.add_element
    get_layer = Element.get_layer
    pcell_params_by_name = Element.pcell_params_by_name

    def face_stack_list_of_lists(self):
        """Return self.face_stack forced to be list of lists"""
        return [f if isinstance(f, list) else [f] for f in self.face_stack]

    @staticmethod
    def ith_value(list_or_constant, i):
        """ Helper function to return value from list or constant corresponding to the ordinal number i.
        Too short lists are extended by duplicating the last value of the list.
        """
        if isinstance(list_or_constant, list):
            if i < len(list_or_constant):
                return list_or_constant[i]  # return ith term of the list
            return list_or_constant[-1]  # return last term of the list
        return list_or_constant  # return constant value

    def face_z_levels(self):
        """ Returns dictionary of z-levels. The dictionary can be used either with integer or string key values: Integer
        keys return surface z-levels in ascending order (including domain boundary bottom and top). String keys
        (key = face_id) return the three z-levels of the face (metal bottom, metal-dielectric interface, dielectric top)

        The level z=0 is at lowest substrate top.
        """
        # Terms below z=0 level
        substrate_bottom = -float(self.ith_value(self.substrate_height, 0))
        z_levels = [substrate_bottom - self.lower_box_height] if self.lower_box_height > 0 else []
        z_levels += [substrate_bottom, 0.0]

        # Terms above z=0 level
        remaining_substrates = (len(self.face_stack) + 2 - len(z_levels)) // 2
        for s in range(remaining_substrates):
            z_levels.append(z_levels[-1] + float(self.ith_value(self.chip_distance, s)))
            z_levels.append(z_levels[-1] + float(self.ith_value(self.substrate_height, s + 1)))
        if len(z_levels) < len(self.face_stack) + 2:
            z_levels.append(z_levels[-1] + self.upper_box_height)

        # Create dictionary of z-levels including integer keys and face_id keys
        z_dict = dict(enumerate(z_levels))
        z_dict[-1] = z_levels[-1]
        for i, face_ids in enumerate(self.face_stack_list_of_lists()):
            sign = (-1) ** (i + int(self.lower_box_height > 0))
            base_z = z_levels[i + 1]
            metal_height = self.ith_value(self.metal_height, i)
            dielectric_height = self.ith_value(self.dielectric_height, i)
            for j, face_id in enumerate(face_ids):
                metal_z = base_z + sign * float(self.ith_value(metal_height, j))
                dielectric_z = metal_z + sign * float(self.ith_value(dielectric_height, j))
                z_dict[face_id] = [base_z, metal_z, dielectric_z]
                base_z = dielectric_z
        return z_dict

    def merged_region_from_layer(self, face_id, layer_name, expansion=0.0):
        """ Returns a `Region` containing all geometry from a specified layer merged together """
        face_layers = default_faces[face_id] if face_id in default_faces else dict()
        if layer_name in face_layers:
            return region_with_merged_polygons(
                pya.Region(self.cell.begin_shapes_rec(self.layout.layer(face_layers[layer_name]))),
                tolerance=self.polygon_tolerance / self.layout.dbu, expansion=expansion / self.layout.dbu)
        return pya.Region()

    def insert_layer(self, region, layer_name, **params):
        """Merges points in the `region` and inserts the result in a target layer. The params are forwarded to the
        'self.layers' dictionary.
        """
        if region.is_empty():
            return  # ignore the layer
        layer = get_simulation_layer_by_name(layer_name)
        self.cell.shapes(self.layout.layer(layer)).insert(region)
        self.layers[layer_name] = {'layer': layer.layer, **params}

    @staticmethod
    def add_layer_to_splitter(splitter, region, layer_name, **params):
        """Add layer to the splitter, which splits the region into different z-levels. The params are forwarded to
        the 'self.layers' dictionary.

        Before calling first time, the splitter should be set as empty splitter, which is a list of empty dictionary and
        empty list, that is [dict(), []].
        """
        if region.is_empty():
            return  # ignore the layer

        # the first term in splitter is dictionary of parameters
        splitter[0][layer_name] = params

        # the second term in splitter is list of tuples containing (reg, list of keys)
        region_and_keys = []
        left_region = region.dup()
        for reg, keys in splitter[1]:
            intersection = reg & region
            if not intersection.is_empty():
                left_region -= intersection
                subtraction = reg - intersection
                if not subtraction.is_empty():
                    region_and_keys.append((subtraction, keys))
                region_and_keys.append((intersection, keys + [layer_name]))
            else:
                region_and_keys.append((reg, keys))
        if not left_region.is_empty():
            region_and_keys.append((left_region, [layer_name]))
        splitter[1] = region_and_keys

    def insert_splitter_layers(self, splitter, z0):
        """Inserts the layers in the splitter to the 'self.layers' dictionary. Each layer are split into sub-layers
        by their z-level. Parameter 'z0' is the base z-level for layer stack-up."""
        for key, params in splitter[0].items():
            z_region_map = dict()
            for reg, keys in splitter[1]:
                if key in keys:
                    # round z-value to avoid differences due to floating point number inaccuracy
                    z = round(sum(splitter[0][i].get('thickness', 0.0) for i in keys[0: keys.index(key)]), 12)
                    if z not in z_region_map:
                        z_region_map[z] = pya.Region()
                    z_region_map[z] += reg

            # Insert combined region if there are multiple levels
            if len(z_region_map) > 1:
                region = pya.Region()
                for reg in z_region_map.values():
                    region += reg
                self.cell.shapes(self.layout.layer(get_simulation_layer_by_name(key))).insert(region.merged())

            # Insert split parts of the region and add layer
            for i, (z, reg) in enumerate(z_region_map.items()):
                layer_name = key + f'_{i}' if len(z_region_map) > 1 else key
                layer = get_simulation_layer_by_name(layer_name)
                self.cell.shapes(self.layout.layer(layer)).insert(reg.merged())
                self.layers[layer_name] = {'layer': layer.layer, 'z': z0 + z, **params}

    def insert_layers_between_faces(self, i, opp_i, layer_name, **params):
        """Helper function to be used to produce indium bumps and TSVs"""
        z = self.face_z_levels()
        mps = self.minimum_point_spacing / self.layout.dbu
        face_stack = self.face_stack_list_of_lists()
        box_region = pya.Region(self.box.to_itype(self.layout.dbu))
        sum_region = pya.Region()
        for face_id in face_stack[i]:
            region = region_with_merged_points(self.merged_region_from_layer(face_id, layer_name) & box_region, mps)
            if region.is_empty():
                continue
            sum_region += region
            if 0 <= opp_i < len(face_stack):
                for opp_id in face_stack[opp_i]:
                    common_region = region & region_with_merged_points(
                        self.merged_region_from_layer(opp_id, layer_name) & box_region, mps)
                    if common_region.is_empty():
                        continue
                    if f'{opp_id}_{face_id}_{layer_name}' not in self.layers:  # if statement is to avoid duplicates
                        self.insert_layer(common_region, f'{face_id}_{opp_id}_{layer_name}', z=z[face_id][1],
                                          thickness=z[opp_id][1] - z[face_id][1], **params)
                    region -= common_region
                    if region.is_empty():
                        break
            if not region.is_empty():
                self.insert_layer(region, face_id + '_' + layer_name, z=z[face_id][1],
                                  thickness=z[opp_i + 1] - z[face_id][1], **params)
        return sum_region

    def create_simulation_layers(self):
        """Create the layers used for simulation export.

        Based on any geometry defined on the relevant lithography layers.

        This method is called from `__init__` after `build`, and should not be called directly.

        Geometry is added to layers created specifically for simulation purposes. The layer numbers, z-levels,
        thicknesses, materials, and other properties are stored in 'self.layers' parameter.

        In the simulation-specific layers, all geometry has been merged and converted to simple polygons, that is,
        polygons without holes.
        """

        z = self.face_z_levels()
        mps = self.minimum_point_spacing / self.layout.dbu
        face_stack = self.face_stack_list_of_lists()
        for i, face_ids in enumerate(face_stack):
            sign = (-1) ** (i + int(self.lower_box_height > 0))
            splitter = [dict(), []]
            dielectric_material = self.ith_value(self.dielectric_material, i)

            # insert TSVs and indium bumps
            tsv_params = {'edge_material': 'pec'} if self.hollow_tsv else {'material': 'pec'}
            tsv_region = self.insert_layers_between_faces(i, i - sign, "through_silicon_via", **tsv_params)
            self.insert_layers_between_faces(i, i + sign, "indium_bump", material='pec')

            for j, face_id in enumerate(face_ids):
                ground_box_region = pya.Region(self.box.to_itype(self.layout.dbu))
                metal_gap_region = self.merged_region_from_layer(face_id, "base_metal_gap_wo_grid", self.over_etching)
                metal_add_region = self.merged_region_from_layer(face_id, "base_metal_addition", -self.over_etching)
                lithography_region = metal_gap_region - metal_add_region

                if lithography_region.is_empty():
                    signal_region = pya.Region()
                    ground_region = ground_box_region.dup()
                else:
                    signal_region = ground_box_region - lithography_region

                    # Find the ground plane and subtract it from the simulation area
                    # First, add all polygons touching any of the edges
                    ground_region = pya.Region()
                    for edge in ground_box_region.edges():
                        ground_region += signal_region.interacting(edge)
                    # Now, remove all edge polygons which are also a port
                    if self.use_ports:
                        for port in self.ports:
                            if self.face_ids[port.face] == face_id:
                                if hasattr(port, 'ground_location'):
                                    v_unit = port.signal_location-port.ground_location
                                    v_unit = v_unit/v_unit.abs()
                                    signal_loc = (port.signal_location+mps*v_unit).to_itype(self.layout.dbu)
                                    ground_region -= ground_region.interacting(pya.Edge(signal_loc, signal_loc))

                                    ground_loc = (port.ground_location-mps*v_unit).to_itype(self.layout.dbu)
                                    ground_region += signal_region.interacting(pya.Edge(ground_loc, ground_loc))
                                else:
                                    signal_loc = port.signal_location.to_itype(self.layout.dbu)
                                    ground_region -= ground_region.interacting(pya.Edge(signal_loc, signal_loc))

                    ground_region.merge()
                    signal_region -= ground_region

                dielectric_region = ground_box_region - self.merged_region_from_layer(face_id, "dielectric_etch")

                # Merge points of each region to optimize the simulations. Subtract TSV region.
                signal_region = region_with_merged_points(signal_region, mps) - tsv_region
                ground_region = region_with_merged_points(ground_region, mps) - tsv_region
                dielectric_region = region_with_merged_points(dielectric_region, mps) - tsv_region
                gap_region = ground_box_region - signal_region - ground_region
                if self.with_grid:
                    ground_region -= self.ground_grid_region(face_id)

                # Insert signal, ground, and dielectric layers to model via splitter
                if j == 0 and self.vertical_over_etching > 0.0:
                    self.add_layer_to_splitter(splitter, ground_box_region - signal_region - ground_region,
                                               face_id + "_etch", thickness=-sign * self.vertical_over_etching)

                metal_thickness = z[face_id][1] - z[face_id][0]
                self.add_layer_to_splitter(splitter, signal_region, face_id + "_signal", thickness=metal_thickness,
                                           material='pec')
                self.add_layer_to_splitter(splitter, ground_region, face_id + "_ground", thickness=metal_thickness,
                                           material='pec')
                dielectric_thickness = z[face_id][2] - z[face_id][1]
                if dielectric_thickness != 0.0:
                    self.add_layer_to_splitter(splitter, dielectric_region, face_id + "_dielectric",
                                               thickness=dielectric_thickness,
                                               material=self.ith_value(dielectric_material, j))

                # Insert gap layer only on the first face of the stack-up (no material)
                if j == 0:
                    gap_z = z[face_id][0] - sign * self.vertical_over_etching
                    self.insert_layer(gap_region, face_id + "_gap", z=gap_z, thickness=z[face_id][1] - gap_z)

                # Insert airbridges
                bridge_z = sign * self.airbridge_height
                self.insert_layer(self.merged_region_from_layer(face_id, "airbridge_flyover") & ground_box_region,
                                  face_id + "_airbridge_flyover", z=z[face_id][1] + bridge_z, thickness=0.0,
                                  material='pec')
                self.insert_layer(self.merged_region_from_layer(face_id, "airbridge_pads") & ground_box_region,
                                  face_id + "_airbridge_pads", z=z[face_id][1], thickness=bridge_z, material='pec')

                # Insert participation layers (no material)
                if j == 0 and self.participation_sheet_distance + self.participation_sheet_thickness > 0.0:
                    self.insert_layer(signal_region + ground_region, face_id + "_layerMA",
                                      z=z[face_id][1] + sign * self.participation_sheet_distance,
                                      thickness=sign * self.participation_sheet_thickness)
                    self.insert_layer(signal_region + ground_region, face_id + "_layerMS",
                                      z=z[face_id][0] - sign * self.participation_sheet_distance,
                                      thickness=-sign * self.participation_sheet_thickness)
                    self.insert_layer(ground_box_region - signal_region - ground_region, face_id + "_layerSA",
                                      z=z[face_id][0] + sign * self.participation_sheet_distance,
                                      thickness=sign * self.participation_sheet_thickness)

            self.insert_splitter_layers(splitter, z[i + 1])

        # Insert substrates
        for i in range(int(self.lower_box_height > 0), len(face_stack) + 1, 2):
            # faces around the substrate
            faces = []
            if i < len(face_stack):
                faces += face_stack[i]
            if i > 0:
                faces += face_stack[i-1]

            # find layers to be subtracted from substrate
            layers = ['etch', 'through_silicon_via']
            subtract = [k for k in self.layers if any(t in k for t in layers) and any(t in k for t in faces)]

            # insert substrate layer
            name = 'substrate' if i < 2 else f'substrate_{i // 2}'
            self.layers[name] = {'z': z[i], 'thickness': z[i + 1] - z[i],
                                 'material': self.ith_value(self.substrate_material, i // 2),
                                 **({'subtract': subtract} if subtract else dict())}

        # Insert vacuum
        subtract = [n for n, v in self.layers.items() if v.get('material', None) is not None and
                    v.get('thickness', 0.0) != 0.0]
        self.layers['vacuum'] = {'z': z[0], 'thickness': z[-1] - z[0], 'material': 'vacuum', 'subtract': subtract}

    def ground_grid_region(self, face_id):
        """Returns region of ground grid for the given face id."""
        box = self.ground_grid_box & self.box  # restrict self.ground_grid_box inside self.box
        grid_area = box * (1 / self.layout.dbu)
        protection = self.merged_region_from_layer(face_id, "ground_grid_avoidance")
        grid_mag_factor = 1
        return make_grid(grid_area, protection,
                         grid_step=10 * (1 / self.layout.dbu) * grid_mag_factor,
                         grid_size=5 * (1 / self.layout.dbu) * grid_mag_factor)

    def produce_waveguide_to_port(self, location, towards, port_nr, side=None,
                                  use_internal_ports=None, waveguide_length=None,
                                  term1=0, turn_radius=None,
                                  a=None, b=None, over_etching=None,
                                  airbridge=False, face=0):
        """Create a waveguide connection from some `location` to a port, and add the corresponding port to
        `simulation.ports`.

        Arguments:
            location (pya.DPoint): Point where the waveguide connects to the simulation
            towards (pya.DPoint): Point that sets the direction of the waveguide.
                The waveguide will start from `location` and go towards `towards`
            port_nr (int): Port index for the simulation engine starting from 1
            side (str): Indicate on which edge the port should be located. Ignored for internal ports.
                Must be one of `left`, `right`, `top` or `bottom`
            use_internal_ports (bool, optional): if True, ports will be inside the simulation. If False, ports will be
                brought out to an edge of the box, determined by `side`.
                Defaults to the value of the `use_internal_ports` parameter
            waveguide_length (float, optional): length of the waveguide (μm), used only for internal ports
                Defaults to the value of the `waveguide_length` parameter
            term1 (float, optional): Termination gap (μm) at `location`. Default 0
            turn_radius (float, optional): Turn radius of the waveguide. Not relevant for internal ports.
                Defaults to the value of the `r` parameter
            a (float, optional): Center conductor width. Defaults to the value of the `a` parameter
            b (float, optional): Conductor gap width. Defaults to the value of the `b` parameter
            over_etching (float, optional): Expansion of gaps. Defaults to the value of the `over_etching` parameter
            airbridge (bool, optional): if True, an airbridge will be inserted at `location`. Default False.
            face: face to place waveguide and port on. Either 0 (default) or 1, for bottom or top face.
        """

        waveguide_safety_overlap = 0.005  # Extend waveguide by this amount to avoid gaps due to nm-scale rounding
                                          # errors
        waveguide_gap_extension = 1  # Extend gaps beyond waveguides into ground plane to define the ground port edge

        if turn_radius is None:
            turn_radius = self.r
        if a is None:
            a = self.a
        if b is None:
            b = self.b
        if over_etching is None:
            over_etching = self.over_etching
        if use_internal_ports is None:
            use_internal_ports = self.use_internal_ports
        if waveguide_length is None:
            waveguide_length = self.waveguide_length

        # Create a new path in the direction of path but with length waveguide_length
        direction = towards - location
        direction = direction / direction.length()

        waveguide_a = a
        waveguide_b = b
        # First node may be an airbridge
        if airbridge:
            first_node = Node(location, Airbridge, a=a, b=b)
            waveguide_a = Airbridge.bridge_width
            waveguide_b = Airbridge.bridge_width / Element.a * Element.b
        else:
            first_node = Node(location)

        if use_internal_ports:
            signal_point = location + (waveguide_length + over_etching) * direction
            ground_point = location + (waveguide_length + a - 3 * over_etching) * direction

            nodes = [
                first_node,
                Node(signal_point + waveguide_safety_overlap * direction),
            ]
            port = InternalPort(port_nr, *self.etched_line(signal_point, ground_point), face=face)

            extension_nodes = [
                Node(ground_point),
                Node(ground_point + waveguide_gap_extension * direction)
            ]
        else:
            corner_point = location + (waveguide_length + turn_radius) * direction
            if side is None:
                raise ValueError("Waveport side in the arguments of `produce_waveguide_to_ports` is not specified")
            port_edge_point = {
                "left": pya.DPoint(self.box.left, corner_point.y),
                "right": pya.DPoint(self.box.right, corner_point.y),
                "top": pya.DPoint(corner_point.x, self.box.top),
                "bottom": pya.DPoint(corner_point.x, self.box.bottom)
            }[side]

            nodes = [
                first_node,
                Node(corner_point),
                Node(port_edge_point),
            ]
            port = EdgePort(port_nr, port_edge_point, face=face)

        tl = self.add_element(WaveguideComposite,
                              nodes=nodes,
                              r=turn_radius,
                              term1=term1,
                              term2=0,
                              a=waveguide_a,
                              b=waveguide_b,
                              face_ids=[self.face_ids[face]]
                              )

        self.cell.insert(pya.DCellInstArray(tl.cell_index(), pya.DTrans()))
        feedline_length = tl.length()

        if use_internal_ports:
            port_end_piece = self.add_element(WaveguideComposite,
                                              nodes=extension_nodes,
                                              a=a,
                                              b=b,
                                              term1=a-4*over_etching,
                                              term2=0,
                                              face_ids=[self.face_ids[face]]
                                              )
            self.cell.insert(pya.DCellInstArray(port_end_piece.cell_index(), pya.DTrans()))
        else:
            port.deembed_len = feedline_length

        self.ports.append(port)

    def get_parameters(self):
        """Return dictionary with all parameters and their values."""

        return {param: getattr(self, param) for param in type(self).get_schema()}

    def etched_line(self, p1: pya.DPoint, p2: pya.DPoint):
        """
            Return the end points of line segment after extending it at both ends by amount of over_etching.
            This function must be used when initializing InternalPort.

            Arguments:
                p1 (pya.DPoint): first end of line segment
                p2 (pya.DPoint): second end of line segment

            Returns:
                 [p1 - d, p2 + d]: list of extended end points.
        """
        d = (self.over_etching / p1.distance(p2)) * (p2 - p1)
        return [p1 - d, p2 + d]

    def get_port_data(self):
        """ Return the port data in dictionary form and add the information of port polygon. Includes following:

            * Items from `Port` instance
            * polygon: point coordinates of the port polygon
            * signal_edge: point coordinates of the signal edge
            * ground_edge: point coordinates of the ground edge
        """
        simulation = self
        z = self.face_z_levels()
        # gather port data
        port_data = []
        if simulation.use_ports:
            for port in simulation.ports:
                # Basic data from Port
                p_data = port.as_dict()

                face_id = self.face_ids[port.face]

                # Define a 3D polygon for each port
                if isinstance(port, EdgePort):

                    port_z0 = max(z[face_id][0] - simulation.port_size / 2, z[0])
                    port_z1 = min(z[face_id][0] + simulation.port_size / 2, z[-1])

                    # Determine which edge this port is on
                    if (port.signal_location.x == simulation.box.left
                            or port.signal_location.x == simulation.box.right):
                        port_y0 = max(port.signal_location.y - simulation.port_size / 2, simulation.box.bottom)
                        port_y1 = min(port.signal_location.y + simulation.port_size / 2, simulation.box.top)
                        p_data['polygon'] = [
                            [port.signal_location.x, port_y0, port_z0],
                            [port.signal_location.x, port_y1, port_z0],
                            [port.signal_location.x, port_y1, port_z1],
                            [port.signal_location.x, port_y0, port_z1]
                        ]

                    elif (port.signal_location.y == simulation.box.top
                          or port.signal_location.y == simulation.box.bottom):
                        port_x0 = max(port.signal_location.x - simulation.port_size / 2, simulation.box.left)
                        port_x1 = min(port.signal_location.x + simulation.port_size / 2, simulation.box.right)
                        p_data['polygon'] = [
                            [port_x0, port.signal_location.y, port_z0],
                            [port_x1, port.signal_location.y, port_z0],
                            [port_x1, port.signal_location.y, port_z1],
                            [port_x0, port.signal_location.y, port_z1]
                        ]

                    else:
                        raise ValueError(f"Port {port.number} is an EdgePort but not on the edge of the simulation box")

                elif isinstance(port, InternalPort):
                    if hasattr(port, 'ground_location'):
                        try:
                            _, _, signal_edge = find_edge_from_point_in_cell(
                                simulation.cell,
                                # simulation.get_layer(port.signal_layer, port.face),
                                self.layout.layer(get_simulation_layer_by_name(face_id + '_' + port.signal_layer)),
                                port.signal_location,
                                simulation.layout.dbu)
                            _, _, ground_edge = find_edge_from_point_in_cell(
                                simulation.cell,
                                # simulation.get_layer('simulation_ground', port.face),
                                self.layout.layer(get_simulation_layer_by_name(face_id + '_ground')),
                                port.ground_location,
                                simulation.layout.dbu)

                            port_z = z[face_id][0]
                            p_data['polygon'] = get_enclosing_polygon(
                                [[signal_edge.x1, signal_edge.y1, port_z], [signal_edge.x2, signal_edge.y2, port_z],
                                 [ground_edge.x1, ground_edge.y1, port_z], [ground_edge.x2, ground_edge.y2, port_z]])
                            p_data['signal_edge'] = ((signal_edge.x1, signal_edge.y1, port_z),
                                                     (signal_edge.x2, signal_edge.y2, port_z))
                            p_data['ground_edge'] = ((ground_edge.x1, ground_edge.y1, port_z),
                                                     (ground_edge.x2, ground_edge.y2, port_z))
                        except ValueError as e:
                            self.__log.warning('Unable to create polygon for port {}, because either signal or ground '
                                               'edge is not found.'.format(port.number))
                            self.__log.debug(e)
                else:
                    raise ValueError("Port {} has unsupported port class {}".format(port.number, type(port).__name__))

                # Change signal and ground location from DVector to list and add z-component as third term
                for location in ['signal_location', 'ground_location']:
                    if location in p_data:
                        p_data[location] = [p_data[location].x, p_data[location].y, z[face_id][0]]

                port_data.append(p_data)

        return port_data

    def get_simulation_data(self):
        """ Return the simulation data in dictionary form. Contains following:

            * gds_file: name of gds file to include geometry layers,
            * units: length unit in simulations, 'um',
            * layers: geometry data,
            * material_dict: Dictionary of dielectric materials,
            * box: Boundary box,
            * ports: Port data in dictionary form, see self.get_port_data(),
            * parameters: All Simulation class parameters in dictionary form,
        """
        # check that materials are defined in material_dict
        materials = [layer['material'] for layer in self.layers.values() if 'material' in layer]
        mater_dict = ast.literal_eval(self.material_dict) if isinstance(self.material_dict, str) else self.material_dict
        for name in materials:
            if name not in mater_dict and name not in ['pec', 'vacuum', None]:
                raise ValueError("Material '{}' used but not defined in Simulation.material_dict".format(name))

        return {
            'gds_file': self.name + '.gds',
            'units': 'um',  # hardcoded assumption in multiple places
            'layers': self.layers,
            'material_dict': mater_dict,
            'box': self.box,
            'ports': self.get_port_data(),
            'parameters': self.get_parameters(),
        }

    def get_layers(self):
        """ Returns simulation layer numbers in list. Only return layers that are in use. """
        return [pya.LayerInfo(d['layer'], 0) for d in self.layers.values() if 'layer' in d]

    @staticmethod
    def delete_instances(cell, name, index=(0,)):
        """
            Allows for deleting a sub-cell of the top 'cell' with a specific 'name'. The 'index' argument can be used to
            access more than one sub-cell sharing the same 'name', but with different appended 'index' to the 'name'.
        """
        for i in index:
            index_name = f'${i}' if i > 0 else ''
            cell_to_be_deleted = cell.layout().cell(f'{name}{index_name}')
            if cell_to_be_deleted is not None:
                cell_to_be_deleted.delete()
