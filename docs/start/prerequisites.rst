.. _prerequisites:

Prerequisites
=============

KLayout
-------

Download and install KLayout from https://www.klayout.de/build.html . Builds
should exist there for most common operating systems, choose the correct one
for your OS. Otherwise you need to build KLayout yourself. We will assume in
these instructions, that KLayout has been installed in the default location.
**Note:** you must open KLayout at least once before installing KQCircuits,
because the KLayout python folder is only created then.

Successfully tested versions:

- Linux (Ubuntu 18.04/20.04 LTS, 64-bit): KLayout 0.26.4, 0.26.7 - 0.26.12
- MacOS: KLayout 0.26.3, 0.26.12 (recommended version `HomeBrew-Python3 included`)
- Windows 10 (64-bit): KLayout 0.26.3, 0.26.4, 0.26.7 - 0.26.9, 0.26.11, 0.26.12

Python
------

KQCircuits installation requires Python 3, which should be already installed on
Linux. On Windows you may have to install it. If your Python installation
does not already contain the ``pip`` package manager, you have to also
install that.

Succesfully tested versions:

- Windows: Python 3.7.6, 3.8.5, 3.9.4
- MacOS: Python 3.9.4
- Ubuntu 18.04 LTS: Python 3.6.9 and Python 3.8.5

Note, that KLayout will run macros with it's own Python version, ignoring
virtualenv settings. KLayout is linked together with libpython*.so on Linux
and libpython*.dll on Windows.


Git
---

KQC can be used without using Git, but it is required for sharing your code
in https://github.com/iqm-finland/KQCircuits .
