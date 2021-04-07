# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from setuptools import setup, find_packages

setup(
    name='kqcircuits',
    version="2.1.0",
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
