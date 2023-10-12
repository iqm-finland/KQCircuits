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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).
from kqcircuits.masks.mask_layout import MaskLayout


class MultiFaceMaskLayout:
    """Class representing multiple mask layouts, corresponding to multiple faces on the same wafer.

    This is a helper class to create multiple ``MaskLayout`` instances, one for each face, and set the same properties
    and chips map for each, and a container for the created mask layouts. It also provides `add_chips_map` that
    distributes over each containing `MaskLayout.add_chips_map`.

    The usual way to instantiate ``MultiFaceMaskLayout`` is through ``MaskSet.add_multi_face_mask_layout``.

    Attributes:
        face_ids: List of face ids to include in this mask layout
        mask_layouts: Dictionary of {face_id: mask_layout} of the individual ``MaskLayouts`` contained in this class
    """
    def __init__(self, layout, name, version, with_grid, face_ids, chips_map=None, extra_face_params=None,
                 mask_layout_type=MaskLayout, **kwargs):
        """Create a multi face mask layout, which can be used to make masks with matching chip maps on multiple faces.

        A ``MaskLayout`` is created of each face in ``face_ids``. If ``face_ids`` is a list, the individual mask layouts
        all have identical parameters. To specify some parameters differently for each mask layout, supply ``face_ids``
        as a dictionary ``{face_ids: extra_params}``, where ``extra_params`` is a dictionary of arguments passed only
        to the mask layout for that face id. These override ``kwargs`` if they contain the same keys.

        By default, ``bbox_face_ids`` is set to ``list(face_ids)`` for all mask layouts.

        Args:
            layout: Layout to use
            name: name of the mask
            version: version of the mask
            with_grid: if True, ground grids are generated
            face_ids: either a list of face ids to include, or a dictionary of ``{face_id: extra_params}``, where
                ``extra_params`` is a dictionary of keyword arguments to apply only to this mask layout.
            chips_map: Chips map to use, or None to use an empty chips map.
            mask_layout_type: optional subclass of MaskLayout to use
            kwargs: any keyword arguments are passed to all containing mask layouts.
        """
        self.face_ids = face_ids
        self.mask_layouts = {}

        for face_id in face_ids:
            all_kwargs = {'bbox_face_ids': self.face_ids}
            all_kwargs.update(kwargs)
            if extra_face_params is not None and face_id in extra_face_params:
                all_kwargs.update(**extra_face_params[face_id])
            self.mask_layouts[face_id]: MaskLayout = mask_layout_type(
                layout=layout,
                name=name,
                version=version,
                with_grid=with_grid,
                face_id=face_id,
                chips_map=chips_map if chips_map is not None else [[]],
                **all_kwargs
            )

    def add_chips_map(self, chips_map, **kwargs):
        for face_id in self.face_ids:
            self.mask_layouts[face_id].add_chips_map(chips_map, **kwargs)
