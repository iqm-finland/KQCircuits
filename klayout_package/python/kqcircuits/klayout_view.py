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


from autologging import logged, traced

from kqcircuits.pya_resolver import pya

from kqcircuits.defaults import default_layers, default_png_dimensions, mask_bitmap_export_layers, \
    all_layers_bitmap_hide_layers, default_faces, SRC_PATHS


@traced
@logged
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

@traced
@logged
class KLayoutView():
    """KLayout layout view wrapper with helper methods."""

    def __init__(self, view=None, current=False, initialize=False):
        super().__init__()
        if not hasattr(pya, "Application"):
            error = MissingUILibraryException()
            self.__log.exception("Cannot find KLayout UI library.", exc_info=error)
            raise error
        if view is None:
            if not current or pya.LayoutView.current() is None:
                pya.MainWindow.instance().create_layout(1)
            self.layout_view = pya.LayoutView.current()
        else:
            if isinstance(view, pya.LayoutView):
                self.layout_view = view
            else:
                error = InvalidViewException(view)
                self.__log.exception("The view is not an instance of pya.LayoutView", exc_info=error)
                raise error
        if initialize:
            self.add_default_layers()

    @staticmethod
    def get_active_cell_view():
        return pya.CellView.active()

    @staticmethod
    def get_active_layout():
        return pya.CellView.active().layout()

    @staticmethod
    def get_active_cell():
        return pya.CellView.active().cell

    def focus(self, cell):
        """Clear view."""
        if cell is not None and isinstance(cell, pya.Cell):
            pya.CellView.active().cell = cell
        self.layout_view.max_hier()
        self.layout_view.zoom_fit()

    def clear_layers(self):
        """Clear view."""
        self.layout_view.clear_layers()

    def add_default_layers(self):
        """Populate view with KQCircuits default layers."""
        self.clear_layers()
        layout = pya.CellView.active().layout()
        for layer in default_layers.values():
            layout.layer(layer)
        self.layout_view.add_missing_layers()
        self.layout_view.load_layer_props(str(SRC_PATHS[-1].joinpath("default_layer_props.lyp")), True)

    def export_layers_bitmaps(self, path, cell, filename="", layers_set=mask_bitmap_export_layers,
                              face_id=None):
        # pylint: disable=dangerous-default-value
        if filename == "":
            filename = cell.name
        for layer_name in layers_set:
            layer_info = resolve_default_layer_info(layer_name, face_id)
            self._export_bitmap(path, cell, filename=filename, layers_set=[layer_info], face_id=face_id)

    def export_all_layers_bitmap(self, path, cell, filename="", face_id=None):
        if filename == "":
            filename = cell.name
        self._export_bitmap(path, cell, filename=filename, layers_set='all', face_id=face_id)

    def export_pcell_png(self, path, cell, filename, max_size=default_png_dimensions[0]):
        """Exports pcell to .png file no bigger than max_size at either dimension."""

        zoom = cell.dbbox()
        x, y = zoom.width(), zoom.height()
        if max_size * x / y < max_size - 200 :   # 200x100 is enough for the sizebar
            size = (max_size * x / y + 200, max_size)
        else:
            size = (max_size, max_size * y / x + 100)
        self._export_bitmap(path, cell, filename=filename, layers_set='all', z_box=zoom, pngsize=size)

    # ********************************************************************************
    # PRIVATE METHODS
    # ********************************************************************************

    def _export_bitmap(self, path, cell=None, filename="", layers_set=mask_bitmap_export_layers,
                       z_box=pya.DBox(0, 0, 0, 0), face_id=None, pngsize=default_png_dimensions):
        # pylint: disable=dangerous-default-value
        if cell is None:
            self.__log.warning("Cannot export bitmap of unspecified cell. Defaulting to active cell in view.")
            cell = pya.CellView.active().cell
        elif not isinstance(cell, pya.Cell):
            self.__log.warning("Cannot export bitmap of invalid cell. Defaulting to active cell in view.")
            cell = pya.CellView.active().cell
        else:
            pya.CellView.active().cell = cell
        # TODO - undo this side-effect
        self.layout_view.zoom_fit()  # Has to be done also before zoom_box

        if filename == "":
            filename = cell.name

        if z_box != pya.DBox(0, 0, 0, 0):
            self.layout_view.zoom_box(z_box)

        if len(layers_set) == 1:
            layer_str = " " + layers_set[0].name
        else:
            layer_str = " " + face_id if face_id else ""
        cell_png_name = path / "{}{}.png".format(filename, layer_str)

        # first make all layers visible, then take a screenshot
        if layers_set == "all":

            # TODO - undo this side-effect
            for layer in self.layout_view.each_layer():
                layer.visible = True

            # hide unwanted layers from the bitmap files
            for layer in self.layout_view.each_layer():
                for layer_to_hide in all_layers_bitmap_hide_layers:
                    if layer.source_layer == layer_to_hide.layer and layer.source_datatype == layer_to_hide.datatype:
                        layer.visible = False
                        break

            self.layout_view.save_image(str(cell_png_name), pngsize[0], pngsize[1])
        # take screenshots of only specific layers
        else:
            # get the current visibility condition of the layers
            current_layer_visibility = []
            for layer in self.layout_view.each_layer():
                current_layer_visibility.append(layer.visible)

            # only show the wanted layers
            layer_infos = self.get_active_layout().layer_infos()
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

            self.layout_view.save_image(str(cell_png_name), pngsize[0], pngsize[1])

            # return the layer visibility to before screenshot state
            for i, layer in enumerate(self.layout_view.each_layer()):
                layer.visible = current_layer_visibility[i]


@traced
class ViewException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


@traced
class MissingUILibraryException(ViewException):
    def __init__(self):
        ViewException.__init__(
            self,
            "Missing KLayout UI library."
        )


@traced
class InvalidViewException(ViewException):
    def __init__(self, view):
        ViewException.__init__(
            self,
            "Invalid layout view [{}].".format(str(view))
        )
