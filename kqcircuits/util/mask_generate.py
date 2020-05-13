import math

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.chip_frame import produce_label
from kqcircuits.defaults import default_layers, default_brand
from kqcircuits.elements.marker import Marker


def auto_fill_layout(**contents):
    total_pixel_amount = 0
    for c_name, amount in contents.items():
        total_pixel_amount = total_pixel_amount + contents[c_name]

    if (total_pixel_amount > 137):
        print("Mask Layout Overflow! Maximum pixel amount is 137. (Currently {})".format(total_pixel_amount))
        return []
    else:
        print("Total pixel amount : {}".format(total_pixel_amount))

    # fill the layout with dashes
    layout = []
    for i in range(0, 15):
        row = []
        for j in range(0, 15):
            row.append("---")
        layout.append(row)

    i = 7
    move = 0
    n = 1
    while i != 0:
        cur_row = layout[i]
        finish = 0

        if i == 1 or i == 13:
            finish = 4
        elif i == 2 or i == 12:
            finish = 2
        elif i == 3 or i == 4 or i == 10 or i == 11:
            finish = 1
        else:
            finish = 0

        j = 7
        sub_move = 0
        m = 1
        while j != finish:
            cur_slot = cur_row[j]

            for c_name, amount in contents.items():
                if contents[c_name] != 0:
                    cur_item = c_name
                    contents[c_name] = contents[c_name] - 1
                    cur_row[j] = cur_item
                    break
                else:
                    continue

            sub_move = ((-1) ** m) * m
            j = j + (sub_move)
            m = m + 1

        layout[i] = cur_row

        move = ((-1) ** n) * n
        i = i + (move)
        n = n + 1

    return layout


def mask_create_geometry(layout, wafer_center, wafer_rad_um):
    label_cell = layout.create_cell("ChipLabels")  # A new cell into the layout

    dbu = layout.dbu
    clip = -14.5e4
    region_covered = pya.Region(
        (pya.DPolygon([
            pya.DPoint(
                wafer_center.x + math.cos(a / 32 * math.pi) * wafer_rad_um,
                wafer_center.y + max(math.sin(a / 32 * math.pi) * wafer_rad_um, clip)
            )
            for a in range(0, 64 + 1)
        ])).to_itype(dbu))

    return dbu, label_cell, region_covered


def mask_create_qubits(layout, mask_name, maskextra_cell, wafer_center, region_covered, dbu, wafer_rad_um, top_cell):
    for layer, postfix in {"b base metal gap wo grid": "-1  .", "b airbridge pads": "- 2 .", "b airbridge flyover": "-  3."}.items():
        cell_mask_name = layout.create_cell("TEXT", "Basic", {
            "layer": default_layers[layer],
            "text": default_brand + "-" + mask_name + postfix,
            "mag": 5000.0
        })
        cell_mask_name_h = cell_mask_name.dbbox().height()
        cell_mask_name_w = cell_mask_name.dbbox().width()
        inst = maskextra_cell.insert(pya.DCellInstArray(cell_mask_name.cell_index(),
                                                        pya.DTrans(wafer_center.x - cell_mask_name_w / 2,
                                                                   -0.5e4 - cell_mask_name_h / 2)))
        region_covered -= pya.Region(inst.bbox()).extents(1e3 / dbu)

    cell_mask_outline = layout.create_cell("CIRCLE", "Basic", {
        "l": default_layers["b base metal gap wo grid"],
        "r": 1.e9,
        "n": 64
    })

    circle = pya.DTrans(wafer_center) * pya.DPath(
        [pya.DPoint(math.cos(a / 32 * math.pi) * wafer_rad_um, math.sin(a / 32 * math.pi) * wafer_rad_um) for a in
         range(0, 64 + 1)], 100)
    maskextra_cell.shapes(layout.layer(default_layers["annotations 2"])).insert(circle)

    cell_marker = Marker.create_cell(layout, {"window": True})
    x_min = 0
    y_min = -15e4
    x_max = 15e4
    y_max = 0

    marker_transes = [pya.DTrans(x_min + 25e3, y_min + 25e3) * pya.DTrans.R180,
                      pya.DTrans(x_max - 25e3, y_min + 25e3) * pya.DTrans.R270,
                      pya.DTrans(x_min + 25e3, y_max - 25e3) * pya.DTrans.R90,
                      pya.DTrans(x_max - 25e3, y_max - 25e3) * pya.DTrans.R0]

    for trans in marker_transes:
        inst = maskextra_cell.insert(pya.DCellInstArray(cell_marker.cell_index(), trans))
        region_covered -= pya.Region(inst.bbox()).extents(1e3 / dbu)

    maskextra_cell.shapes(layout.layer(default_layers["b base metal gap wo grid"])).insert(region_covered)
    maskextra_cell.shapes(layout.layer(default_layers["b airbridge pads"])).insert(region_covered)
    maskextra_cell.shapes(layout.layer(default_layers["b airbridge flyover"])).insert(region_covered)
    maskextra_cell.shapes(layout.layer(default_layers["mask graphical rep"])).insert(region_covered)

    top_cell.insert(pya.DCellInstArray(maskextra_cell.cell_index(), pya.DTrans()))


