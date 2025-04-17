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
from kqcircuits.simulations.export.cross_section.cut_simulation import CutSimulation
from kqcircuits.simulations.simulation import Simulation


def create_cross_sections_from_simulations(
    simulations: list[Simulation],
    cuts: tuple[pya.DPoint, pya.DPoint] | list[tuple[pya.DPoint, pya.DPoint]],
    ma_permittivity: float = 0,
    ms_permittivity: float = 0,
    sa_permittivity: float = 0,
    ma_thickness: float = 0,
    ms_thickness: float = 0,
    sa_thickness: float = 0,
    vertical_cull: tuple[float, float] | None = None,
    mer_box: pya.DBox | list[pya.DBox] | None = None,
    magnification_order: int = 0,
    layout: pya.Layout | None = None,
    sim_names: list[str] | None = None,
    sim_class: type[CutSimulation] = CutSimulation,
    **kwargs,
) -> list[CutSimulation]:
    """Create cross-sections of all simulation geometries in the list.
    Will set 'box' and 'cell' parameters according to the produced cross-section geometry data.

    Args:
        simulations: List of Simulation objects, usually produced by a sweep
        cuts: 1. A tuple (p1, p2), where p1 and p2 are endpoints of a cross-section cut or
              2. a list of such tuples such that each Simulation object gets an individual cut
        ma_permittivity: Permittivity of metal–vacuum (air) interface
        ms_permittivity: Permittivity of metal–substrate interface
        sa_permittivity: Permittivity of substrate–vacuum (air) interface
        ma_thickness: Thickness of metal–vacuum (air) interface
        ms_thickness: Thickness of metal–substrate interface
        sa_thickness: Thickness of substrate–vacuum (air) interface
        vertical_cull: Tuple of two y-coordinates, will cull all geometry not in-between the y-coordinates.
            None by default, which means all geometry is retained.
        mer_box: If set as pya.DBox, will create a specified box as metal edge region,
            meaning that the geometry inside the region are separated into different layers with '_mer' suffix
        magnification_order: Increase magnification of simulation geometry to accomodate more precise spacial units.
            0 =   no magnification with 1e-3 dbu
            1 =  10x magnification with 1e-4 dbu
            2 = 100x magnification with 1e-5 dbu etc
            Consider setting non-zero value when using oxide layers with < 1e-3 layer thickness
        layout: predefined layout for the cross-section simulation. If not set, will create new layout.
        sim_names: Names for the created cross-section simulations. If not given, names of parent simulations are used
        sim_class: CutSimulation or its subclass used for processing the cross-section layers
        kwargs: Additional arguments passed to sim_class

    Returns:
        List of XSectionSimulation objects for each Simulation object in simulations
    """
    if isinstance(cuts, tuple):
        cuts = [cuts] * len(simulations)
    cuts = [tuple(c if isinstance(c, pya.DPoint) else c.to_p() for c in cut) for cut in cuts]
    if len(simulations) != len(cuts):
        if len(simulations) != 1:
            raise ValueError("Number of cuts did not match the number of simulations")
        simulations = simulations * len(cuts)

    if not layout:
        layout = pya.Layout()

    sim_names = (sim_names or []) + [None] * (len(cuts) - len(sim_names or []))

    # Increase database unit accuracy in layout if bigger magnification_order set
    if magnification_order > 0:
        layout.dbu = 10 ** (-3 - magnification_order)

    # Collect cross section simulation sweeps
    return [
        sim_class(
            layout,
            name=(name or simulation.name),
            source_sim=simulation,
            cut_start=cut[0],
            cut_end=cut[1],
            cut_bottom=-1e30 if vertical_cull is None else min(vertical_cull),
            cut_top=1e30 if vertical_cull is None else max(vertical_cull),
            tls_layer_thickness=[ma_thickness, ms_thickness, sa_thickness],
            tls_layer_material=["ma", "ms", "sa"],
            material_dict={
                "ma": {"permittivity": ma_permittivity},
                "ms": {"permittivity": ms_permittivity},
                "sa": {"permittivity": sa_permittivity},
            },
            region_map={} if mer_box is None else {"_mer": mer_box if isinstance(mer_box, list) else [mer_box]},
            **kwargs,
        )
        for simulation, cut, name in zip(simulations, cuts, sim_names)
    ]


def visualise_cross_section_cut_on_original_layout(
    simulations: list[Simulation],
    cuts: tuple[pya.DPoint, pya.DPoint] | list[tuple[pya.DPoint, pya.DPoint]],
    cut_label: str = "cut",
    width_ratio: float = 0.0,
) -> None:
    """Visualise requested cross section cuts on the original simulation layout.

    Will add a rectangle between two points of the cut, and two text points into layer "cross_section_cut"::

        * f"{cut_label}_1" representing the left side of the cross section simulation
        * f"{cut_label}_2" representing the right side of the cross section simulation

    In case the export takes cross sections for one simulation multiple times, this function
    can be called on same simulation sweep multiple times so that multiple cuts can be visualised
    in the same layout. In such case it is recommended to differentiate the cuts using `cut_label`.

    Args:
        simulations: list of simulations from which cross sections are taken. After this call these simulations
            will be modified to include the visualised cuts.
        cuts: 1. A tuple (p1, p2), where p1 and p2 are endpoints of a cross-section cut or
              2. a list of such tuples such that each Simulation object gets an individual cut
        cut_label: prefix of the two text points shown for the cut
        width_ratio: rectangles visualising cuts will have a width of length of the cut multiplied by width_ratio.
            By default will set 0 width line, which is visualised in KLayout.
    """
    if isinstance(cuts, tuple):
        cuts = [cuts] * len(simulations)
    cuts = [tuple(c if isinstance(c, pya.DPoint) else c.to_p() for c in cut) for cut in cuts]
    if len(simulations) != len(cuts):
        if len(simulations) != 1:
            raise ValueError("Number of cuts did not match the number of simulations")
        simulations = simulations * len(cuts)
    for simulation, cut in zip(simulations, cuts):
        cut_length = (cut[1] - cut[0]).length()
        marker_path = pya.DPath(cut, cut_length * width_ratio).to_itype(simulation.layout.dbu)
        # Prevent .OAS saving errors by rounding integer value of path width to even value
        marker_path.width -= marker_path.width % 2
        marker = pya.Region(marker_path)
        simulation.visualise_region(marker, cut_label, "cross_section_cut", cut)
