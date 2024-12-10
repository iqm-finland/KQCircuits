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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


import abc
import ast

import logging

from kqcircuits.defaults import default_faces
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.element import Element, resolve_face
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.partition_region import PartitionRegion
from kqcircuits.simulations.port import Port, InternalPort, EdgePort
from kqcircuits.util.geometry_helper import (
    region_with_merged_polygons,
    region_with_merged_points,
    merge_points_and_match_on_edges,
)
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.simulations.export.util import find_edge_from_point_in_cell
from kqcircuits.simulations.export.util import get_enclosing_polygon
from kqcircuits.util.groundgrid import make_grid
from kqcircuits.junctions.sim import Sim
from kqcircuits.util.library_helper import load_libraries


simulation_layer_dict = {}

load_libraries()  # allows parameter overrides from defaults.py


def get_simulation_layer_by_name(layer_name):
    """Returns layer info of given name. If layer doesn't exist, a new layer is created.
    New layers are created with data type = 0 and layer numbering starts from 1000."""
    if layer_name not in simulation_layer_dict:
        simulation_layer_dict[layer_name] = pya.LayerInfo(len(simulation_layer_dict) + 1000, 0, layer_name)
    return simulation_layer_dict[layer_name]


def to_1d_list(data):
    """Helper function to cast a scalar or a nested list into a one dimensional list"""

    def _scalar_to_list(data):
        return data if isinstance(data, list) else [data]

    data = _scalar_to_list(data)

    while any(isinstance(d, list) for d in data):
        data = [y for x in data for y in _scalar_to_list(x)]

    return data


