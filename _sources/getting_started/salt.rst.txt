.. _salt_package:

KQCircuits Salt package
=======================

The easiest way to get started with KQCircuits is to install the so-called Salt package from the KLayout package
manager. The Salt package allows you to use all of the KQC features:

* Place and use any of the built-in KQC elements and chips
* Create your own elements and chips in a user-defined location
* Run scripts, define and export simulations, etc.

However, the Salt package itself is read-only, so using this mode does not allow you to modify existing KQC elements
or chips. To modify KQC elements, use the :ref:`developer_setup` instead. It is also possible to migrate to the
Developer setup later on, just uninstall the Salt package first.

Installing KQCircuits Salt Package
----------------------------------

First, make sure you have a recent version of KLayout installed. Open KLayout in edit mode, and select
"Tools -> Manage Packages" in the KLayout menu to install the KQCircuits package:

.. image:: ../images/salt/install.gif

Note that KLayout was started in edit mode, see :ref:`usage`.

.. note::
   If KQCircuits is not working properly after installation (KQC libraries
   not visible, running any macro gives an error, etc.), there might be some
   problem with the specific KLayout version/build you are using, see
   :ref:`installation_issues` section for possible solutions.

.. _salt_user_package:

Setting up a user package directory
-----------------------------------

To create your own elements and chips, you have to set a directory as user package. In KLayout, choose the
**KQCircuits -> Add User Package** menu entry, and fill the following dialog box:

.. image:: ../images/salt/add_user_package.png

Packages have a name and a directory linked to it. The package name should be a single lowercase word, possibly with
underscores. The directory can be anywhere on your system. Click ``Add`` to complete the setup.

.. note::
    After setting up a user package, close and restart KLayout for the changes to complete.

If you choose a new directory for the user package, subdirectories for all KQC libraries are created automatically.
You can view the user package content in the Macro Editor (press **F5**), under **Python**, **[Local - python branch]**.

.. image:: ../images/salt/user_package_directory.png

.. note::
    To remove a user package, use the **KQCircuits -> Remove User Package** menu. This will remove links to the package,
    but it will not delete any actual files.

Upgrading or Removing Salt Package
----------------------------------

After upgrading the KQCircuits Salt package, KLayout needs to be restarted. See the release notes
for further details.

Downgrading or upgrading several steps at once is not guaranteed to always work. Upgrading KQC
usually works but the safest approach is to uninstall KQC and then install a new version.

Release Notes
-------------

Here we list particular quirks of specific KQCircuits Salt packages. For a full list of changes see
the code repository.

* Version 4.5.0 is broken
* Version 4.1.0 requires full reinstall of KQC. Qubits directory has moved, to remove the earlier
  version we need to first remove KQC then install the new version.
* Version 4.0.0 requires full reinstall of KQC. Several files have been relocated, without a full
  reinstall multiple versions of the same file will be left behind.
* Version 3.3.0 needs manual install of ``tqdm`` Python module.
