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


from setuptools import setup, find_packages

setup(
    name='kqcircuits',
    version="3.2.1",
    description="KQCircuits is a KLayout/Python-based superconducting quantum circuit library developed by IQM.",
    author="IQM Finland Oy",
    author_email="developers@meetiqm.com",
    url="meetiqm.com",
    packages=find_packages(),
    python_requires=">=3.6.9,<3.10",  # klayout package not yet released for 3.10
    install_requires=[
        "klayout>=0.26,<0.27",
        "numpy>=1.18",
        "Autologging~=1.3",
        "scipy>=1.2",
    ],
    extras_require={
        "docs": ["sphinx~=2.4", "sphinx-rtd-theme~=0.4"],
        "tests": ["pytest>=6.0.2", "pytest-cov~=2.8", "pytest-xdist>=2.1", "tox>=3.18"],
        "gds_export": ["gdspy~=1.5"],
        "png_export": ["cairosvg~=2.4"],
    },
)