@add_parameters_from(Element)
@add_parameters_from(
    Sim,
    "junction_total_length",
    "junction_upper_pad_width",
    "junction_upper_pad_length",
    "junction_lower_pad_width",
    "junction_lower_pad_length",
    "include_background_gap",
)
class Simulation:
    """Base class for simulation geometries.

    Generally, this class is intended to be subclassed by a specific simulation implementation; the
    implementation defines the simulation geometry and ports in `build`.

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
    ports: list[Port]

    # Parameters
    box = Param(pdt.TypeShape, "Boundary box", pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000)))
    ground_grid_box = Param(pdt.TypeShape, "Border", pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000)))
    with_grid = Param(pdt.TypeBoolean, "Make ground plane grid", False)
    name = Param(pdt.TypeString, "Name of the simulation", "Simulation")

    use_ports = Param(pdt.TypeBoolean, "Turn off to disable all ports (for debugging)", True)
    use_internal_ports = Param(pdt.TypeBoolean, "Use internal (lumped) ports. The alternative is wave ports.", True)
    port_size = Param(
        pdt.TypeDouble,
        "Width and height of wave ports",
        400.0,
        unit="µm",
        docstring="The port size can also be set as a list specifying the extensions from the center of "
        "the port to left, right, down and up, respectively.",
    )

    upper_box_height = Param(pdt.TypeDouble, "Height of vacuum above top substrate", 1000.0, unit="µm")
    lower_box_height = Param(
        pdt.TypeDouble,
        "Height of vacuum below bottom substrate",
        0,
        unit="µm",
        docstring="Set > 0 to start face counting from substrate bottom layer.",
    )
    fixed_level_stackup = Param(pdt.TypeBoolean, "Use fixed level multi-face stack-up", True)
    face_stack = Param(
        pdt.TypeList,
        "Face IDs on the substrate surfaces from bottom to top",
        ["1t1"],
        docstring="The parameter can be set as list of lists to enable multi-face stack-up on substrate "
        "surfaces. Set term to empty list to not have metal on the surface.",
    )
    substrate_height = Param(
        pdt.TypeList,
        "Height of the substrates",
        [550.0, 375.0],
        unit="[µm]",
        docstring="The value can be scalar or list of scalars. Set as list to use individual "
        "substrate heights from bottom to top.",
    )
    substrate_box = Param(
        pdt.TypeList,
        "x and y dimensions of substrates",
        [None],
        docstring="Set as a list of pya.DBox objects to give substrate dimensions individually from "
        "bottom to top. If a value in the list is not pya.DBox object, the corresponding"
        "substrate covers fully the general boundary box.",
    )
    substrate_material = Param(
        pdt.TypeList,
        "Material of the substrates.",
        ["silicon"],
        docstring="Value can be string or list of strings. Use only keywords introduced in "
        "material_dict. Set as list to use individual materials from bottom to top.",
    )
    material_dict = Param(
        pdt.TypeString,
        "Dictionary of dielectric materials",
        "{'silicon': {'permittivity': 11.45}}",
        docstring="Material property keywords follow Ansys Electromagnetics property names. "
        "For example 'permittivity', 'dielectric_loss_tangent', etc.",
    )
    chip_distance = Param(
        pdt.TypeList,
        "Height of vacuum between two chips",
        [8.0],
        unit="[µm]",
        docstring="The value can be scalar or list of scalars. Set as list to use individual chip "
        "distances from bottom to top. The chip distances are measured between "
        "the closest layers of the opposing chips.",
    )

    airbridge_height = Param(pdt.TypeDouble, "Height of airbridges.", 3.4, unit="µm")
    metal_height = Param(pdt.TypeList, "Height of metal sheet on each face.", [0.0], unit="µm")
    dielectric_height = Param(pdt.TypeList, "Height of insulator dielectric on each face.", [0.0], unit="µm")
    dielectric_material = Param(
        pdt.TypeList,
        "Material of insulator dielectric on each face.",
        ["silicon"],
        unit="µm",
        docstring="Use only keywords introduced in material_dict.",
    )

    waveguide_length = Param(
        pdt.TypeDouble,
        "Length of waveguide stubs or distance between couplers and waveguide turning point",
        100,
        unit="µm",
    )
    over_etching = Param(pdt.TypeDouble, "Expansion of metal gaps (negative to shrink the gaps).", 0, unit="μm")
    vertical_over_etching = Param(pdt.TypeDouble, "Vertical over-etching into substrates at gaps.", 0, unit="μm")
    hollow_tsv = Param(pdt.TypeBoolean, "Make TSVs hollow with vacuum inside and thin metal boundary.", False)

    partition_regions = Param(
        pdt.TypeString,
        "Parameters of partition regions as list of dictionaries",
        [],
        docstring="See constructor of the PartitionRegion class for parameter definitions.",
    )

    tls_layer_thickness = Param(
        pdt.TypeList, "Thickness of TLS interface layers (MA, MS, and SA, respectively)", [0.0], unit="µm"
    )
    tls_layer_material = Param(
        pdt.TypeList,
        "Materials of TLS interface layers (MA, MS, and SA, respectively)",
        ["vacuum", "silicon", "silicon"],
        docstring="Use only keywords introduced in material_dict. Valid only if tls_sheet_approximation=False.",
    )
    tls_sheet_approximation = Param(pdt.TypeBoolean, "Approximate TLS interface layers as sheets", False)
    detach_tls_sheets_from_body = Param(
        pdt.TypeBoolean,
        "TLS interface layers are created `tls_layer_thickness` above or below the interface of 3D bodies",
        True,
        docstring="Only has an effect when tls_sheet_approximation=True."
        "Setting to False when using `ElmerEPR3DSolution` significantly improves simulation performance",
    )

    minimum_point_spacing = Param(pdt.TypeDouble, "Tolerance for merging adjacent points in polygon", 0.01, unit="µm")
    polygon_tolerance = Param(pdt.TypeDouble, "Tolerance for merging adjacent polygons in a layer", 0.004, unit="µm")

    small_shape_area = Param(pdt.TypeDouble, "Area below which shapes will trigger a warning.", 1.0, unit="µm²")

    extra_json_data = Param(
        pdt.TypeNone,
        "Extra data in dict form to store in resulting JSON",
        None,
        docstring="This field may be used to store 'virtual' parameters useful for your simulations",
    )

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
            logging.error(error_text)
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
        if "cell" in kwargs:
            self.cell = kwargs["cell"]
        else:
            self.cell = layout.create_cell(self.name)

        self.layers = {}
        self.build()
        self.create_simulation_layers()
        self.warn_of_small_shapes()

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

        if "box" not in kwargs:
            box = cell.dbbox().enlarge(margin, margin)
            if grid_size > 0:
                box.left = round(box.left / grid_size) * grid_size
                box.right = round(box.right / grid_size) * grid_size
                box.bottom = round(box.bottom / grid_size) * grid_size
                box.top = round(box.top / grid_size) * grid_size
            extra_kwargs["box"] = box

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

    def _face_box(self, i):
        """Return the boundary box for given face number.
        Boundary box is the intersection of the global boundary box and the substrate x-y-dimension box.
        """
        box = self.ith_value(self.substrate_box, (i + int(self.lower_box_height <= 0)) // 2)
        return self.box & box if isinstance(box, pya.DBox) else self.box

    @staticmethod
    def ith_value(list_or_constant, i):
        """Helper function to return value from list or constant corresponding to the ordinal number i.
        Too short lists are extended by duplicating the last value of the list.
        """
        if isinstance(list_or_constant, list):
            if i < len(list_or_constant):
                return list_or_constant[i]  # return ith term of the list
            return list_or_constant[-1]  # return last term of the list
        return list_or_constant  # return constant value

    def face_z_levels(self):
        """Returns dictionary of z-levels. The dictionary can be used either with integer or string key values: Integer
        keys return surface z-levels in ascending order (including domain boundary bottom and top). String keys
        (key = face_id) return the three z-levels of the face (metal bottom, metal-dielectric interface, dielectric top)

        The level z=0 is at lowest substrate top.
        """
        # Build z-levels such that level z=0 is at very bottom. Z-transformation is applied later.
        vacuum_at_bottom = self.lower_box_height > 0
        z = self.lower_box_height if vacuum_at_bottom else float(self.ith_value(self.substrate_height, 0))
        z_dict = {}
        z_list = [0.0]
        z_trans = 0.0
        stack = self.face_stack_list_of_lists()
        for i, face_ids in enumerate(stack):
            metal_heights = self.ith_value(self.metal_height, i)
            dielectric_heights = self.ith_value(self.dielectric_height, i)
            if bool(i % 2) == vacuum_at_bottom:
                # faces on top of a substrate
                z_list.append(z)
                if i < 2:
                    z_trans = z  # determine z-transformation
                for j, face_id in enumerate(face_ids):
                    metal_z = z + float(self.ith_value(metal_heights, j))
                    dielectric_z = metal_z + float(self.ith_value(dielectric_heights, j))
                    z_dict[face_id] = [z, metal_z, dielectric_z]
                    z = dielectric_z
                z += float(self.ith_value(self.chip_distance, i // 2)) if i < len(stack) - 1 else self.upper_box_height
            else:
                # faces on bottom of a substrate
                for j, face_id in enumerate(face_ids[::-1]):
                    dielectric_z = z + float(self.ith_value(dielectric_heights, j))
                    metal_z = dielectric_z + float(self.ith_value(metal_heights, j))
                    z_dict[face_id] = [metal_z, dielectric_z, z]
                    z = metal_z
                z_list.append(z)
                z += float(self.ith_value(self.substrate_height, (i + 1) // 2))
        z_list.append(z)

        # Return combined dictionary such that level z=0 is at lowest substrate top
        return {
            **{k: z_list[k] - z_trans for k in range(-1, len(z_list))},
            **{k: [x - z_trans for x in v] for k, v in z_dict.items()},
        }

    def region_from_layer(self, face_id, layer_name):
        """Returns a `Region` containing all geometry from a specified layer"""
        face_layers = default_faces[face_id] if face_id in default_faces else {}
        if layer_name in face_layers:
            return pya.Region(self.cell.begin_shapes_rec(self.layout.layer(face_layers[layer_name])))
        return pya.Region()

    def simplified_region(self, region, expansion=0.0):
        """Returns a region that is simplified by functions region_with_merged_polygons and region_with_merged_points.
        More precisely:
        - Merges polygons ignoring gaps that are smaller than self.polygon_tolerance
        - Expands/shrinks region by amount given by 'expansion'
        - In each polygon of the region, removes points that are closer to other points than self.minimum_point_spacing
        """
        return region_with_merged_points(
            region_with_merged_polygons(
                region, tolerance=self.polygon_tolerance / self.layout.dbu, expansion=expansion / self.layout.dbu
            ),
            tolerance=self.minimum_point_spacing / self.layout.dbu,
        )

    def insert_layer(self, layer_name, region, z0, z1, **params):
        """Adds layer parameters into 'self.layers' if region is non-empty."""
        if not region.is_empty():
            self.layers[layer_name] = {"region": region.dup(), "bottom": min(z0, z1), "top": max(z0, z1), **params}

    def insert_stacked_up_layers(self, stack, z0):
        """Produces the layer stack-up and adds the layers into 'self.layers'.
        Each layer is split into sub-layers by their z-level.

        Args:
            stack: list of layers in form of tuples containing (region, layer name, thickness, material)
            z0: the base z-level for the layer stack-up
        """
        levels = {}  # existing z-levels based on layers underneath (z-level as key and region as value)
        for region, layer_name, thickness, material in stack:
            if region.is_empty():
                continue

            # Split the layer into z-levels
            region_levels = {}  # the layer region divided into z-levels
            non_region_levels = {}  # the z-levels outside the layer region
            sum_reg = pya.Region()
            for z, reg in levels.items():
                intersection = reg & region
                if not intersection.is_empty():
                    region_levels[z] = intersection
                subtraction = reg - region
                if not subtraction.is_empty():
                    non_region_levels[z] = subtraction
                sum_reg += reg
            on_base_level = region - sum_reg
            if not on_base_level.is_empty():
                region_levels[round(z0, 12)] = on_base_level

            # Create collective layer for klayout visualization if the layer is split
            if len(region_levels) > 1:
                self.cell.shapes(self.layout.layer(get_simulation_layer_by_name(layer_name))).insert(region)

            # Apply parts of divided layers into self.layers
            for i, (z, reg) in enumerate(sorted(region_levels.items())):
                self.insert_layer(
                    f"{layer_name}_{i}" if len(region_levels) > 1 else layer_name,
                    reg,
                    z,
                    z + thickness,
                    material=material,
                )

            # Update existing z-levels dictionary
            if thickness != 0.0:
                levels = non_region_levels
                for z, reg in region_levels.items():
                    top_z = round(z + thickness, 12)
                    if top_z in levels:
                        levels[top_z] += reg
                    else:
                        levels[top_z] = reg

    def insert_layers_between_faces(self, i, opp_i, layer_name, **params):
        """Helper function to be used to produce indium bumps and TSVs"""
        z = self.face_z_levels()
        face_stack = self.face_stack_list_of_lists()
        box = self._face_box(i)
        if 0 <= opp_i < len(face_stack):
            box = box & self._face_box(opp_i)
        box_region = pya.Region(box.to_itype(self.layout.dbu))
        sum_region = pya.Region()
        for face_id in face_stack[i]:
            region = self.simplified_region(self.region_from_layer(face_id, layer_name) & box_region)
            if region.is_empty():
                continue
            sum_region += region
            if 0 <= opp_i < len(face_stack):
                for opp_id in face_stack[opp_i]:
                    common_region = region & self.simplified_region(
                        self.region_from_layer(opp_id, layer_name) & box_region
                    )
                    if common_region.is_empty():
                        continue
                    if f"{opp_id}_{face_id}_{layer_name}" not in self.layers:  # if statement is to avoid duplicates
                        self.insert_layer(
                            f"{face_id}_{opp_id}_{layer_name}",
                            common_region,
                            z[face_id][1],
                            z[opp_id][1],
                            **params,
                        )
                    region -= common_region
                    if region.is_empty():
                        break
            if not region.is_empty():
                self.insert_layer(
                    face_id + "_" + layer_name,
                    region,
                    z[face_id][1],
                    z[opp_i + 1],
                    **params,
                )
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
        parts = self.get_partition_regions()
        for part in parts:
            part.limit_box(z[0], z[-1], self.box, self.layout.dbu)
        face_stack = self.face_stack_list_of_lists()
        for i, face_ids in enumerate(face_stack):
            sign = (-1) ** (i + int(self.lower_box_height > 0))
            stack = []
            dielectric_material = self.ith_value(self.dielectric_material, i)

            # insert TSVs and indium bumps
            tsv_params = {"edge_material": "pec"} if self.hollow_tsv else {"material": "pec"}
            tsv_region = self.insert_layers_between_faces(i, i - sign, "through_silicon_via", **tsv_params)
            bump_region = self.insert_layers_between_faces(i, i + sign, "indium_bump", material="pec")
            ground_box_region = pya.Region(self._face_box(i).to_itype(self.layout.dbu))

            for j, face_id in enumerate(face_ids):
                metal_gap_region = self.region_from_layer(face_id, "base_metal_gap_wo_grid")
                metal_add_region = self.region_from_layer(face_id, "base_metal_addition")

                if self.over_etching >= 0:
                    lithography_region = self.simplified_region(metal_gap_region - metal_add_region, self.over_etching)
                else:
                    lithography_region = ground_box_region - self.simplified_region(
                        ground_box_region - (metal_gap_region - metal_add_region), -self.over_etching
                    )
                for port in self.ports:
                    if resolve_face(port.face, self.face_ids) == face_id and hasattr(port, "get_etch_polygon"):
                        lithography_region += pya.Region(port.get_etch_polygon().to_itype(self.layout.dbu))

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
                            if resolve_face(port.face, self.face_ids) == face_id:
                                if hasattr(port, "ground_location"):
                                    v_mps = port.signal_location - port.ground_location
                                    v_mps = self.minimum_point_spacing * v_mps / v_mps.abs()
                                    signal_loc = (port.signal_location + v_mps).to_itype(self.layout.dbu)
                                    ground_region -= ground_region.interacting(pya.Edge(signal_loc, signal_loc))

                                    ground_loc = (port.ground_location - v_mps).to_itype(self.layout.dbu)
                                    if not port.floating:
                                        ground_region += signal_region.interacting(pya.Edge(ground_loc, ground_loc))
                                else:
                                    signal_loc = port.signal_location.to_itype(self.layout.dbu)
                                    ground_region -= ground_region.interacting(pya.Edge(signal_loc, signal_loc))

                    ground_region.merge()
                    signal_region -= ground_region

                dielectric_region = ground_box_region - self.simplified_region(
                    self.region_from_layer(face_id, "dielectric_etch")
                )

                # Create gap and etch regions and update metals
                gap_region = ground_box_region - signal_region - ground_region  # excluding ground grid
                if self.with_grid:
                    ground_region -= self.ground_grid_region(face_id)
                etch_region = ground_box_region - signal_region - ground_region  # including ground grid
                signal_region -= tsv_region
                ground_region -= tsv_region
                dielectric_region -= tsv_region
                metal_region = signal_region + ground_region
                for part in parts:
                    if part.face is not None and resolve_face(part.face, self.face_ids) == face_id:
                        part.limit_face(z[face_id][0], sign, metal_region, etch_region, self.layout.dbu)

                # Insert signal, ground and dielectric layers
                dielectric_thickness = z[face_id][2] - z[face_id][1]
                if self.fixed_level_stackup:
                    # Use fixed level stack-up
                    self.insert_layer(face_id + "_signal", signal_region, z[face_id][0], z[face_id][1], material="pec")
                    self.insert_layer(face_id + "_ground", ground_region, z[face_id][0], z[face_id][1], material="pec")
                    if dielectric_thickness != 0.0:
                        self.insert_layer(
                            face_id + "_via",
                            ground_box_region - dielectric_region,
                            z[face_id][1],
                            z[face_id][2],
                            material="pec",
                        )
                        self.insert_layer(
                            face_id + "_dielectric",
                            ground_box_region,
                            z[face_id][0],
                            z[face_id][2],
                            material=self.ith_value(dielectric_material, j),
                        )

                else:
                    # Use stack to produce drop-down stack-up
                    metal_thickness = z[face_id][1] - z[face_id][0]
                    stack.append((signal_region, face_id + "_signal", metal_thickness, "pec"))
                    stack.append((ground_region, face_id + "_ground", metal_thickness, "pec"))
                    if dielectric_thickness != 0.0:
                        stack.append(
                            (
                                dielectric_region,
                                face_id + "_dielectric",
                                dielectric_thickness,
                                self.ith_value(dielectric_material, j),
                            )
                        )

                # Insert gap and etch layers only on the first face of the stack-up (no material)
                if j == 0:
                    if self.vertical_over_etching > 0.0:
                        etch_z = z[face_id][0] - sign * self.vertical_over_etching
                        self.insert_layer(face_id + "_etch", etch_region, etch_z, z[face_id][0])
                    self.insert_layer(face_id + "_gap", gap_region, z[face_id][0], z[face_id][1])

                # Insert airbridges
                bridge_z = z[face_id][1] + sign * self.airbridge_height
                ab_flyover_region = (
                    self.simplified_region(self.region_from_layer(face_id, "airbridge_flyover")) & ground_box_region
                )
                self.insert_layer(
                    face_id + "_airbridge_flyover",
                    ab_flyover_region,
                    bridge_z,
                    bridge_z,
                    material="pec",
                )
                ab_pads_region = (
                    self.simplified_region(self.region_from_layer(face_id, "airbridge_pads")) & ground_box_region
                )
                self.insert_layer(face_id + "_airbridge_pads", ab_pads_region, z[face_id][1], bridge_z, material="pec")

            self.insert_stacked_up_layers(stack, z[i + 1])

            # Rest of the features are not available with multilayer stack-up
            if len(face_ids) != 1:
                continue
            face_id = face_ids[0]

            # Insert TLS interface layers
            for layer_num, layer_id in enumerate(["MA", "MS", "SA"]):
                layer_name = face_id + "_layer" + layer_id
                layer_z = [z[face_id][1], z[face_id][0], z[face_id][0] - sign * self.vertical_over_etching][layer_num]
                thickness = float(self.ith_value(self.tls_layer_thickness, layer_num))
                layer_top_z = layer_z + [sign, -sign, -sign][layer_num] * thickness
                if self.tls_sheet_approximation:
                    if layer_id == "MA":
                        material = "vacuum"
                    else:
                        material = self.ith_value(self.substrate_material, (i + int(self.lower_box_height <= 0)) // 2)
                    if self.detach_tls_sheets_from_body:
                        z_params = {"z0": layer_top_z, "z1": layer_top_z}
                    else:
                        z_params = {"z0": layer_z, "z1": layer_z}
                elif thickness != 0.0:
                    material = self.ith_value(self.tls_layer_material, layer_num)
                    z_params = {"z0": layer_z, "z1": layer_top_z}

                    # Insert wall layer
                    if layer_z != z[face_id][0]:
                        wall_region = metal_region.sized(thickness / self.layout.dbu) & etch_region
                        self.insert_layer(
                            layer_name + "wall",
                            wall_region,
                            layer_z,
                            z[face_id][0],
                            material=material,
                        )
                else:
                    continue

                # Insert layer
                layer_region = [
                    (
                        metal_region
                        if self.tls_sheet_approximation
                        else metal_region.sized(thickness / self.layout.dbu)
                        & (metal_region + etch_region - bump_region - ab_pads_region)
                    ),
                    metal_region,
                    etch_region,
                ][layer_num]
                self.insert_layer(layer_name, layer_region, material=material, **z_params)

        # Insert substrates
        for i in range(int(self.lower_box_height > 0), len(face_stack) + 1, 2):
            self.insert_layer(
                f"substrate_{(i // 2) + 1}",
                pya.Region(self._face_box(i).to_itype(self.layout.dbu)),
                z[i],
                z[i + 1],
                material=self.ith_value(self.substrate_material, i // 2),
                subtract_keys=["_etch", "_through_silicon_via"],
            )

        # Insert vacuum
        self.insert_layer(
            "vacuum",
            pya.Region(self.box.to_itype(self.layout.dbu)),
            z[0],
            z[-1],
            material="vacuum",
        )

        self.produce_layers(parts)

        # Visualise parititon regions
        for part in parts:
            if part.visualise:
                self.visualise_region(part.region, part.name, f"part_reg_{part.name}")

    def produce_layers(self, parts):
        """Finalizes and partitions self.layers.

        Metals and non-model objects are left without partitioning. We assume that these do not overlap.

        Vacuum or dielectric objects are partitioned if parts is not empty. If these objects overlap, the smaller is
        subtracted from larger.

        Non-model objects are subtracted from vacuum or dielectric objects only if non-model object is mentioned in
        subtract_keys of vacuum or dielectric object.
        """
        layers = []

        def can_modify(obj):
            return obj.get("material", None) not in ["pec", None]

        def are_separate(obj, tool):
            """Returns True if obj and tool do not overlap"""
            if obj["bottom"] == obj["top"] and tool["bottom"] == tool["top"]:
                if obj["bottom"] != tool["bottom"]:
                    return True
            elif obj["top"] <= tool["bottom"] or tool["top"] <= obj["bottom"]:
                return True
            return tool["region"].overlapping(obj["region"]).is_empty()

        def subtract(obj, lay):
            """Subtracts layers[lay] from obj."""
            if lay in obj.get("subtract", set()):
                return  # already subtracted
            tool = layers[lay]
            if tool.get("material", None) is None and all(n not in tool["name"] for n in obj.get("subtract_keys", [])):
                return  # non-material tools are subtracted only if specified in subtract keys
            if obj["bottom"] != obj["top"] and tool["bottom"] == tool["top"]:
                return  # do not subtract sheet from solid
            if are_separate(obj, tool):
                return  # ignore separate objects
            obj["subtract"] = obj.get("subtract", set()) | {lay}

        def subtract_hard(obj, tool):
            """Subtracts tool from obj by modifying dimensions of obj. Returns True if successful."""
            if are_separate(obj, tool):
                return True
            subtract_diff = tool.get("subtract", set()) - obj["subtract"]
            if any(layers[s].get("material", None) is None and not are_separate(obj, layers[s]) for s in subtract_diff):
                return False  # can't apply hard subtract if tool has non-material subtractions that obj doesn't have
            if obj["bottom"] < tool["bottom"]:
                if tool["top"] < obj["top"]:
                    return False
                if obj["region"].not_inside(tool["region"]).is_empty() or not exists(
                    {
                        "bottom": tool["bottom"],
                        "top": obj["top"],
                        "region": obj["region"].dup(),
                        "subtract": obj["subtract"].copy(),
                    }
                ):
                    obj["top"] = tool["bottom"]
                    return True
                return False
            if tool["top"] < obj["top"]:
                if obj["region"].not_inside(tool["region"]).is_empty() or not exists(
                    {
                        "bottom": obj["bottom"],
                        "top": tool["top"],
                        "region": obj["region"].dup(),
                        "subtract": obj["subtract"].copy(),
                    }
                ):
                    obj["bottom"] = tool["top"]
                    return True
                return False
            if not can_modify(tool) and tool["region"].inside(obj["region"]).count() > 10 * obj["region"].count():
                return False  # avoid lateral hard subtract if it creates lots of holes (useful with lots of vias)
            obj["region"] -= tool["region"]
            return True

        def exists(obj):
            """Hardens subtractions and returns True if geometry exists."""
            if "subtract" in obj:
                while True:
                    for s in obj["subtract"]:
                        if subtract_hard(obj, layers[s]):
                            obj["subtract"].remove(s)
                            break
                    else:
                        break

            return not obj["region"].is_empty()

        def covering_regions(obj, tool):
            """Returns tuple of regions where tool covers obj from above and below, respectively."""
            if obj["top"] < tool["bottom"] or tool["top"] < obj["bottom"]:
                return pya.Region(), pya.Region()
            region = obj["region"] & tool["region"]
            if region.is_empty():
                return pya.Region(), pya.Region()
            above = region.dup() if obj["top"] < tool["top"] else pya.Region()
            below = region.dup() if tool["bottom"] < obj["bottom"] else pya.Region()
            for s in tool.get("subtract", set()):
                s_above, s_below = covering_regions(obj, layers[s])
                above -= s_above
                below -= s_below
            return above, below

        layer_list = [
            {
                "name": name,
                "bottom": round(layer["bottom"], 12),
                "top": round(layer["top"], 12),
                **{n: v for n, v in layer.items() if n not in ["bottom", "top"]},
            }
            for name, layer in self.layers.items()
        ]
        part_list = [
            {
                "name": part.name,
                "bottom": round(part.z[0], 12),
                "top": round(part.z[1], 12),
                "region": part.region.dup(),
            }
            for part in parts
            if part.face is None
        ]
        # subtract the previous partition region from the latter if covering the z-range
        for i, part1 in enumerate(part_list):
            for part2 in part_list[i + 1 :]:
                if part1["bottom"] <= part2["bottom"] and part2["top"] <= part1["top"]:
                    part2["region"] -= part1["region"]
        merge_points_and_match_on_edges([part["region"] for part in part_list])

        for layer in sorted(layer_list, key=lambda x: (can_modify(x), x["top"] - x["bottom"], x["region"].area())):
            if can_modify(layer):
                # subtract layers that are added to layer_list
                for i in range(len(layers)):
                    subtract(layer, i)

                # partition the layer into sub-layers
                for part in part_list:
                    if are_separate(layer, part):
                        continue  # ignore separate objects
                    intersection = {
                        "bottom": max(layer["bottom"], part["bottom"]),
                        "top": min(layer["top"], part["top"]),
                        "region": layer["region"] & part["region"],
                        "material": layer.get("material", None),
                        "subtract_keys": layer.get("subtract_keys", []),
                    }
                    for s in layer.get("subtract", set()):
                        subtract(intersection, s)
                    if exists(intersection):
                        layers.append(intersection)
                        subtract(part, len(layers) - 1)
                        subtract(layer, len(layers) - 1)
                        intersection["name"] = (layer["name"] if "used" in part or exists(part) else "") + part["name"]
                        part["used"] = True

            # add non-partitioned parts of the layer
            if exists(layer):
                layers.append(layer)

        merge_points_and_match_on_edges([layer["region"] for layer in layers])

        # Indicate background layer for each sheet
        for layer in layers:
            if can_modify(layer) and layer["bottom"] == layer["top"]:
                max_overlap = 0
                for solid in layers:
                    if solid.get("material", None) == layer["material"] and solid["bottom"] < solid["top"]:
                        overlap = max(r.area() for r in covering_regions(layer, solid))
                        if overlap > max_overlap:
                            layer["background"] = solid["name"]
                            max_overlap = overlap

        # produce self.layers from layers
        self.layers = {}
        for layer in layers:
            if layer["region"].is_empty():
                continue  # ignore layers with empty region
            sim_layer = get_simulation_layer_by_name(layer["name"])
            self.cell.shapes(self.layout.layer(sim_layer)).insert(layer["region"])
            limit_region = pya.Region(self.box.to_itype(self.layout.dbu)).inside(layer["region"]).is_empty()
            subtract = [
                layers[n]["name"]
                for n in sorted(layer.get("subtract", set()), reverse=True)
                if layers[n]["name"] in self.layers
            ]
            self.layers[layer["name"]] = {
                "z": round(layer["bottom"], 12),
                "thickness": round(layer["top"] - layer["bottom"], 12),
                **({"layer": sim_layer.layer} if limit_region else {}),
                **{
                    k: v for k, v in layer.items() if k in ["material", "edge_material", "background"] and v is not None
                },
                **({"subtract": subtract} if subtract else {}),
            }

    def warn_of_small_shapes(self):
        """Warns of small shapes in simulation layers."""
        if self.small_shape_area <= 0.0:
            return
        for name, layer in self.layers.items():
            if "layer" not in layer:
                continue
            shapes = self.cell.shapes(self.layout.layer(layer["layer"], 0))
            for shape in shapes.each():
                area = shape.darea()  # area in µm²
                if area < self.small_shape_area:
                    logging.warning(
                        f"Layer '{name}' of simulation '{self.name}' contains a small shape of {round(area, 3)} µm² "
                        f"with bounding box {shape.dbbox()}."
                    )

    def ground_grid_region(self, face_id):
        """Returns region of ground grid for the given face id."""
        grid_area = self.ground_grid_box * (1 / self.layout.dbu)
        protection = self.simplified_region(self.region_from_layer(face_id, "ground_grid_avoidance"))
        grid_mag_factor = 1
        return make_grid(
            grid_area,
            protection,
            grid_step=10 * (1 / self.layout.dbu) * grid_mag_factor,
            grid_size=5 * (1 / self.layout.dbu) * grid_mag_factor,
        )

    def produce_waveguide_to_port(
        self,
        location,
        towards,
        port_nr,
        side=None,
        use_internal_ports=None,
        waveguide_length=None,
        term1=0,
        turn_radius=None,
        a=None,
        b=None,
        airbridge=False,
        face=0,
        etch_opposite_face=False,
        deembed_cross_section=None,
        **port_kwargs,
    ):
        """Create a waveguide connection from some `location` to a port, and add the corresponding port to
        `simulation.ports`.

        Arguments:
            location (pya.DPoint): Point where the waveguide connects to the simulation
            towards (pya.DPoint): Point that sets the direction of the waveguide.
                The waveguide will start from `location` and go towards `towards`
            port_nr (int): Port index for the simulation engine starting from 1
            side (str): Indicate on which edge the waveguide is routed to, either `left`, `right`, `top` or `bottom`.
                Ignored when use_internal_ports=True. If `None` then the edge is inferred from waveguide direction.
            use_internal_ports: If True, a lumped port is placed at the end of straight waveguide segment. If False,
                the waveguide is brought out to a wave port at the edge of the box, determined by `side`.
                If the value is a string 'at_edge', then a lumped port will be placed next to the edge.
                Defaults to the value of the `use_internal_ports` parameter.
            waveguide_length (float, optional): length of the straight waveguide starting from `location` (μm).
                Defaults to the value of the `waveguide_length` parameter.
            term1 (float, optional): Termination gap (μm) at `location`. Default 0
            turn_radius (float, optional): Turn radius of the waveguide. Defaults to the value of the `r` parameter.
            a (float, optional): Center conductor width. Defaults to the value of the `a` parameter
            b (float, optional): Conductor gap width. Defaults to the value of the `b` parameter
            airbridge (bool, optional): if True, an airbridge will be inserted at `location`. Default False.
            face: face to place waveguide and port on. Either 0 (default) or 1, for bottom or top face.
            etch_opposite_face: If true, the metal on opposite face of the waveguide is etched away.
            port_kwargs: keyword arguments passed for port
        """

        waveguide_gap_extension = 1  # Extend gaps beyond waveguides into ground plane to define the ground port edge

        if turn_radius is None:
            turn_radius = self.r
        if a is None:
            a = self.a
        if b is None:
            b = self.b
        if use_internal_ports is None:
            use_internal_ports = self.use_internal_ports
        if waveguide_length is None:
            waveguide_length = self.waveguide_length

        waveguide_a = a
        waveguide_b = b
        # First node may be an airbridge
        if airbridge:
            first_node = Node(location, Airbridge, a=a, b=b)
            waveguide_a = Airbridge.bridge_width
            waveguide_b = Airbridge.bridge_width / Element.a * Element.b
        else:
            first_node = Node(location)

        d = towards - location
        direction = d / d.length()
        internal_port_length = a - 2 * self.over_etching  # compensated with over etching
        if use_internal_ports in [False, "at_edge"]:  # edge port or internal port next to edge
            if side is None:
                side = (("left", "right"), ("bottom", "top"))[abs(d.x) < abs(d.y)][d.x + d.y > 0]
            out_direction = {
                "left": pya.DVector(-1, 0),
                "right": pya.DVector(1, 0),
                "top": pya.DVector(0, 1),
                "bottom": pya.DVector(0, -1),
            }[side]
            turn_length = turn_radius * abs(out_direction.vprod(direction)) / (1 + out_direction.sprod(direction))
            corner_point = location + (waveguide_length + turn_length) * direction
            port_edge_point = {
                "left": pya.DPoint(self.box.left, corner_point.y),
                "right": pya.DPoint(self.box.right, corner_point.y),
                "top": pya.DPoint(corner_point.x, self.box.top),
                "bottom": pya.DPoint(corner_point.x, self.box.bottom),
            }[side]
            nodes = [
                first_node,
                Node(corner_point),
                Node(port_edge_point),
            ]

            if use_internal_ports == "at_edge":
                signal_point = port_edge_point - waveguide_gap_extension * out_direction
                ground_point = signal_point - internal_port_length * out_direction
                port = InternalPort(port_nr, signal_point, ground_point, face=face, etch_width=a + b, **port_kwargs)
            else:
                port = EdgePort(port_nr, port_edge_point, face=face, deembed_cross_section=deembed_cross_section)

        else:  # internal port at the end of straight waveguide segment
            signal_point = location + waveguide_length * direction
            ground_point = signal_point + internal_port_length * direction

            nodes = [
                first_node,
                Node(ground_point + (waveguide_gap_extension - self.over_etching) * direction),
            ]
            port = InternalPort(port_nr, signal_point, ground_point, face=face, etch_width=a + b, **port_kwargs)

        tl = self.add_element(
            WaveguideComposite,
            nodes=nodes,
            r=turn_radius,
            term1=term1,
            term2=0,
            a=waveguide_a,
            b=waveguide_b,
            etch_opposite_face=etch_opposite_face,
            face_ids=[self.face_ids[face]],
        )

        self.cell.insert(pya.DCellInstArray(tl.cell_index(), pya.DTrans()))
        if not use_internal_ports:
            port.deembed_len = tl.length()

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
        """Return the port data in dictionary form and add the information of port polygon. Includes following:

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
                p_data = {**port.as_dict()}  # Shallow copy to not modify the ports

                face_id = self.face_ids[port.face]

                # Define a 3D polygon for each port
                if isinstance(port, EdgePort):

                    port_size = simulation.port_size if port.size is None else port.size
                    ps = port_size if isinstance(port_size, list) else [port_size / 2] * 4

                    port_z0 = max(z[face_id][0] - ps[2], z[0])
                    port_z1 = min(z[face_id][0] + ps[3], z[-1])

                    # Determine which edge this port is on
                    port_x0 = port_x1 = port.signal_location.x
                    port_y0 = port_y1 = port.signal_location.y
                    if abs(port.signal_location.x - simulation.box.left) < self.layout.dbu:
                        port_y0 = max(port.signal_location.y - ps[1], simulation.box.bottom)
                        port_y1 = min(port.signal_location.y + ps[0], simulation.box.top)
                    elif abs(port.signal_location.x - simulation.box.right) < self.layout.dbu:
                        port_y0 = max(port.signal_location.y - ps[0], simulation.box.bottom)
                        port_y1 = min(port.signal_location.y + ps[1], simulation.box.top)
                    elif abs(port.signal_location.y - simulation.box.bottom) < self.layout.dbu:
                        port_x0 = max(port.signal_location.x - ps[0], simulation.box.left)
                        port_x1 = min(port.signal_location.x + ps[1], simulation.box.right)
                    elif abs(port.signal_location.y - simulation.box.top) < self.layout.dbu:
                        port_x0 = max(port.signal_location.x - ps[1], simulation.box.left)
                        port_x1 = min(port.signal_location.x + ps[0], simulation.box.right)
                    else:
                        raise ValueError(f"Port {port.number} is an EdgePort but not on the edge of the simulation box")

                    p_data["polygon"] = [
                        [port_x0, port_y0, port_z0],
                        [port_x1, port_y1, port_z0],
                        [port_x1, port_y1, port_z1],
                        [port_x0, port_y0, port_z1],
                    ]

                elif isinstance(port, InternalPort):
                    if hasattr(port, "ground_location"):
                        try:
                            _, _, signal_edge = find_edge_from_point_in_cell(
                                simulation.cell,
                                # simulation.get_layer(port.signal_layer, port.face),
                                self.layout.layer(get_simulation_layer_by_name(face_id + "_" + port.signal_layer)),
                                port.signal_location,
                                simulation.layout.dbu,
                            )
                            if port.floating:
                                ground_search = face_id + "_" + port.signal_layer
                            else:
                                ground_search = face_id + "_ground"

                            _, _, ground_edge = find_edge_from_point_in_cell(
                                simulation.cell,
                                # simulation.get_layer('simulation_ground', port.face),
                                self.layout.layer(get_simulation_layer_by_name(ground_search)),
                                port.ground_location,
                                simulation.layout.dbu,
                            )

                            port_z = z[face_id][0]
                            p_data["polygon"] = get_enclosing_polygon(
                                [
                                    [signal_edge.x1, signal_edge.y1, port_z],
                                    [signal_edge.x2, signal_edge.y2, port_z],
                                    [ground_edge.x1, ground_edge.y1, port_z],
                                    [ground_edge.x2, ground_edge.y2, port_z],
                                ]
                            )
                            p_data["signal_edge"] = (
                                (signal_edge.x1, signal_edge.y1, port_z),
                                (signal_edge.x2, signal_edge.y2, port_z),
                            )
                            p_data["ground_edge"] = (
                                (ground_edge.x1, ground_edge.y1, port_z),
                                (ground_edge.x2, ground_edge.y2, port_z),
                            )
                        except ValueError as e:
                            logging.warning(
                                "Unable to create polygon for port %s, because either signal or ground "
                                "edge is not found.",
                                port.number,
                            )
                            logging.debug(e)
                else:
                    raise ValueError(f"Port {port.number} has unsupported port class {type(port).__name__}")

                # Change signal and ground location from DVector to list and add z-component as third term
                for location in ["signal_location", "ground_location"]:
                    if location in p_data:
                        p_data[location] = [p_data[location].x, p_data[location].y, z[face_id][0]]

                port_data.append(p_data)

        return port_data

    def get_simulation_data(self):
        """Return the simulation data in dictionary form. Contains following:

        * units: length unit in simulations, 'um',
        * layers: geometry data,
        * material_dict: Dictionary of dielectric materials,
        * box: Boundary box,
        * ports: Port data in dictionary form, see self.get_port_data(),
        """
        # check that materials are defined in material_dict
        materials = [layer["material"] for layer in self.layers.values() if "material" in layer]
        mater_dict = ast.literal_eval(self.material_dict) if isinstance(self.material_dict, str) else self.material_dict
        for name in materials:
            if name not in mater_dict and name not in ["pec", "vacuum", None]:
                raise ValueError("Material '{name}' used but not defined in Simulation.material_dict")

        return {
            "simulation_name": self.name,
            "units": "um",  # hardcoded assumption in multiple places
            "layers": self.layers,
            "material_dict": mater_dict,
            "box": self.box,
            "ports": self.get_port_data(),
        }

    def get_layers(self):
        """Returns simulation layer numbers in list. Only return layers that are in use."""
        return [pya.LayerInfo(d["layer"], 0) for d in self.layers.values() if "layer" in d]

    def get_partition_regions(self):
        """Returns partition regions for the simulation instance.

        If member function not overriden, will simply return whatever was passed as ``partition_regions``, if any.
        Can be overriden, for example, to use partition regions defined in kqcircuits.simulations.epr.
        """
        return [PartitionRegion(**(ast.literal_eval(r) if isinstance(r, str) else r)) for r in self.partition_regions]

    @staticmethod
    def delete_instances(cell, name, index=(0,)):
        """
        Allows for deleting a sub-cell of the top 'cell' with a specific 'name'. The 'index' argument can be used to
        access more than one sub-cell sharing the same 'name', but with different appended 'index' to the 'name'.
        """
        for i in index:
            index_name = f"${i}" if i > 0 else ""
            cell_to_be_deleted = cell.layout().cell(f"{name}{index_name}")
            if cell_to_be_deleted is not None:
                # This has started causing errors on KLayout's side, protect with try-except
                try:
                    cell_to_be_deleted.delete()
                except RuntimeError as e:
                    logging.warning(f"Attempt to delete cell {name}{index_name} caused following error: {e}")

    def visualise_region(
        self,
        region: pya.Region,
        label: str,
        layer: str = "visualisation",
        points: list[pya.DPoint] | pya.DPoint | None = None,
    ) -> None:
        """Visualises given region in a dedicated layer in the preview geometry file.

        Arguments:
            region: pya.Region to visualise
            label: Label of the region, rendered using pya.DText objects
            layer: Name of the KLayout layer to place the visualised region
            points: pya.DPoint or list of DPoints to place as labels to the region.
                By default places one point at the middle of the region's boundary box.
        """
        # Not using get_sim_layer since this geometry is not part of any simulation
        visualisation_layer = self.layout.layer(layer)
        self.cell.shapes(visualisation_layer).insert(region)
        if points is None:
            points = [region.bbox().to_dtype(self.layout.dbu).center()]
        elif isinstance(points, pya.DPoint):
            points = [points]
        if len(points) <= 1:
            self.cell.shapes(visualisation_layer).insert(pya.DText(label, points[0].x, points[0].y))
        else:
            for i, p in enumerate(points):
                self.cell.shapes(visualisation_layer).insert(pya.DText(f"{label}_{i+1}", p.x, p.y))
