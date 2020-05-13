def deep_delete_pcells(cell):
    for inst in cell.each_inst():
        if (cell.is_pcell_variant(inst)):
            inst.delete()


def deep_delete_all(cell):
    for inst in cell.each_inst():
        inst.delete()
