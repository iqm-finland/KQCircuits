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


from kqcircuits.elements.meander import Meander
from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.port import InternalPort
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.parameters import Param, pdt


class XMonsDirectCouplingFullChipSim(Simulation):

    qubit_spacing = Param(pdt.TypeDouble, "Qubit spacing", 10, unit="μm")
    arm_width_a = Param(pdt.TypeDouble, "Qubit A and C arm width", 24, unit="μm")
    arm_width_b = Param(pdt.TypeDouble, "Qubit B arm width", 24, unit="μm")
    enable_flux_lines = Param(pdt.TypeBoolean, "To flux or not to flux", True)
    enable_drive_lines = Param(pdt.TypeBoolean, "To drive or not to drive", True)
    enable_transmission_line = Param(pdt.TypeBoolean, "To transmit?", True)


    def produce_waveguide(self, path, term1=0, term2=0, turn_radius=None):
        if turn_radius is None:
            turn_radius = self.r

        tl = self.add_element(WaveguideCoplanar,
            path=pya.DPath(path, 1),
            r=turn_radius,
            term1=term1,
            term2=term2,
        )
        self.cell.insert(pya.DCellInstArray(tl.cell_index(), pya.DTrans()))

        return tl.length()

    def produce_qubit(self, qubit_cell, center_x, center_y=5e3, name=None):
        qubit_trans = pya.DTrans(0, False, center_x, center_y)
        qubit_inst = self.cell.insert(pya.DCellInstArray(qubit_cell.cell_index(), qubit_trans))
        if name:
            qubit_inst.set_property("id", name)

        refpoints_abs = self.get_refpoints(qubit_cell, qubit_inst.dtrans)
        port_qubit_dr = refpoints_abs["port_drive"]
        port_qubit_fl = refpoints_abs["port_flux"] if "port_flux" in refpoints_abs else None
        port_qubit_ro = refpoints_abs["port_cplr1"]
        port_qubit_squid_a = refpoints_abs["port_squid_a"]
        port_qubit_squid_b = refpoints_abs["port_squid_b"]

        return (port_qubit_dr, port_qubit_fl, port_qubit_ro, port_qubit_squid_a, port_qubit_squid_b)

    def produce_readout_resonator(self, pos_start, end_y, length):
        width_rr = 300

        # coupler
        pos_coupler_end = pya.DPoint(pos_start.x, end_y - 3 * self.r)
        len_coupler = self.produce_waveguide([
            pya.DPoint(pos_start.x - width_rr / 2, end_y),
            pya.DPoint(pos_start.x + width_rr / 2, end_y),
            pya.DPoint(pos_start.x + width_rr / 2, end_y - 2 * self.r),
            pya.DPoint(pos_start.x, end_y - 2 * self.r),
            pos_coupler_end
        ], turn_radius=50, term1=10)

        # meander
        meander = self.add_element(Meander,
            start=pos_coupler_end,
            end=pos_start,
            length=length - len_coupler,
            meanders=8,
            r=50
        )
        self.cell.insert(pya.DCellInstArray(meander.cell_index(), pya.DTrans()))

    def produce_launcher(self, pos, direction):
        """Wrapper function for launcher PCell placement at `pos` with `direction`, `name` and `width`."""

        subcell = self.add_element(WaveguideCoplanar,
            path= pya.DPath([pya.DPoint(0, 0), pya.DPoint(90, 0)], 0),
            term2=10,
        )
        subcell2 = self.add_element(WaveguideCoplanar,
            path=pya.DPath([pya.DPoint(100, 0), pya.DPoint(110, 0)], 0),
            term2=0,
        )

        if isinstance(direction, str):
            direction = {"E": 0, "W": 180, "S": -90, "N": 90}[direction]
        transf = pya.DCplxTrans(1, direction, False, pos)
        self.cell.insert(pya.DCellInstArray(subcell.cell_index(), transf))
        self.cell.insert(pya.DCellInstArray(subcell2.cell_index(), transf))

    def produce_launchers_SMA8(self, enabled=["WS", "WN", "ES", "EN", "SW", "SE", "NW", "NE"]):
        """Produces enabled launchers for SMA8 sample holder default locations

        Args:
            enabled: List of enabled standard launchers from set ("WS", "WN", "ES", "EN", "SW", "SE", "NW", "NE")

        Effect:
            launchers PCells added to the class parent cell.

        Returns:
            launchers dictionary, where keys are launcher names and values are tuples of (point, heading, distance from
            chip edge)
        """
        # pylint: disable=invalid-name,dangerous-default-value
        # dictionary of point, heading, distance from chip edge
        launchers = {
            "WS": (pya.DPoint(800, 2800), "W", 300),
            "ES": (pya.DPoint(9200, 2800), "E", 300),
            "WN": (pya.DPoint(800, 7200), "W", 300),
            "EN": (pya.DPoint(9200, 7200), "E", 300),
            "SW": (pya.DPoint(2800, 800), "S", 300),
            "NW": (pya.DPoint(2800, 9200), "N", 300),
            "SE": (pya.DPoint(7200, 800), "S", 300),
            "NE": (pya.DPoint(7200, 9200), "N", 300)
        }
        for name in enabled:
            self.produce_launcher(launchers[name][0], launchers[name][1])
        return launchers

    def build(self):
        enabled_launchers = []
        launchers_with_ports = []
        if self.enable_transmission_line:
            enabled_launchers += ['NW', 'NE']
            launchers_with_ports += ['NW', 'NE']
        if self.enable_drive_lines:
            enabled_launchers += ['WN', 'SW', 'ES']
            launchers_with_ports += ['WN', 'SW', 'ES']
        if self.enable_flux_lines:
            enabled_launchers += ['WS', 'SE', 'EN']
            # For now, flux lines don't have ports
            # TODO: Set up a way to make flux line a different polygon from ground plane, and move it to signal layer
        launchers = self.produce_launchers_SMA8(enabled=enabled_launchers)

        # Finnmon
        qubit_props_common = {
            "fluxline_type": "Fluxline Standard" if self.enable_flux_lines else "none",
            "junction_type": 'Sim',
            "arm_length": [146] * 4,
            "island_r": 2,
            "cpl_length": [0, 140, 0],
            "cpl_width": [60, 24, 60],
            "cpl_gap": [110, 102, 110],
            "cl_offset": [150, 150]
        }
        finnmon_a = self.add_element(Swissmon,
            arm_width=[self.arm_width_a] * 4,
            gap_width=[(72 - self.arm_width_a) / 2] * 4, **qubit_props_common)
        finnmon_b = self.add_element(Swissmon,
            arm_width=[self.arm_width_b] * 4,
            gap_width=[(72 - self.arm_width_b) / 2] * 4, **qubit_props_common)

        (pos_qb1_dr, pos_qb1_fl, pos_qb1_rr, port_qubit1_squid_a, port_qubit1_squid_b) = \
            self.produce_qubit(finnmon_a, 5e3 - 330 - self.qubit_spacing, name="qb_1")
        (pos_qb2_dr, pos_qb2_fl, pos_qb2_rr, port_qubit2_squid_a, port_qubit2_squid_b) = \
            self.produce_qubit(finnmon_b, 5e3, name="qb_`2")
        (pos_qb3_dr, pos_qb3_fl, pos_qb3_rr, port_qubit3_squid_a, port_qubit3_squid_b) = \
            self.produce_qubit(finnmon_a, 5e3 + 330 + self.qubit_spacing, name="qb_3")

        # Readout resonators
        height_rr_feedline = 7.3e3
        self.produce_readout_resonator(pos_qb1_rr, height_rr_feedline - 30, 4330.9)  # values from manual X06
        self.produce_readout_resonator(pos_qb2_rr, height_rr_feedline - 30, 4225.9)
        self.produce_readout_resonator(pos_qb3_rr, height_rr_feedline - 30, 4177.9)

        # Transmission lines
        tl_gap = 300

        if self.enable_transmission_line:
            # RR feedline
            self.produce_waveguide([
                launchers["NW"][0],
                pya.DPoint(launchers["NW"][0].x, height_rr_feedline),
                pya.DPoint(launchers["NE"][0].x, height_rr_feedline),
                launchers["NE"][0]])

        if self.enable_drive_lines:
            # Qb1 chargeline
            self.produce_waveguide([
                launchers["WN"][0],
                pya.DPoint(launchers["NW"][0].x - tl_gap, launchers["WN"][0].y),
                pya.DPoint(launchers["NW"][0].x - tl_gap, launchers["WS"][0].y + tl_gap),
                pya.DPoint(pos_qb1_dr.x, launchers["WS"][0].y + tl_gap),
                pos_qb1_dr], term2=self.b)
            # Qb2 chargeline
            self.produce_waveguide([
                launchers["SW"][0],
                pya.DPoint(launchers["SW"][0].x, launchers["WS"][0].y - tl_gap),
                pya.DPoint(pos_qb2_dr.x, launchers["WS"][0].y - tl_gap),
                pos_qb2_dr], term2=self.b)
            # Qb3 driveline
            self.produce_waveguide([
                launchers["ES"][0],
                pya.DPoint(pos_qb3_dr.x, launchers["ES"][0].y),
                pos_qb3_dr], term2=self.b)

        if self.enable_flux_lines:
            # Qb1 fluxline
            self.produce_waveguide([
                launchers["WS"][0],
                pya.DPoint(pos_qb1_fl.x, launchers["WS"][0].y),
                pos_qb1_fl])
            # Qb2 fluxline
            self.produce_waveguide([
                launchers["SE"][0],
                pya.DPoint(launchers["SE"][0].x, launchers["ES"][0].y - tl_gap),
                pya.DPoint(pos_qb2_fl.x, launchers["ES"][0].y - tl_gap),
                pos_qb2_fl])
            # Qb3 fluxline
            self.produce_waveguide([
                launchers["EN"][0],
                pya.DPoint(launchers["NE"][0].x + tl_gap, launchers["EN"][0].y),
                pya.DPoint(launchers["NE"][0].x + tl_gap, launchers["ES"][0].y + tl_gap),
                pya.DPoint(pos_qb3_fl.x, launchers["ES"][0].y + tl_gap),
                pos_qb3_fl])


        dx = {'W': -90, 'E': 90, 'S': 0, 'N': 0}
        dy = {'W': 0, 'E': 0, 'S': -90, 'N': 90}

        dx2 = {'W': -100, 'E': 100, 'S': 0, 'N': 0}
        dy2 = {'W': 0, 'E': 0, 'S': -100, 'N': 100}


        for i, launcher_name in enumerate(launchers_with_ports):
            launcher = launchers[launcher_name]
            p1 = pya.DPoint(launcher[0].x + dx[launcher[1]], launcher[0].y + dy[launcher[1]])
            p2 = pya.DPoint(launcher[0].x + dx2[launcher[1]], launcher[0].y + dy2[launcher[1]])
            self.ports.append(InternalPort(i + 1, *self.etched_line(p1, p2)))

        self.ports.append(InternalPort(9, *self.etched_line(port_qubit1_squid_a, port_qubit1_squid_b)))
        self.ports.append(InternalPort(10, *self.etched_line(port_qubit2_squid_a, port_qubit2_squid_b)))
        self.ports.append(InternalPort(11, *self.etched_line(port_qubit3_squid_a, port_qubit3_squid_b)))
