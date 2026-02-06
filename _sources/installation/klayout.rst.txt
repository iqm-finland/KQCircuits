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

- Linux: Ubuntu 24.04 LTS, 64-bit
- MacOS: latest github image
- Microsoft Windows Server 2025, OS version 10

Python
^^^^^^

KQCircuits installation requires Python 3.11 minimum. This should already come pre-packaged at least
with Ubuntu 24.04. On Windows platforms Python needs to be installed manually.
If your Python installation does not already contain the ``pip`` package
manager, you have to also install that.

Successfully tested versions:

- Ubuntu 24.04 LTS with Python 3.12.3
- Windows: Python 3.11.2

.. warning::
    For linux, KLayout installation is compiled in such a way
    that the system python is used to execute python commands within KLayout GUI runtime.
    Please check that your system python version is at least 3.11, as otherwise KQCircuits plug-in
    may be incompatible. Since system python is not recommended to be updated, consider in this case to either
    update the system OS or to manually compile KLayout application linked with separately installed python executable.
    Reminder that system python version doesn't affect most KLayout installations
    for other OS, and it also doesn't affect :ref:`standalone`.
