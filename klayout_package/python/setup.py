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
from importlib.util import module_from_spec, spec_from_file_location
from setuptools import setup, find_packages


# Loads _version.py module without importing the whole package.
def get_version_and_cmdclass(package_name):
    spec = spec_from_file_location('version', os.path.join(package_name, '_version.py'))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__, module.cmdclass


version, cmdclass = get_version_and_cmdclass('kqcircuits')

setup(
    name='kqcircuits',
    version=version,
    cmdclass=cmdclass,
    description="KQCircuits is a KLayout/Python-based superconducting quantum circuit library developed by IQM.",
    long_description=open('README.md').read(),  # pylint: disable=consider-using-with
    long_description_content_type='text/markdown',
    author="IQM Finland Oy",
    author_email="kqcircuits@meetiqm.com",
    url="https://iqm-finland.github.io/KQCircuits/",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.6.9",
    install_requires=[                # Record dependencies in kqcircuits/util/dependencies.py too
        "klayout>=0.28",
        "numpy>=1.16",
        "Autologging~=1.3",
        "scipy>=1.2",
        "tqdm>=4.61",
        # psutil was considered when cpu_count(logical=False), was implemented in an alternative way
        # in elmer_export.py and gmsh_helpers.py, consider adding if more features are needed.
    ],
    extras_require={
        "docs": ["sphinx~=4.4", "sphinx-rtd-theme~=0.4", "networkx>=2.7", "matplotlib>=3.5.1"],
        "tests": ["pytest>=6.0.2", "pytest-cov~=2.8", "pytest-xdist>=2.1", "tox>=3.18", "pylint==2.9",
                  "networkx>=2.7", "matplotlib>=3.5.1", "nbqa~=1.3"],
        "notebooks": ["jupyter~=1.0.0", "klayout>=0.28"],
        "graphs": ["networkx>=2.7", "matplotlib>=3.5.1"],
        "simulations": ["gmsh>=4.11.1", "pandas>=1.5.3"],
    },
    entry_points={
        'console_scripts':[
            'kqc = console_scripts.run:run',
            ]
        }
)
