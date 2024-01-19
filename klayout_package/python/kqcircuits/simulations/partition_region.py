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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).

from kqcircuits.pya_resolver import pya


class PartitionRegion:
    """ Class to enable partitioning of simulation geometry into sub-regions
    """
    def __init__(self, name='part', vertical_dimensions=1.0, metal_edge_dimensions=None, region=None, face_ids=None):
        """
        Args:
            name: Suffix of the partition layers. Must not end with a number.
            vertical_dimensions: Vertical dimensions of the partition region as scalar or list. The terms in the list
                correspond to expansion dimensions into directions of substrate and vacuum, respectively. Scalar means
                the substrate and vacuum expansions are equal.
            metal_edge_dimensions: Lateral dimensions to limit the partition region next to the metal edges. If given as
                list, the terms correspond to expansions into directions of gap and metal, respectively. If given as
                scalar, the gap and metal expansions are equal. Use None to disable the metal edge limitation.
            region: Area to which the partition region is limited. Can be given as pya.DBox, pya.DPolygon, or list of
                pya.DPolygons. Use None to cover full domain.
            face_ids: List of face names to which the partition region is applied. Use None to apply on all faces.
        """
        if name[-1] in '0123456789':
            raise ValueError(f"PartitionRegion name must not end with a number, but {name} is given.")
        if name == "":
            raise ValueError("PartitionRegion name must not be an empty string.")
        self.name = name
        self.vertical_dimensions = vertical_dimensions
        self.metal_edge_dimensions = metal_edge_dimensions
        self.region = region
        self.face_ids = face_ids

    def get_vertical_dimension(self):
        """Returns the partition region expansion dimensions towards substrate and vacuum, respectively."""
        if isinstance(self.vertical_dimensions, list):
            return self.vertical_dimensions[0], self.vertical_dimensions[1]
        return self.vertical_dimensions, self.vertical_dimensions

    def covers_face(self, face_id):
        """Returns True only if the metal edge region covers given face name.

        Args:
            face_id: name of the face as string
        """
        if self.face_ids is None:
            return True
        return face_id in self.face_ids

    def get_partition_region(self, metal_region, etch_region, full_region, dbu):
        """Returns the region of the partitioning.

        Args:
            metal_region: metallization area
            etch_region: area where metal is etched away
            full_region: full area where partition region can be applied
            dbu: layout database unit
        """
        if self.region is None:
            limited_region = full_region
        elif isinstance(self.region, list):
            limited_region = pya.Region([r.to_itype(dbu) for r in self.region]) & full_region
        else:
            limited_region = pya.Region(self.region.to_itype(dbu)) & full_region

        if self.metal_edge_dimensions is None:
            return limited_region

        if isinstance(self.metal_edge_dimensions, list):
            dim_gap = self.metal_edge_dimensions[0]
            dim_metal = self.metal_edge_dimensions[1]
        else:
            dim_gap = dim_metal = self.metal_edge_dimensions
        return metal_region.sized(dim_gap / dbu) & etch_region.sized(dim_metal / dbu) & limited_region
