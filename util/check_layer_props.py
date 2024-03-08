# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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


# Check the default_layer_props.lyp or the file given as the first argument with values taken from
# KQCircuit's default_layers variable.
#
# If the last argument is "-w" (i.e. write) then it interactively updates the specified properties
# file with user provided values.
#
# usage: python check_layer_props.py [path/to/default_layer_props.lyp] [-w]


import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET


_layer_template = """
   <group-members>
   <frame-color>#FFFFFF</frame-color>
   <fill-color>#FF0000</fill-color>
   <frame-brightness>0</frame-brightness>
   <fill-brightness>0</fill-brightness>
   <dither-pattern>I0</dither-pattern>
   <line-style />
   <valid>true</valid>
   <visible>true</visible>
   <transparent>false</transparent>
   <width>1</width>
   <marked>false</marked>
   <xfill>false</xfill>
   <animation>0</animation>
   <name />
   <source>'some layer name' 1/1@1</source>
  </group-members>
"""

_layer_groups = []


def _add_new_layer(root, layers, name):
    """Add a new layer property entry."""
    ids = layers[name]
    src = f"'{name}' {ids[0]}/{ids[1]}@1"
    reply = input(f"Add missing layer ({src}) to properties file? (y/N)\n")
    if reply.lower() not in ("yes", "y"):
        return

    new = ET.XML(_layer_template)
    src = new.find("source").text = src
    new.tail = "\n "

    print("Please specify changed layer properties (Enter to accept the default values.)")
    face = f"{src[1:4]}-face" if src[4] == " " else "texts"  # give a reasonable default
    lg = None
    while not lg:  # find the layer group element
        face = input(f"    layer group: {face} --> ") or face
        lg = root.find(f"properties[name='{face}']")
        if not lg:  # further explain options
            print(f"No such layer group! Please choose one of these: {_layer_groups}")
    lg[-1].tail += " "
    lg.append(new)

    def replace(tag):
        e = new.find(tag)
        e.text = input(f"    {tag}: {e.text} --> ") or e.text

    replace("frame-color")
    replace("fill-color")
    replace("dither-pattern")


def check_file(file_name, diagnostic_mode=True):
    if not file_name.is_file():
        print(f"Can't find '{file_name}'!")
        sys.exit(-1)

    if diagnostic_mode:
        print(f"Checking file '{file_name}'.\nUse '-w' switch to interactively modify it.\n")

    errcnt = 0
    old_layers = []
    layers = {name.replace("_", " "): (ids.layer, ids.datatype) for name, ids in default_layers.items()}

    tree = ET.parse(file_name)
    root = tree.getroot()

    for prop in root.iter("properties"):
        if prop.find("source").text == "*/*@*":
            _layer_groups.append(prop.find("name").text)

    for src in root.iter("source"):
        if src.text == "*/*@*":
            continue

        name, lid, dt, extra = re.match(r"^'?([^']+)'? (\d+)/(\d+)(.+)", src.text).groups()
        if name in layers:
            old_layers.append(name)
            ids = layers[name]
            if ids != (int(lid), int(dt)):  # update in case of layer index mismatch
                if diagnostic_mode:
                    errcnt += 1
                    print("layer index mismatch in:", src.text)
                    continue
                reply = input(f"Fix mismatched layer id in '{name}'? (y/N)\n")
                if reply.lower() in ("yes", "y"):
                    src.text = f"'{name}' {ids[0]}/{ids[1]}{extra}"
        else:
            if diagnostic_mode:
                errcnt += 1
                print("unused layer in properties file:", src.text)
                continue
            reply = input(f"Remove unnecessary layer ({src.text}) from properties file? (y/N)\n")
            if reply.lower() in ("yes", "y"):
                src.text = None

    if not diagnostic_mode:
        for prop in root.findall("properties"):
            for gm in prop.findall("group-members"):
                if gm.find("source").text is None:
                    prop.remove(gm)

    for name in layers:
        if name not in old_layers:
            if diagnostic_mode:
                errcnt += 1
                print("missing layer:", name)
                continue
            _add_new_layer(root, layers, name)

    if not diagnostic_mode:
        tree.write(file_name, encoding="utf-8", xml_declaration=True)
    sys.exit(errcnt)


if __name__ == "__main__":
    diagnostic_mode = sys.argv[-1] != "-w"
    if not diagnostic_mode:
        sys.argv.pop()

    if len(sys.argv) > 1 and not sys.argv[-1].endswith(".lyp"):
        from importlib import import_module

        import_module(sys.argv.pop())  # load optional module to modify default_layers
    from kqcircuits.defaults import default_layers  # pylint: disable=wrong-import-position

    props_file = Path(__file__).parents[1] / "klayout_package/python/kqcircuits/layer_config/default_layer_props.lyp"
    if len(sys.argv) > 1:
        props_file = Path(sys.argv[1])

    check_file(props_file, diagnostic_mode)
