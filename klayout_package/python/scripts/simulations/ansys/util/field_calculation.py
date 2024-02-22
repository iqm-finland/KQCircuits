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


def add_squared_electric_field_expression(oModule, name, vec_operator):
    """Adds squared complex-magnitude electric field expression to field calculation"""
    oModule.EnterQty("E")
    oModule.CalcOp("CmplxMag")
    oModule.CalcOp(vec_operator)
    oModule.EnterScalar(2)
    oModule.CalcOp("Pow")
    oModule.AddNamedExpression(name, "Fields")


def add_energy_integral_expression(oModule, name, objects, field_expr, dim, epsilon, subtraction_field):
    """Adds energy integral expression to field calculation"""
    for i, obj in enumerate(objects):
        oModule.CopyNamedExprToStack(field_expr)
        if dim == 2:
            oModule.EnterSurf(obj)
        else:
            oModule.EnterVol(obj)
        oModule.CalcOp("Integrate")
        if i > 0:
            oModule.CalcOp("+")
    if objects:
        oModule.EnterScalar(epsilon / 2)
        oModule.CalcOp("*")
    else:
        oModule.EnterScalar(0.0)
    if subtraction_field:
        oModule.CopyNamedExprToStack(subtraction_field)
        oModule.CalcOp("-")
    oModule.AddNamedExpression(name, "Fields")


def add_magnetic_flux_integral_expression(oModule, name, objects):
    """Adds magnetic flux integral expression to field calculation. Will be in units of magnetic flux quanta."""
    for i, obj in enumerate(objects):
        oModule.EnterQty("H")
        oModule.CalcOp("ScalarZ")
        oModule.CalcOp("Real")
        oModule.EnterSurf(obj)
        oModule.CalcOp("Integrate")
        if i > 0:
            oModule.CalcOp("+")
    if objects:
        oModule.EnterScalar(607706979.4822713)  # 2 * mu_0 * elementary_charge / Planck
        oModule.CalcOp("*")  # Transform flux into unit of magnetic flux quanta.
    else:
        oModule.EnterScalar(0.0)
    oModule.AddNamedExpression(name, "Fields")
