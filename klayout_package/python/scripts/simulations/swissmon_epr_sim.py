"""EPR marker preview utilities for KLayout GUI.

This module provides utilities for previewing EPR partition regions and
correction cross-section cuts using KLayout Marker objects instead of
fabrication layers.

The implementation avoids geometry collisions with fabrication layers and
supports live preview updates while editing PCells.
"""

from __future__ import annotations

from importlib import import_module

from kqcircuits.pya_resolver import lay, pya
from kqcircuits.util.parameters import Param, pdt


class EPRMarkerMixin:
    """Mixin class for displaying EPR preview geometry using markers.

    Features
    --------
    - Displays correction cuts as line markers
    - Displays partition regions as polygon markers
    - Applies instance transformations correctly
    - Prevents lingering and duplicated markers
    - Safely handles invalid selection states
    """

    _epr_show = Param(
        pdt.TypeBoolean,
        "Show EPR preview",
        False,
    )

    _epr_cross_section_cut = Param(
        pdt.TypeBoolean,
        "Show EPR correction cuts",
        False,
    )

    # Dynamically added partition-region parameters:
    #
    # _epr_part_reg_crossleft
    # _epr_part_reg_crossright
    # etc.

    def post_build(self):
        """Refresh EPR markers after element build."""
        super().post_build()
        self._refresh_epr_markers()

    def _refresh_epr_markers(self):
        """Clear and redraw all EPR markers."""

        layout_view = lay.LayoutView.current()

        if layout_view is None:
            return

        # Clear previous markers to avoid duplication or lingering shapes.
        layout_view.clear_markers()

        if not getattr(self, "_epr_show", False):
            return

        selected_objects = list(layout_view.each_object_selected())

        if len(selected_objects) != 1:
            print(
                "[EPR] Expected exactly one selected instance, "
                f"got {len(selected_objects)}."
            )
            return

        inst_path = selected_objects[0]
        transform = inst_path.inst().dcplx_trans

        epr_module = self._load_epr_module()

        if epr_module is None:
            return

        if getattr(self, "_epr_cross_section_cut", False):
            self._draw_cross_section_cuts(
                layout_view,
                epr_module,
                transform,
            )

        self._draw_partition_regions(
            layout_view,
            epr_module,
            transform,
        )

    def _load_epr_module(self):
        """Load the EPR module corresponding to this element."""

        try:
            module_name = self.__module__.split(".")[-1]

            return import_module(
                f"kqcircuits.simulations.epr.{module_name}"
            )

        except Exception as exc:
            print(f"[EPR] Failed to load EPR module: {exc}")
            return None

    def _draw_cross_section_cuts(
        self,
        layout_view,
        epr_module,
        transform,
    ):
        """Draw correction cross-section cuts as markers.

        Parameters
        ----------
        layout_view :
            Active KLayout layout view.
        epr_module :
            Dynamically imported EPR module.
        transform :
            Instance transformation applied to marker geometry.
        """

        if not hasattr(epr_module, "correction_cuts"):
            return

        try:
            cuts = epr_module.correction_cuts(self)

        except Exception as exc:
            print(
                "[EPR] Failed to generate correction cuts: "
                f"{exc}"
            )
            return

        for cut_name, segment in cuts.items():

            point_a, point_b = segment

            transformed_a = transform * point_a
            transformed_b = transform * point_b

            line_marker = pya.Marker()

            line_marker.set(
                pya.DBox(
                    transformed_a,
                    transformed_b,
                )
            )

            line_marker.line_width = 3
            line_marker.vertex_size = 6
            line_marker.halo = 1

            layout_view.add_marker(line_marker)

            start_label = pya.Marker()

            start_label.set_text(
                f"{cut_name}_A",
                transformed_a,
            )

            start_label.line_width = 2

            layout_view.add_marker(start_label)

            end_label = pya.Marker()

            end_label.set_text(
                f"{cut_name}_B",
                transformed_b,
            )

            end_label.line_width = 2

            layout_view.add_marker(end_label)

    def _draw_partition_regions(
        self,
        layout_view,
        epr_module,
        transform,
    ):
        """Draw EPR partition regions as polygon markers.

        Parameters
        ----------
        layout_view :
            Active KLayout layout view.
        epr_module :
            Dynamically imported EPR module.
        transform :
            Instance transformation applied to marker geometry.
        """

        if not hasattr(epr_module, "partition_regions"):
            return

        try:
            regions = epr_module.partition_regions(self)

        except Exception as exc:
            print(
                "[EPR] Failed to generate partition regions: "
                f"{exc}"
            )
            return

        for region in regions:

            region_name = region.name

            parameter_name = (
                f"_epr_part_reg_{region_name}"
            )

            if not getattr(self, parameter_name, False):
                continue

            transformed_points = [
                transform * point
                for point in region.region.points
            ]

            transformed_polygon = pya.DPolygon(
                transformed_points
            )

            polygon_marker = pya.Marker()

            polygon_marker.set_polygon(
                transformed_polygon
            )

            polygon_marker.line_width = 2
            polygon_marker.vertex_size = 4
            polygon_marker.halo = 1

            # Use dithering to improve visibility.
            polygon_marker.dither_pattern = 2

            layout_view.add_marker(
                polygon_marker
            )

            center_point = (
                transformed_polygon
                .bbox()
                .center()
            )

            text_marker = pya.Marker()

            text_marker.set_text(
                region_name,
                center_point,
            )

            text_marker.line_width = 2

            layout_view.add_marker(
                text_marker
            )
