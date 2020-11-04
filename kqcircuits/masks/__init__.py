"""Modules for generating and exporting masks.

Masks are represented by mask sets, which can contain one or more mask layouts. Each mask layout consists of a chip
layout and a list of chip variants.

The following things can be exported for the mask and the chips:

    * layout files with specific layers
    * images with specific layers
    * automatic documentation containing:

        - number of each chip in the mask
        - chip parameters
        - images of the mask layout and chips
"""
