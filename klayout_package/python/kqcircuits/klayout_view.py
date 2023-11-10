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
import importlib
import warnings

from kqcircuits.elements.element import insert_cell_into
from kqcircuits.pya_resolver import pya, lay, is_standalone_session

from kqcircuits.defaults import default_layers, default_png_dimensions, mask_bitmap_export_layers, \
    all_layers_bitmap_hide_layers, default_faces, default_layer_props


class KLayoutView:
    """Helper object to represent the KLayout rendering environment.

    ``KLayoutView`` is a wrapper around the KLayout ``LayoutView`` and ``CellView`` objects, that represent containers
    for viewing a layout in the GUI. It provides methods to initialize the views and layout for KQCircuits, for placing
    KQCircuits ``Elements``, and for exporting images.

    Create a new view as follows::

       view = KLayoutView()

    This creates a new set of ``LayoutView``, ``CellView``, ``Layout`` and top ``Cell`` objects with layers initialized
    to the KQCircuits layer configuration. In the KLayout GUI, the new view will show as a new tab.

    Note: In standalone python mode, the user must keep a reference to the ``KLayoutView`` object in scope, otherwise
    the associated layout and cells may also go out of scope.

    When running scripts or macros in the KLayout application, the following command creates a wrapper around the
    currently active view::

        view = KLayoutView(current=True)

    This can be used in macros to act on the existing layout. The argument ``current=True`` is not available in
    standalone python mode.

    Once a view is created, new ``Elements`` can be placed with the ``insert_cell`` method.

    Several methods are available to export PNG files of the current view or specific cells and layers.
    In Jupyter notebooks, the ``show`` method displays the current view inline in the notebook.
    """
    if hasattr(lay, "LayoutView"):
        layout_view: lay.LayoutView

    def __init__(self, current=False, initialize=None, background_color="#ffffff"):
        """Initialize a ``KLayoutView`` instance.

        Args:
            current: Boolean. If True, wrap the currently active ``LayoutView`` (not available in standalone python)
            initialize: Boolean, specify whether to initialize the layout with the default layer configuration and a
                top cell. Defaults to True if ``current==False``, and to False if ``current==True``.
            background_color: Background color as HTML color code. Defaults to `"#ffffff"` (white).
            """
        if not hasattr(lay, "LayoutView"):
            # Standalone session before KLayout 0.28
            raise MissingUILibraryException("KLayoutView is not supported in standalone mode for this klayout version. "
                                            "Consider upgrading your klayout package to version 0.28 or above.")

        if initialize is None:
            initialize = not current

        if is_standalone_session():
            # Standalone session since KLayout 0.28
            if current:
                raise MissingUILibraryException("In standalone python mode only KLayoutView(current=False) " +
                                                "is supported.")
            self.layout_view = lay.LayoutView(True)  # Creates a new LayoutView in editable mode
            self.layout_view.show_layout(pya.Layout(), True)  # Adds a CellView and Layout
            self.layout_view.set_config("background-color", background_color)
        else:
            # Regular session in the KLayout GUI
            if not current or (lay.LayoutView.current() is None):
                pya.MainWindow.instance().create_layout(1)
            self.layout_view = lay.LayoutView.current()

        if initialize:
            self.add_default_layers()
            self.create_top_cell()

    def insert_cell(self, cell, trans=None, inst_name=None, label_trans=None, align_to=None, align=None,
                    rec_levels=0, **parameters):
        """Inserts a subcell into the first top cell (the very first cell in the cell window)

        It will use the given ``cell`` object or if ``cell`` is an Element class' name then directly
        take the provided keyword arguments to first create the cell object.

        If `inst_name` given, a label ``inst_name`` is added to labels layer at the ``base`` refpoint and `label_trans`
        transformation.

        Args:
            cell: cell object or Element class name
            trans: used transformation for placement. None by default, which places the subcell into the coordinate
                origin of the parent cell. If `align` and `align_to` arguments are used, `trans` is applied to the
                `cell` before alignment transform which allows for example rotation of the `cell` before placement.
            inst_name: possible instance name inserted into subcell properties under `id`. Default is None
            label_trans: relative transformation for the instance name label
            align_to: ``DPoint`` or ``DVector`` location in parent cell coordinates for alignment of cell.
                Default is None
            align: name of the ``cell`` refpoint aligned to argument ``align_to``. Default is None
            rec_levels: recursion level when looking for refpoints from subcells. Set to 0 to disable recursion.
            **parameters: PCell parameters for the element, as keyword argument

        Return:
            tuple of placed cell instance and reference points with the same transformation
        """

        return insert_cell_into(self.top_cell, cell, trans, inst_name, label_trans, align_to, align, rec_levels,
                                **parameters)

    def focus(self, cell=None):
        """Sets a given cell as the active cell, and fits the zoom level to fit the cell.

        Args:
            cell: cell to focus on, or None to focus on the currently active cell
        """
        if cell is not None and isinstance(cell, pya.Cell):
            self.layout_view.active_cellview().active().cell = cell
        self.layout_view.max_hier()
        self.layout_view.zoom_fit()

    def show(self, **kwargs):
        """In KLayout, show this LayoutView as the current in the main window.

        In standalone python, display an image of the view. Requires IPython / Jupyter. Keyword arguments are passed
        to ``KLayoutView.get_pixels``.
        """

        if is_standalone_session():
            display = importlib.import_module("IPython.display")
            display.display_png(self.get_pixels(**kwargs).to_png_data(), raw=True)
        else:
            main_window = lay.MainWindow.instance()
            for i in range(main_window.views()):
                if main_window.view(i) is self.layout_view:
                    main_window.current_view_index = i
                    break

    def close(self):
        """Closes the current LayoutView."""
        if is_standalone_session():
            self.layout_view.destroy()
        else:
            lay.MainWindow.instance().close_current_view()

    @property
    def cell_view(self) -> "lay.CellView":
        """The active ``CellView``"""
        return self.layout_view.active_cellview()

    @property
    def layout(self) -> pya.Layout:
        """The active ``Layout``"""
        return self.cell_view.layout()

    @property
    def active_cell(self) -> pya.Cell:
        """The active ``Cell``, which is shown as current top in the cellview and bold in the cell window.

        Can be set to any Cell in the layout."""
        return self.cell_view.cell

    @active_cell.setter
    def active_cell(self, cell: pya.Cell):
        self.cell_view.cell = cell

    @property
    def top_cell(self) -> pya.Cell:
        """The first top cell of the active layout."""
        cells = self.layout.top_cells()
        return cells[0] if len(cells) else None

    def clear_layers(self):
        """Clear the layer view."""
        self.layout_view.clear_layers()

    def add_default_layers(self):
        """Populate view with KQCircuits default layers. Adds the layers to the layout, and populates the layer view."""
        self.clear_layers()
        layout = self.layout
        for layer in default_layers.values():
            layout.layer(layer)
        self.layout_view.add_missing_layers()
        if default_layer_props:
            self.layout_view.load_layer_props(default_layer_props, True)

    def create_top_cell(self, top_cell_name="Top Cell"):
        """Creates a new static cell and set it as the top cell."""
        top_cell = self.layout.create_cell(top_cell_name)
        self.cell_view.cell_name = top_cell.name  # Shows the new cell
        return top_cell

    def export_layers_bitmaps(self, path, cell, filename=None, layers_set=None, face_id=None):
        """Exports each layer to a separate png image.

        Args:
            path: Directory to place the exported file in
            cell: Cell to export
            filename: Filename to export to, or None to use the cell's name.
            layers_set: A list of layer names to export, or None for default values specified in the layer configuration
            face_id: The face id for which to export the given layers, or None for general layers not associated to
                a face.
        """
        if layers_set is None:
            layers_set = mask_bitmap_export_layers
        for layer_name in layers_set:
            layer_info = resolve_default_layer_info(layer_name, face_id)
            self._export_bitmap(path, cell, filename=filename, layers_set=[layer_info])

    def export_all_layers_bitmap(self, path, cell, filename=None):
        """Exports a cell to a .png file with all layers visible

        Args:
            path: Directory to place the exported file in
            cell: Cell to export
            filename: Filename to export to, or None to use the cell's name.
        """
        self._export_bitmap(path, cell, filename=filename, layers_set='all')

    def export_pcell_png(self, path, cell, filename=None, max_size=default_png_dimensions[0]):
        """Exports a cell to a .png file no bigger than max_size at either dimension.

        Args:
            path: Directory to place the exported file in
            cell: Cell to export
            filename: Filename to export to, or None to use the cell's name.
            max_size: Maximum size of the image.
        """

        zoom = cell.dbbox()
        x, y = zoom.width(), zoom.height()
        if max_size * x / y < max_size - 200 :   # 200x100 is enough for the sizebar
            size = (max_size * x / y + 200, max_size)
        else:
            size = (max_size, max_size * y / x + 100)
        self._export_bitmap(path, cell, filename=filename, layers_set='all', z_box=zoom, pngsize=size)

    def get_pixels(self, cell=None, width=None, height=None, layers_set=None, box=None):
        """Returns a PixelBuffer render of the current view.

        This method first zooms to fit the whole layout and shows all hierarchy levels. If either ``width`` or
        ``height`` is specified, the other is chosen correspondingly to keep the same viewport aspect ratio. If neither
        is specified, the current viewport size is used.

        Args:
            cell: Cell to render, or None to render the currently active cell.
            width: image width in pixels, or None for automatic.
            height: image height in pixels, or None for automatic.
            layers_set: list of layer names to export, or None for the default set.
            box: DBox area to show, or None for the full layout.

        Returns: PixelBuffer
        """

        if width is None and height is None:
            width = self.layout_view.viewport_width()
            height = self.layout_view.viewport_height()
        elif width is None:
            width = height * self.layout_view.viewport_width() / self.layout_view.viewport_height()
        elif height is None:
            height = width * self.layout_view.viewport_height() / self.layout_view.viewport_width()
        if layers_set is not None:
            layers_set = [resolve_default_layer_info(layer_name) for layer_name in layers_set]

        def export_callback():
            pixel_buffer = self.layout_view.get_pixels(width, height)
            return pixel_buffer

        return self._export_bitmap_configure(export_callback, cell, layers_set, box)

    @staticmethod
    def get_active_cell_view():
        """Gets the currently active CellView. Not supported in standalone python mode.

        Deprecated, use ``KLayoutView(current=True).cell_view`` to get the same behavior."""
        warnings.warn('KLayoutView.get_active_cell_view will be deprecated. ' +
                      'Use instance property KLayoutView.cell_view instead.', DeprecationWarning)
        return lay.CellView.active()

    @staticmethod
    def get_active_layout():
        """Gets the layout of the currently active CellView. Not supported in standalone python mode.

        Deprecated, use ``KLayoutView(current=True).layout`` to get the same behavior. If you already have a
        KLayoutView instance, use the ``layout`` property of that instance instead."""
        warnings.warn('KLayoutView.get_active_layout will be deprecated. ' +
                      'Use instance property KLayoutView.layout instead.', DeprecationWarning)
        return lay.CellView.active().layout()

    @staticmethod
    def get_active_cell():
        """Gets the active cell of the currently active CellView. Not supported in standalone python mode.

        Deprecated, use ``KLayoutView(current=True).active_cell`` to get the same behavior. If you already have a
        KLayoutView instance, use the ``active_cell`` property of that instance instead."""
        warnings.warn('KLayoutView.get_active_cell will be deprecated. ' +
                      'Use instance property KLayoutView.active_cell instead.', DeprecationWarning)
        return lay.CellView.active().cell

    # ********************************************************************************
    # PRIVATE METHODS
    # ********************************************************************************

    def _export_bitmap(self, path, cell=None, filename=None, layers_set=None, z_box=None,
                       pngsize=default_png_dimensions):

        if filename is None:
            filename = cell.name
        if layers_set is None:
            layers_set = [resolve_default_layer_info(layer_name) for layer_name in mask_bitmap_export_layers]

        if len(layers_set) == 1:
            layer_str = "-" + layers_set[0].name
        else:
            layer_str = ""
        cell_png_name = path / "{}{}.png".format(filename, layer_str)

        def export_callback():
            self.layout_view.save_image(str(cell_png_name), pngsize[0], pngsize[1])

        self._export_bitmap_configure(export_callback, cell, layers_set, z_box)

    def _export_bitmap_configure(self, export_callback, cell, layers_set, z_box):
        """ Common configuration for export functions. """

        def get_visibility_state():
            """Get the current layer visibility and drawing focus state"""
            current_layer_visibility = [_layer.visible for _layer in self.layout_view.each_layer()]
            current_cell = self.layout_view.active_cellview().cell
            current_hier = (self.layout_view.min_hier_levels, self.layout_view.max_hier_levels)
            current_zoom = self.layout_view.box()
            return current_layer_visibility, current_cell, current_zoom, current_hier

        def restore_visibility_state(layer_visibility, cell, zoom, hier):
            """Restore the layer visibility and drawing focus state.
            Assumes order of layers has not changed since calling ``get_visibility_state`` """
            for _layer, _visible in zip(self.layout_view.each_layer(), layer_visibility):
                _layer.visible = _visible
            self.layout_view.active_cellview().cell = cell
            self.layout_view.min_hier_levels, self.layout_view.max_hier_levels = hier
            self.layout_view.zoom_box(zoom)

        visibility_state = get_visibility_state()

        if cell is not None:
            self.layout_view.active_cellview().cell = cell

        self.layout_view.max_hier()
        self.layout_view.zoom_fit()  # Has to be done also before zoom_box

        if z_box is not None:
            self.layout_view.zoom_box(z_box)

        if layers_set is None or layers_set == "all":
            for layer in self.layout_view.each_layer():
                layer.visible = True

                for layer_to_hide in all_layers_bitmap_hide_layers:
                    if layer.source_layer == layer_to_hide.layer and layer.source_datatype == layer_to_hide.datatype:
                        layer.visible = False
                        break
        else:
            layer_infos = self.layout.layer_infos()
            for layer in self.layout_view.each_layer():
                # need to avoid hiding layer groups, because that could hide also layers in layers_set
                is_layer_group = True
                for layer_info in layer_infos:
                    if pya.LayerInfo(layer.source_layer, layer.source_datatype).is_equivalent(layer_info):
                        is_layer_group = False
                        break
                if not is_layer_group:
                    layer.visible = False
                for layer_to_show in layers_set:
                    if layer.source_layer == layer_to_show.layer \
                            and layer.source_datatype == layer_to_show.datatype:
                        layer.visible = True
                        break

        if hasattr(lay, "Application"):
            # Make sure the layer property changes are reflected before saving the image
            lay.Application.instance().process_events()
        else:
            # Undocumented method timer does basically the same thing as process_events in GUI.
            self.layout_view.timer()

        export_return = export_callback()

        restore_visibility_state(*visibility_state)

        return export_return


class MissingUILibraryException(Exception):
    def __init__(self, message="Missing KLayout UI library."):
        Exception.__init__(self, message)


def resolve_default_layer_info(layer_name, face_id=None):
    """Returns LayerInfo based on default_layers.

    Assumes that layer_name is valid, and that face_id is valid or None.

    Args:
        layer_name: layer name (without face prefix for face-specific layers)
        face_id: id of the face from which this layer should be
    """
    if face_id:
        if layer_name in default_faces[face_id]:
            return default_faces[face_id][layer_name]
        else:
            return default_layers[layer_name]
    else:
        return default_layers[layer_name]
