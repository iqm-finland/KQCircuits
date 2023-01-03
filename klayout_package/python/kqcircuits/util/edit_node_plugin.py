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
import os
from kqcircuits.defaults import node_editor_valid_elements
from kqcircuits.pya_resolver import pya
from kqcircuits.util.gui_helper import node_from_text, get_nodes_near_position, replace_node, node_to_text


class EditNodePlugin(pya.Plugin):
    def __init__(self, manager, view):
        self.is_active = False
        self.manager = manager
        self.view = view
        self.selection = None
        self.last_dialog_position = None
        self.capture_range = 10  # Mouse capture and marker size in pixels
        self.last_mouse_position = pya.DPoint(0, 0)
        self.create_dialog()

    def create_dialog(self):
        dialog = pya.QDialog(pya.Application.instance().main_window())
        self.dialog = dialog
        dialog.windowTitle = 'Edit Node'
        dialog.setModal(False)

        form = pya.QFormLayout(dialog)

        def add_row(label, widget):
            form.addRow(label, widget)
            return widget

        self.text_x = add_row("x position (µm): ", pya.QLineEdit("0.0", dialog))
        self.text_y = add_row("y position (µm):", pya.QLineEdit("0.0", dialog))

        form.addRow(pya.QLabel("Optional arguments, leave empty for default:", dialog))

        self.text_inst_name = add_row("Instance name:", pya.QLineEdit("", dialog))
        self.text_angle = add_row("Angle (degrees):", pya.QLineEdit("", dialog))
        self.text_length_before = add_row("Length before (µm):", pya.QLineEdit("", dialog))
        self.text_length_increment = add_row("Length increment (µm):", pya.QLineEdit("", dialog))
        self.text_element = add_row("Element:", pya.QComboBox(dialog))
        self.text_element.addItems([''] + node_editor_valid_elements)
        self.text_element.editable = True
        self.text_align = add_row("Refpoint names to align to (input,output):", pya.QLineEdit("", dialog))
        self.text_params = add_row("Element parameters:", pya.QPlainTextEdit("", dialog))
        self.button_apply = add_row("", pya.QPushButton("Apply", dialog))
        self.button_apply.clicked(self.update_node_from_form)

    def update_node_from_form(self):
        if self.selection is None:
            return

        try:
            new_node = node_from_text(self.text_x.text, self.text_y.text, self.text_element.currentText,
                                      self.text_inst_name.text, self.text_angle.text,
                                      self.text_length_before.text, self.text_length_increment.text,
                                      self.text_align.text, self.text_params.toPlainText())
        except ValueError as e:
            pya.MessageBox.warning(type(e).__name__, str(e), pya.MessageBox.Ok)
            return

        self.manager.transaction("Edit node")
        replace_node(self.selection['instance'], self.selection['node_index'], new_node)
        self.manager.commit()
        self.selection['node'] = new_node
        self.update()

    def update_form_from_node(self, node):
        (self.text_x.text,
         self.text_y.text,
         self.text_element.currentText,
         self.text_inst_name.text,
         self.text_angle.text,
         self.text_length_before.text,
         self.text_length_increment.text,
         self.text_align.text,
         self.text_params.plainText) = node_to_text(node)

    def deselect(self):
        self.selection = None
        self.last_dialog_position = (self.dialog.x, self.dialog.y)
        self.dialog.hide()

    def select(self, instance, node_index, node):
        if self.selection is not None:
            self.deselect()

        marker = pya.Marker(self.view)
        position = instance.dcplx_trans * node.position
        size = pya.DVector(self.capture_range, self.capture_range) / self.view.viewport_trans().mag
        marker.set(pya.DBox(position - size, position + size))
        marker.vertex_size = 0
        marker.line_style = 2

        self.update_form_from_node(node)
        if self.last_dialog_position is not None:
            self.dialog.move(*self.last_dialog_position)
        self.dialog.show()

        self.selection = {
            'instance': instance,
            'instance_trans': instance.dcplx_trans,
            'node_index': node_index,
            'node': node,
            'marker': marker,
        }

    def activated(self):
        self.is_active = True

    def deactivated(self):
        self.deselect()
        self.is_active = False

    def mouse_click_event(self, p, buttons, prio):
        if prio and buttons == pya.ButtonState.LeftButton and self.is_active:
            cell_view = self.view.active_cellview()
            node_data = get_nodes_near_position(cell_view.cell, p, self.capture_range / self.view.viewport_trans().mag)
            if len(node_data) == 1:
                wg_inst, node, node_index = node_data[0]
                self.select(wg_inst, node_index, node)
            else:
                self.deselect()
            return True
        else:
            return False

    def mouse_moved_event(self, p, _, __):
        # Store current mouse position for use in tracking_position
        self.last_mouse_position = p

    def has_tracking_position(self):  # pylint: disable=no-self-use
        # We provide a custom tracking position only if a node is selected
        return self.selection is not None

    def tracking_position(self):
        if self.selection is not None:
            position = self.selection['instance_trans'].inverted() * self.last_mouse_position
            return position
        else:
            return pya.DPoint(0, 0)  # Only reached if something in the internal state is broken

    def update(self):
        # Update marker size to stay constant in pixels
        if self.selection is not None:
            marker = self.selection['marker']
            position = self.selection['instance_trans'] * self.selection['node'].position
            size = pya.DVector(self.capture_range, self.capture_range) / self.view.viewport_trans().mag
            marker.set(pya.DBox(position - size, position + size))


class EditNodePluginFactory(pya.PluginFactory):
    def __init__(self):
        if pya.Application.instance().is_editable():
            icon_path = os.path.join(os.path.dirname(__file__), 'edit_node_plugin.png')
            self.register(1000, "kqc_edit_node", "Edit Node", icon_path)

            # Set tooltip to something more helpful
            toolbar_action = pya.MainWindow.instance().menu().action('@toolbar.kqc_edit_node')
            if toolbar_action:
                toolbar_action.tool_tip = "Edit individual Node properties of WaveguideComposite elements"

    def create_plugin(self, manager, _, view):  # pylint: disable=no-self-use
        return EditNodePlugin(manager, view)
