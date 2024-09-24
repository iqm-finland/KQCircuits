# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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

from kqcircuits.pya_resolver import pya


def get_list_of_two(dims):
    """Returns list of two terms when 'dims' is given as a scalar or list."""
    if isinstance(dims, list):
        return [dims[0], dims[1]]
    return [dims, dims]


class PartitionRegion:
    """Class to enable partitioning of simulation geometry into sub-regions"""

    def __init__(
        self,
        name="part",
        region=None,
        z=None,
        face=None,
        vertical_dimensions=None,
        metal_edge_dimensions=None,
        visualise=False,
    ):
        """
        Args:
            name: Suffix of the partition layers. Must not end with a number.
            region: Area to which the partition region is limited. Can be given as pya.DBox, pya.DPolygon, or list of
                those. Accepts also pya.Region if called from custom Simulation.get_partition_regions function.
                Use None to cover full domain.
            z: Lower and upper bound for the partition region as scalar or list. Use None to cover full height.
            face: The face name to which the partition region is applied. If this is used, the vertical_dimensions
                and metal_edge_dimensions are applied.
            vertical_dimensions: Vertical dimensions of the partition region on face as scalar or list. The terms in the
                list correspond to expansion dimensions into directions of substrate and vacuum, respectively. Scalar
                means the substrate and vacuum expansions are equal. This is applied only if face is given.
            metal_edge_dimensions: Lateral dimensions to limit the partition region next to the metal edges. If given as
                list, the terms correspond to expansions into directions of gap and metal, respectively. If given as
                scalar, the gap and metal expansions are equal. Use None to disable the metal edge limitation. This is
                applied only if face is given.
            visualise: Visualises the partition region in the preview of the simulation geometry.
        """
        if name[-1] in "0123456789":
            raise ValueError(f"PartitionRegion name must not end with a number, but {name} is given.")
        if name == "":
            raise ValueError("PartitionRegion name must not be an empty string.")
        if any(n in name for n in ["layerMA", "layerMS", "layerSA", "substrate", "vacuum"]):
            raise ValueError(f"PartitionRegion name {name} contains reserved layer name.")
        self.name = name
        self.region = region
        self.z = z
        self.face = face
        self.vertical_dimensions = vertical_dimensions
        self.metal_edge_dimensions = metal_edge_dimensions
        self.visualise = visualise

    def limit_box(self, bottom, top, box, dbu):
        """Limits the region and z-levels into simulation dimensions.

        Args:
            bottom: bottom of the simulation domain.
            top: top of the simulation domain.
            box: lateral dimensions of simulation domain as pya.DBox.
            dbu: layout database unit
        """
        # update self.z using bottom and top
        self.z = get_list_of_two(self.z)
        if self.z[0] is None or self.z[0] < bottom:
            self.z[0] = bottom
        if self.z[1] is None or top < self.z[1]:
            self.z[1] = top

        # update self.region using box
        box_region = pya.Region(box.to_itype(dbu))
        if self.region is None:
            self.region = box_region
        elif isinstance(self.region, pya.Region):
            self.region = self.region & box_region
        elif isinstance(self.region, list):
            merged_region = pya.Region()
            for r in self.region:
                merged_region += pya.Region(r.to_itype(dbu))
            self.region = merged_region & box_region
        else:
            self.region = pya.Region(self.region.to_itype(dbu)) & box_region

    def limit_face(self, z, sign, metal_region, etch_region, dbu):
        """Limits the region and z-levels on face. Function limit_box should be called once before this.

        Args:
            z: z-level of the face
            sign: 1 if substrate is below vacuum, -1 otherwise
            metal_region: metallization area as pya.Region
            etch_region: area where metal is etched away as pya.Region
            dbu: layout database unit
        """
        # Reset face to indicate that face limitation is applied
        self.face = None

        # update self.z using self.vertical_dimensions
        vd = get_list_of_two(self.vertical_dimensions)
        if vd[sign < 0] is not None and self.z[0] < z - vd[sign < 0]:
            self.z[0] = z - vd[sign < 0]
        if vd[sign > 0] is not None and z + vd[sign > 0] < self.z[1]:
            self.z[1] = z + vd[sign > 0]

        # update self.region using self.metal_edge_dimensions
        ed = get_list_of_two(self.metal_edge_dimensions)
        if ed[0] is not None:
            self.region &= metal_region.sized(ed[0] / dbu)
        if ed[1] is not None:
            self.region &= etch_region.sized(ed[1] / dbu)
