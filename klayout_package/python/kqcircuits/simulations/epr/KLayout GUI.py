from kqcircuits.pya_resolver import lay, pya

class Element:

    def post_build(self):

        if not self._epr_show:
            return

        self._show_epr_cross_section_cuts()
        self._show_epr_partition_regions()


    def _show_epr_cross_section_cuts(self):

        layout_view = lay.LayoutView.current()

        if layout_view is None:
            return

        # remove old markers before redraw
        layout_view.clear_markers()

        # allow drawing only when exactly one object is selected
        selected = list(layout_view.each_object_selected())

        if len(selected) != 1:
            return

        inst_path = selected[0]
        trans = inst_path.inst().dcplx_trans

        # dynamically load epr module
        epr_module = load_epr_module(self.__class__.__name__)

        if epr_module is None:
            return

        cuts = epr_module.correction_cuts(self)

        for cut_name, cut_data in cuts.items():

            if not getattr(self, "_epr_cross_section_cut", False):
                continue

            p1 = trans * cut_data["p1"]
            p2 = trans * cut_data["p2"]

            # create line marker
            line_marker = pya.Marker()
            line_marker.set_path([p1, p2], 0)

            line_marker.line_width = 2
            line_marker.vertex_size = 4

            layout_view.add_marker(line_marker)

            # endpoint text markers
            text1 = pya.Marker()
            text1.set_text(f"{cut_name}_p1", p1)

            text2 = pya.Marker()
            text2.set_text(f"{cut_name}_p2", p2)

            layout_view.add_marker(text1)
            layout_view.add_marker(text2)


    def _show_epr_partition_regions(self):

        layout_view = lay.LayoutView.current()

        if layout_view is None:
            return

        selected = list(layout_view.each_object_selected())

        if len(selected) != 1:
            return

        inst_path = selected[0]
        trans = inst_path.inst().dcplx_trans

        epr_module = load_epr_module(self.__class__.__name__)

        if epr_module is None:
            return

        regions = epr_module.partition_regions(self)

        for region in regions:

            param_name = f"_epr_part_reg_{region.name}"

            if not getattr(self, param_name, False):
                continue

            polygon = transform_polygon(region.region, trans)

            marker = pya.Marker()
            marker.set_polygon(polygon)

            marker.line_width = 2
            marker.vertex_size = 3
            marker.dither_pattern = 2
            marker.halo = 1

            layout_view.add_marker(marker)

            # text marker in polygon center
            center = polygon.bbox().center()

            text_marker = pya.Marker()
            text_marker.set_text(region.name, center)

            layout_view.add_marker(text_marker)


def load_epr_module(element_name):

    module_name = f"kqcircuits.simulations.epr.{element_name.lower()}"

    try:
        return importlib.import_module(module_name)

    except Exception:
        return None


def transform_polygon(polygon, trans):

    transformed_points = []

    for point in polygon.each_point_hull():
        transformed_points.append(trans * point)

    return pya.DPolygon(transformed_points)