def mask_add_pixel(layout, mask_name, text_margin, layers, label_cell, top_cell, mask_map_legend, region_covered,
                   step_ver, step_hor, i, j, slot,
                   dice_width=200,
                   wafer_rad_um=6 / 2. * 25400.,
                   wafer_center=pya.DVector(76200 - 1200, -76200 + 1200)):
    v = step_ver * (i + 1) + step_hor * (j)
    if ((
            v - step_ver * 0.5 + step_hor * 0.5 - wafer_center).length() - wafer_rad_um < -1e4):  # center of the pixer 1 cm from the mask edge
        # slot = pixel_list[placed]
        # placed += 1
        if slot in mask_map_legend.keys():
            v0 = -pya.DVector(mask_map_legend[slot].dbbox().p1)
            inst = top_cell.insert(pya.DCellInstArray(mask_map_legend[slot].cell_index(), pya.DTrans(v + v0)))
            if inst.is_pcell():
                produce_label_wrap(i, j, v, dice_width, text_margin, layers, label_cell)
            else:
                produce_label_wrap(i, j, v, dice_width, text_margin, layers, label_cell, mask_name=mask_name,
                                   pixel_name=mask_map_legend[slot].basic_name(), company_name=default_brand)
            region_covered -= pya.Region(inst.bbox())

            # add graphical representation
            # print(label_cell)
            add_graphical_represantation_layer(layout, top_cell, get_pixel_name(mask_map_legend, mask_map_legend[slot]),
                                               v, v0)


def mask_add_box_pixel(layout, mask_name, text_margin, layers, label_cell, top_cell, mask_map_legend, region_covered,
                       step_ver, step_hor, i, j, k, l, slot,
                       dice_width=200,
                       wafer_rad_um=6 / 2. * 25400.,
                       wafer_center=pya.DVector(76200 - 1200, -76200 + 1200)):
    v = step_ver * (i + 3 * k + 1) + step_hor * (j + 3 * l)
    if ((
            v - step_ver * 0.5 + step_hor * 0.5 - wafer_center).length() - wafer_rad_um < -1e4):  # center of the pixer 1 cm from the mask edge
        inst = top_cell.insert(pya.DCellInstArray(mask_map_legend[slot].cell_index(), pya.DTrans(v)))
        v0 = -pya.DVector(mask_map_legend[slot].dbbox().p1)
        produce_label_wrap(i + 3 * k, j + 3 * l, v, dice_width, text_margin, layers, label_cell)
        region_covered -= pya.Region(inst.bbox())

        # add graphical representation
        add_graphical_represantation_layer(layout, top_cell, get_pixel_name(mask_map_legend, mask_map_legend[slot]), v,
                                           v0)


