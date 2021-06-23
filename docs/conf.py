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


# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import inspect
import shutil

__location__ = os.path.join(os.getcwd(), os.path.dirname(
    inspect.getfile(inspect.currentframe())))


# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

sys.path.insert(0, os.path.abspath('..'))
sys.path.append(os.path.abspath("../docs/sphinxext"))

# -- Run sphinx-apidoc ------------------------------------------------------
# This hack is necessary since RTD does not issue `sphinx-apidoc` before running
# `sphinx-build -b html . _build/html`. See Issue:
# https://github.com/rtfd/readthedocs.org/issues/1139
# DON'T FORGET: Check the box "Install your project inside a virtualenv using
# setup.py install" in the RTD Advanced Settings.
# Additionally it helps us to avoid running apidoc manually

try:  # for Sphinx >= 1.7
    from sphinx.ext import apidoc
except ImportError:
    from sphinx import apidoc

output_dir = os.path.join(__location__, "api")
module_dir = os.path.join(__location__, "../python/kqcircuits")
try:
    shutil.rmtree(output_dir)
except FileNotFoundError:
    pass

try:
    import sphinx
    from pkg_resources import parse_version

    template_dir = os.path.join(__location__, "templates", "apidoc")
    cmd_line_template = "sphinx-apidoc -f -o {outputdir} {moduledir} -e --implicit-namespaces --templatedir={templatedir}"
    cmd_line = cmd_line_template.format(outputdir=output_dir, moduledir=module_dir, templatedir=template_dir)

    args = cmd_line.split(" ")
    if parse_version(sphinx.__version__) >= parse_version('1.7'):
        args = args[1:]

    apidoc.main(args)
except Exception as e:
    print("Running `sphinx-apidoc` failed!\n{}".format(e))

import sphinx_rtd_theme

# -- Project information -----------------------------------------------------

import re
from kqcircuits._version import get_version

project = 'KQCircuits'
copyright = '2019-2021, IQM'
author = 'IQM'

# The full version, including alpha/beta/rc tags
release = re.match(r'([0-9]+\.[0-9]+\.[0-9]+)\.', get_version()).group(1)

# -- General configuration ---------------------------------------------------

source_suffix = ['.rst']
master_doc = 'index'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx_rtd_theme',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.coverage',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'kqc_elem_params',
]

todo_include_todos = True

pygments_style = 'sphinx'

autoclass_content = "both"
autosummary_generate = True
autodoc_member_order = 'bysource'
autodoc_default_options = {'members': True,
                           'undoc-members': True,
                           'show-inheritance': True}

def add_param_details(app, what, name, obj, options, lines):
    global _parameters
    if what == "class" and hasattr(obj, "get_schema"):
        _parameters = obj.get_schema(noparents=True).keys()

def skip_params(app, what, name, obj, skip, options):
    if what == "class" and str(type(obj)) != "<class 'function'>" and not skip and name in _parameters:
        return True

def setup(app):
    app.connect("autodoc-process-docstring", add_param_details)
    app.connect("autodoc-skip-member", skip_params)

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'api/modules.rst']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = [
    'css/custom.css'
]
