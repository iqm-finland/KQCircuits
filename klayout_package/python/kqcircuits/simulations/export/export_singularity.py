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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).

import subprocess
from kqcircuits.defaults import ROOT_PATH


def export_singularity(remote_host: str, singularity_remote_path: str):

    if singularity_remote_path is None:
        singularity_remote_path = '~/KQCircuits/singularity'

    subprocess.call(['ssh', remote_host,
                    'mkdir', '-p',
                    singularity_remote_path,
                    singularity_remote_path + '/libexec',
                    singularity_remote_path + '/bin'])

    subprocess.call(['scp',
                    ROOT_PATH / 'singularity/libexec/kqclib',
                    ROOT_PATH / 'singularity/libexec/kqclib.sh',
                    remote_host + ':' + singularity_remote_path + '/libexec'])

    subprocess.call(['scp',
                     ROOT_PATH / 'singularity/create_links.sh',
                     remote_host + ':' + singularity_remote_path])


    subprocess.call(['ssh', remote_host,
                     'cd', singularity_remote_path, '&&',
                     './create_links.sh', '&&',
                     'mv', 'python', 'bin/python', '&&',
                     'rm', 'bin/paraview'])