def produce_label_wrap(i, j, loc, dice_width, text_margin, default_layers, label_cell, pixel_name="", mask_name="",
                       version=1):
    """ dice_width, text_margin, default_layers """
    produce_label(label_cell, pos_index_name(i, j), loc + pya.DVector(1e4, 0), "bottomright",
                  dice_width, text_margin, default_layers["b base metal gap wo grid"], default_layers["b ground grid avoidance"])
    if pixel_name:
        produce_label(label_cell, pixel_name, loc + pya.DVector(1e4, 1e4), "topright",
                      dice_width, text_margin, default_layers["b base metal gap wo grid"], default_layers["b ground grid avoidance"])

    if mask_name:
        produce_label(label_cell, mask_name, loc + pya.DVector(0, 1e4), "topleft",
                      dice_width, text_margin, default_layers["b base metal gap wo grid"], default_layers["b ground grid avoidance"])


def pos_index_name(i, j):
    return chr(ord("A") + i) + ("{:02d}".format(j))


def get_pixel_name(mask_map_legend, search_cell):
    for pixel_name, cell in mask_map_legend.items():
        if search_cell == cell:
            return pixel_name


def add_graphical_represantation_layer(layout, top_cell, pixel_name, v, v0):
    grp_text = layout.create_cell("TEXT", "Basic", {
        "layer": default_layers["mask graphical rep"],
        "text": pixel_name,
        "mag": 5000,
    })

    top_cell.insert(pya.DCellInstArray(grp_text.cell_index(), pya.DTrans(v + v0 + pya.DVector(750, 750))))


def generate_mask(layout, top_cell, mask_name, mask_map, mask_map_legend, text_margin,
                  wafer_rad_um=6 / 2. * 25400.,
                  wafer_center=pya.DVector(76200 - 1200, -76200 + 1200),
                  dice_width=200,
                  mask_extra_name="MaskExtra",
                  layers=default_layers):
    step_ver = pya.DVector(0, -1e4)
    step_hor = pya.DVector(1e4, 0)

    dbu, label_cell, region_covered = mask_create_geometry(layout, wafer_center, wafer_rad_um)
    top_cell.insert(pya.DCellInstArray(label_cell.cell_index(), pya.DTrans(pya.DVector(0, 0))))

    for (i, row) in enumerate(mask_map):
        # print(i)
        for (j, slot) in enumerate(row):
            mask_add_pixel(layout, mask_name, text_margin, layers, label_cell, top_cell, mask_map_legend,
                           region_covered, step_ver, step_hor, i, j, slot)

    maskextra_cell = layout.create_cell(mask_extra_name)  # A new cell into the layout

    mask_create_qubits(layout, mask_name, maskextra_cell, wafer_center, region_covered, dbu, wafer_rad_um, top_cell)

    return maskextra_cell, label_cell


def generate_box_mask(layout, top_cell, mask_name, mask_map, box_map, mask_map_legend, text_margin,
                      wafer_rad_um=6 / 2. * 25400.,
                      wafer_center=pya.DVector(76200 - 1200, -76200 + 1200),
                      dice_width=200,
                      mask_extra_name="MaskExtra",
                      layers=default_layers):
    step_ver = pya.DVector(0, -1e4)
    step_hor = pya.DVector(1e4, 0)

    dbu, label_cell, region_covered = mask_create_geometry(layout, wafer_center, wafer_rad_um)
    top_cell.insert(pya.DCellInstArray(label_cell.cell_index(), pya.DTrans(pya.DVector(0, 0))))

    for (k, brow) in enumerate(mask_map):
        for (l, box) in enumerate(brow):
            if box in box_map:
                for (i, row) in enumerate(box_map[box]):
                    for (j, slot) in enumerate(row):
                        if slot in mask_map_legend.keys():
                            mask_add_box_pixel(layout, mask_name, text_margin, layers, label_cell, top_cell,
                                               mask_map_legend, region_covered, step_ver, step_hor, i, j, k, l, slot)

    maskextra_cell = layout.create_cell("MaskExtra")  # A new cell into the layout

    mask_create_qubits(layout, mask_name, maskextra_cell, wafer_center, region_covered, dbu, wafer_rad_um, top_cell)

    top_cell.insert(pya.DCellInstArray(maskextra_cell.cell_index(), pya.DTrans()))

    return maskextra_cell, label_cell
