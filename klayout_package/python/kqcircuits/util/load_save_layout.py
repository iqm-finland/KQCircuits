# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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


def load_layout(filename, layout: pya.Layout, **opts) -> None:
    """Loads ``Layout`` from file.

    The default LoadLayoutOptions of KLayout are employed with following exceptions:
    * This function sets cell_conflict_resolution = RenameCell by default (conflicting cells will be renamed).
    * The LoadLayoutOptions can be modified via keyword arguments.

    Args:
        filename: The name of the file to load.
        layout: The layout object into which the file is loaded.
        opts: Custom LoadLayoutOptions as keyword arguments.
    """
    load_opts = pya.LoadLayoutOptions()
    load_opts.cell_conflict_resolution = pya.LoadLayoutOptions.CellConflictResolution.RenameCell
    for key, value in opts.items():
        if not hasattr(load_opts, key):
            raise NotImplementedError(f"pya.LoadLayoutOptions has no attribute called {key}.")
        setattr(load_opts, key, value)
    layout.read(str(filename), load_opts)


def save_layout(
    filename,
    layout: pya.Layout,
    cells: list[pya.Cell] | None = None,
    layers: list[pya.LayerInfo] | None = None,
    **opts,
) -> None:
    """Saves ``Layout`` to file.

    The default SaveLayoutOptions of KLayout are employed with following exceptions:
    * This function calls set_format_from_filename to select file format according to the file's extension.
    * By default write_context_info = False to enable saving cells as static cells.
    * If cells or layers are specified, only given instances will be saved.
    * The SaveLayoutOptions can be modified via keyword arguments.

    Args:
        filename: The name of the file to save.
        layout: The layout object whose geometry will be saved.
        cells: List of pya.Cell objects to indicate which cells are saved. Save all cells if not specified.
        layers: List of pya.LayerInfo objects to indicate which layers are saved. Save all layers if not specified.
        opts: Custom SaveLayoutOptions as keyword arguments.
    """
    save_opts = pya.SaveLayoutOptions()
    save_opts.set_format_from_filename(filename)
    save_opts.write_context_info = False
    if cells is not None:
        save_opts.clear_cells()
        for cell in cells:
            save_opts.add_cell(cell.cell_index())
    if layers is not None:
        save_opts.deselect_all_layers()
        for layer in layers:
            save_opts.add_layer(layout.layer(layer), layer)
    for key, value in opts.items():
        if not hasattr(save_opts, key):
            raise NotImplementedError(f"pya.SaveLayoutOptions has no attribute called {key}.")
        setattr(save_opts, key, value)
    layout.write(str(filename), save_opts)
