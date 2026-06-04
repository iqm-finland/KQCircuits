.. _klayout:

Installing KLayout
------------------

Download and install KLayout from https://www.klayout.de/build.html. Builds
should exist there for most common operating systems, choose the correct one
for your OS.

An important consideration when choosing an installation package is how
a python interpreter is linked into the KLayout compilation. For linux builds,
it will always link the system python of the OS. For windows, a copy of python executable
is packaged with the installation. For macOS, package names starting with ``ST-*``
link to system python, and ``HW-*`` include a python executable with the package.

The reason why we need to care about system python is that ideally we would like
the python version to be recent enough so that its compatible with our dependencies.
**KQCircuits requires Python 3.11 minimum.** This is not a problem for sufficiently
recent linux distributions (Ubuntu 24.04), as well as Windows and ``HW-*`` macOS installations
since pre-packaged python executables fulfill the requirement.

.. warning::
    Do note that updating system python executable to later version is **NOT** recommended
    and may risk breaking your operating system.

Wherever the python executable happens to be, make sure that ``pip`` package
manager is installed for that python executable.

You can also build KLayout yourself, which allows you to link the python
executable of your choosing.

We recommend installing
KLayout without changing the installation directory location from default,
as many KQCircuits features assume that KLayout specific files can be found there.

.. note::
    For mac users:

    There are KLayout installation packages precompiled natively for ``arm64``,
    but they are only available in ``ST-*`` form. Most macOS distributions
    have Python version 3.9.6 as the system python. There are multiple ways
    to resolve this problem.

    1. Easiest way is to install older dependencies that are compatible with older
    python. Copy the contents of :git_url:`gui-requirements-396.txt <klayout_package/python/requirements/mac/gui-requirements-396.txt>`
    into :git_url:`gui-requirements.txt <klayout_package/python/requirements/mac/gui-requirements.txt>`
    then proceed with installation guides as usual. There are risks that we might
    use features not supported by out-of-date dependencies in KQC, and also that
    a standalone KQCircuits installation may be out-of-sync with the GUI KQCircuits installation.

    2. Next consideration is to use ``HW-*`` macOS installation of KLayout. At the time
    of writing this is only available for ``x86_64`` compilations, which means for some macOS
    devices it is dependent on Rosetta to recompile the KLayout executable during launch.
    This slows down KLayout startup, and also at some macOS release in the future
    Rosetta support will be deprecated.

    3. Finally, KLayout can be compiled yourself using your macOS device. We recommend
    `Guide 6C. Fully Homebrew-flavored build with Homebrew Ruby 3.4 and Homebrew Python 3.13 <https://github.com/KLayout/klayout/tree/master/macbuild#6c-fully-homebrew-flavored-build-with-homebrew-ruby-34-and-homebrew-python-313>`_,
    which we have tested to work for us. A prerequisite is to install a python version of your choice
    using the HomeBrew package manager,
    then instructing KLayout compiler to link to Homebrew python installation.

    4. There is a KLayout cask in `HomeBrew package manager <https://formulae.brew.sh/cask/klayout>`_,
    available for install using ``brew install --cask klayout``.
    This will install a ``x86_64`` compilation with prepackaged python executable.
    At the time of writing there seemed to be problems installing from homebrew, which is
    why we don't recommend anymore to install KLayout using this method.

    There might be issues on first time launch of KLayout with window:
    ``"klayout" cannot be opened because the developer cannot be verified``.
    To fix this, find KLayout app using Finder, control+click KLayout,
    click Open, then in the warning window there should be option to Open.

.. note::
    If problems with linking python executable to KLayout installation seem insurmountable,
    do remember that it doesn't affect the :ref:`standalone`, in case you only care about
    such use case of KQCircuits.

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
