from autologging import logged, traced

from kqcircuits.pya_resolver import pya

from kqcircuits.defaults import default_layers, default_png_dimensions, lay_id_set


@logged
@traced
class KLayoutView():
    """KLayout layout view wrapper with helper methods.
    """

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
                self.__log.exception(exc_info=error)
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
        """Clear view.
        """
        if cell is not None and isinstance(cell, pya.Cell):
            pya.CellView.active().cell = cell
        self.layout_view.max_hier()
        self.layout_view.zoom_fit()

    def clear_layers(self):
        """Clear view.
        """
        self.layout_view.clear_layers()

    def add_default_layers(self):
        """Populate view with KQCircuits default layers.
        """
        self.clear_layers()
        layout = pya.CellView.active().layout()
        for layer in default_layers.values():
            layout.layer(layer)
        self.layout_view.add_missing_layers()

    def export_layers_bitmaps(self, path, cell, cell_name="", cell_version=1, layers_set=lay_id_set):
        if (cell_name == ''):
            cell_name = cell.name
        for lay_id in range(len(layers_set)):
            layer_png_name = "{}_layer_{}".format(cell_name, layers_set[lay_id].layer)
            self.__export_bitmap(path, cell, cell_name=layer_png_name, cell_version=cell_version, layers_set=[layers_set[lay_id]])

    def export_all_layers_bitmap(self, path, cell, cell_name="", cell_version=1):
        if (cell_name == ''):
            cell_name = cell.name
        self.__export_bitmap(path, cell, cell_name=cell_name, cell_version=cell_version, layers_set='all')

    # ********************************************************************************
    # PRIVATE METHODS
    # ********************************************************************************

    def __export_bitmap(self, path, cell=None, cell_name="", cell_version=1, layers_set=lay_id_set, z_box=pya.DBox(0, 0, 0, 0)):
        if cell is None:
            self.__log.warning("Cannot export bitmap of unspecified cell. Defaulting to active cell in view.")
            cell = pya.CellView.active().cell
        elif not isinstance(cell, pya.Cell):
            self.__log.warning("Cannot export bitmap of invalid cell. Defaulting to active cell in view.")
            cell = pya.CellView.active().cell
        else:
            pya.CellView.active().cell = cell
        self.layout_view.zoom_fit()  # Has to be done also before zoom_box

        if (cell_name == ""):
            cell_name = cell.name

        if z_box != pya.DBox(0, 0, 0, 0):
            self.layout_view.zoom_box(z_box)

            # custom_png_name = path / "{}.png".format(cell_name)
            # layout_view.save_image(str(custom_png_name), default_png_dimensions[0], default_png_dimensions[1])

        filename = "{}_v{}".format(cell_name, str(cell_version))
        cell_png_name = path / "{}.png".format(filename)

        # first make all layers visible, then take a screenshot
        if (layers_set == 'all'):

            layers_to_hide = [
                default_layers["annotations"],
                default_layers["annotations 2"],
                default_layers["mask graphical rep"],
            ]

            for layer in self.layout_view.each_layer():
                layer.visible = True

                # hide unwanted annotations layers from the bitmap files
            for layer in self.layout_view.each_layer():
                for layer_to_hide in layers_to_hide:
                    if layer.source_layer == layer_to_hide.layer and layer.source_datatype == layer_to_hide.datatype:
                        layer.visible = False
                        break

            self.layout_view.save_image(str(cell_png_name), default_png_dimensions[0], default_png_dimensions[1])
        # take screenshots of only specific layers
        else:
            # get the current visibility condition of the layers
            current_layer_visibility = []
            for layer in self.layout_view.each_layer():
                current_layer_visibility.append(layer.visible)

            # only show the wanted layers
            for layer in self.layout_view.each_layer():
                layer.visible = False
                for layer_to_show in layers_set:
                    if layer.source_layer == layer_to_show.layer and layer.source_datatype == layer_to_show.datatype:
                        layer.visible = True
                        break

            self.layout_view.save_image(str(cell_png_name), default_png_dimensions[0], default_png_dimensions[1])

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
