.. _klayout:

Installing KLayout
------------------

Download and install KLayout from https://www.klayout.de/build.html. Builds
should exist there for most common operating systems, choose the correct one
for your OS. Otherwise you need to build KLayout yourself. We recommend installing
KLayout without changing the installation directory location from default,
as many KQCircuits features assume that KLayout specific files can be found there.

.. note::
    For mac users:

    KLayout can also be installed using the `HomeBrew package manager <https://formulae.brew.sh/cask/klayout>`_,
    using terminal command ``brew install --cask klayout``.

    There might be issues on first time launch of KLayout with window:
    ``"klayout" cannot be opened because the developer cannot be verified``.
    To fix this, find KLayout app using Finder, control+click KLayout,
    click Open, then in the warning window there should be option to Open.

KLayout is an actively maintained project with regular feature updates, bugfixes and
stability improvements. We recommend using the latest version. KQCircuits is automatically
tested using KLayout versions:

- 0.28.17
- 0.29.12
- latest version of 0.30

on the following platforms:

- Linux: Ubuntu 22.04 LTS, 64-bit
- MacOS: latest github image
- Microsoft Windows Server 2022, OS version 10

.. note::
    KQC documentation uses Linux conventions and examples unless explicitly talking about Windows or
    MacOS. For example a Windows user should mentally translate path separator ``/`` to ``\``,
    klayout executable ``klayout`` to ``%APPDATA%\KLayout\klayout_app.exe`` or the KLayout
    environment directory ``~/.klayout`` to ``%HOMEPATH%\KLayout``.
