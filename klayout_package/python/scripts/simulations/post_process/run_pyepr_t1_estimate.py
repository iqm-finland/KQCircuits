# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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
"""
Executes pyEPR calculations on Ansys simulation tool.
The geometry should be imported and Ansys project should be saved before calling this.

Args:
    sys.argv[1]: json file of the simulation
    sys.argv[2]: parameter file for pyEPR calculations

"""
import sys
import json

from pathlib import Path

import pandas as pd
import pyEPR as epr
import qutip.fileio

project_path = Path.cwd()
project_name = str(Path(sys.argv[1]).stem if Path(sys.argv[1]).suffixes else Path(sys.argv[1])) + "_project"

with open(sys.argv[2], "r") as fp:
    pp_data = json.load(fp)

try:
    # Nominal values, good for relative comparison
    epr.config["dissipation"].update(
        {
            ## 3D, given in `pinfo.dissipative['dielectrics_bulk']`
            # integration to get participation ratio which is multiplied with the loss tangent, adds to Q as 1/(p tan_d)
            # loss tangent (currently does not support multiple different materials)
            "tan_delta_sapp": pp_data.get("substrate_loss_tangent", 1e-6),
            ## 2D, given in `pinfo.dissipative['dielectric_surfaces']`.
            # These values are not used if layer specific values for `dielectric_surfaces` are given in the JSON
            # Approximates having the surface energy on a thin dielectric layer with
            "tan_delta_surf": 0.001,  # loss tangent
            "th": 3e-9,  # thickness
            "eps_r": 10,  # relative permittivity
        }
    )

    # Rough correction factors from comparing to cross-section EPR. For more info, see Niko Savola M.Sc. thesis
    correction_factor = {
        "layerMA": 1 / 2.5,
        "layerMS": 1 / 0.35,
        "layerSA": 1 / 0.7,
    }

    pinfo = epr.ProjectInfo(
        project_path=project_path,
        project_name=project_name,
        design_name="EigenmodeDesign",
    )
    oDesign = pinfo.design

    junction_numbers = [int(e.split("Junction")[-1]) for e in pinfo.get_all_object_names() if "Junction" in e]

    ## Set dissipative elements
    # Ansys solids
    pinfo.dissipative["dielectrics_bulk"] = [e for e in pinfo.get_all_object_names() if e.startswith("Substrate")]
    if pp_data.get("dielectric_surfaces", None) is None:
        pinfo.dissipative["dielectric_surfaces"] = [  # Ansys sheets (exclude 3D volumes, ports, and junctions)
            e
            for e in pinfo.get_all_object_names()
            if not (
                e.startswith("Vacuum")
                or e.startswith("Substrate")
                or any(e in [f"Port{i}", f"Junction{i}"] for i in junction_numbers)
            )
        ]
    else:
        pinfo.dissipative["dielectric_surfaces"] = {
            e: v for e in pinfo.get_all_object_names() for k, v in pp_data["dielectric_surfaces"].items() if k in e
        }

    oEditor = oDesign.modeler._modeler
    for j in junction_numbers:
        pinfo.junctions[f"j{j}"] = {
            "Lj_variable": f"Lj_{j}",  # junction inductance Lj
            "rect": f"Port{j}",  # rectangle on which lumped boundary condition is specified
            "line": (name := f"Junction{j}"),  # polyline spanning the length of the rectangle
            "Cj_variable": f"Cj_{j}",  # junction capacitance Cj (optional but needed for dissipation)
            "length": f"{oEditor.GetEdgeLength(oEditor.GetEdgeIDsFromObject(name)[0])}{oEditor.GetModelUnits()}",
        }
    pinfo.validate_junction_info()

    # Simulate
    if pinfo.setup.solution_name:
        pinfo.setup.analyze()

    eprh = epr.DistributedAnalysis(pinfo)
    eprh.do_EPR_analysis()  # do field calculations

    epra = epr.QuantumAnalysis(eprh.data_filename)
    epr_results = epra.analyze_all_variations()  # post-process field calculations to get results

    df = pd.DataFrame()
    for variation, data in epr_results.items():

        f_ND, chi_ND, hamiltonian = epr.calcs.back_box_numeric.epr_numerical_diagonalization(
            data["f_0"] / 1e3,  # in GHz
            data["Ljs"],  # in H
            data["ZPF"],  # in units of reduced flux quantum
            return_H=True,
        )
        # older versions of qutip require str path
        qutip.fileio.qsave(hamiltonian, str(project_path / f"Hamiltonian_{project_name}_{variation}.qu"))

        # fmt: off
        df = pd.concat([df, pd.DataFrame({
            'variation': eprh.get_variation_string(variation),

            # Substrate quality factor and participation
            **{(Q_bulk := data['sol'].filter(regex=bulk+'$')).columns[0]: Q_bulk.values.flatten()
                for bulk in pinfo.dissipative['dielectrics_bulk']},
            **{f'p_dielectric_{bulk}': (1 / (
                    data['sol'].filter(regex=bulk+'$') * epr.config['dissipation']['tan_delta_sapp']
                )).values.flatten()
                for bulk in pinfo.dissipative['dielectrics_bulk']},

            # Surface quality factors and participation
            **{(Q_surf := data['sol'].filter(regex=surface)).columns[0]: Q_surf.values.flatten() \
                    / correction_factor.get(surface, 1)
                for surface in pinfo.dissipative['dielectric_surfaces'].keys()},
            **{f'p_surf_{surface}': (1 / (  # th & eps_r still affect
                    data['sol'].filter(regex=surface) \
                    * (pinfo.dissipative['dielectric_surfaces'][surface]['tan_delta_surf']
                        if isinstance(pinfo.dissipative['dielectric_surfaces'], dict)
                        else epr.config['dissipation']['tan_delta_surf'])
                    * correction_factor.get(surface, 1)
                )).values.flatten()
                for surface in pinfo.dissipative['dielectric_surfaces'].keys()},

            'Q_ansys': data.get('Qs', None),
            'f_0': data['f_0'] * 1e6,
            'f_1': data['f_1'] * 1e6,  # f_0 frequency - Lamb shift from cavity
            # for ZPF details consult https://github.com/zlatko-minev/pyEPR/blob/master/pyEPR/calcs/basic.py#L12
            'ZPF': data['ZPF'].flatten(),
            'Pm_normed': data['Pm_normed'].flatten(),
            'Ljs': data['Ljs'][0],
            'Cjs': data['Cjs'][0],
            'Chi_O1': str(data['chi_O1'].values),  # first order perturbation theory
            # Results from numerical diagonalisation
            'Chi_ND': str(chi_ND),
            'f_ND': f_ND,
            # 'n_zpf': ZPF from capacitive participation, small compared to inductive
        }).rename_axis('mode')])
        # fmt: on

        # Total quality factor (harmonic sum) after corrected values
        df["Q_total"] = (1 / (1 / df.filter(regex="^Q(dielectric|surf).*")).sum(axis=1)).values.flatten()

    # Convert to multi-index
    df.set_index(["variation", df.index], inplace=True)
    df.to_csv(project_path / f"QData_{project_name}.csv", index_label=["variation", "mode"])

    # Save HFSS project file
    pinfo.project.save()
    # This allows Ansys to be closed, but doesn't close it
    pinfo.disconnect()

finally:

    # Always exit Ansys
    epr.ansys.HfssApp().get_app_desktop()._desktop.QuitApplication()
