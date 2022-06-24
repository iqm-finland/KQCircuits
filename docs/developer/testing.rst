.. _testing:

Testing
=======

KQCircuits uses `tox` for running tests. It runs tools for different types of
tests, such as `pytest` for unit tests or `pylint` for linting. The
configuration of `tox` is done in `tox.ini`. You can execute all tests by
executing `tox`, or you can use separate commands like `pytest` to run
certain types of tests. The CI/CD pipeline uses `tox` to run the tests.


Unit tests
----------

KQCircuits uses the pytest framework for unit tests. Run the unit tests by
executing `pytest` or `pytest -n <NUM>` for some speed-up on  multi core CPUs.

All tests are placed in a separate
``tests`` folder in the project root. This folder should reflect the same hierarchy as
for the kqcircuits source folder. For example, if you are writing tests for
`kqcircuits/util/library_helper.py <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/kqcircuits/util/library_helper.py>`_, then you would create and use the same path to
the corresponding folder containing tests for ``library_helper.py`` such as
``tests/util/library_helper``.

For better organization and improved reporting, create a folder for each module
that you test. This folder would then contain a module for each method that you
want to test. Within that module, you would have test functions for each case
that you want to test for that method. For example, continuing to use
`library_helper.py <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/kqcircuits/util/library_helper.py>`_ to demonstrate the proposed structure, the ``library_helper`` folder
would have a ``test_load_library.py`` module which may contain test cases such as
``test_invalid_name``.

If your module contains a class, using the ``validate`` method in the ``Validator`` class
within `parameter_helper.py <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/kqcircuits/util/parameter_helper.py>`_, then you would have a ``tests/util/parameter_helper`` folder
and within it you would have a `test_validator_validate.py <https://github.com/iqm-finland/KQCircuits/blob/main/tests/util/parameter_helper/test_validator_validate.py>`_ module which may contain test
cases such as ``test_type_boolean``. In this case, we form the test module name by
a combination of the class and method names.

The above approach helps us organize our test cases into files which can easily be located
and do not get too large, while also producing pytest reports which are easy to understand.
Unfortunately, the repetitive ``test`` prefixes are conventional and needed for pytest to find
and/or filter tests at both module and function level. The required
prefixes/postfixes for the tests are defined in `pytest.ini <https://github.com/iqm-finland/KQCircuits/blob/main/pytest.ini>`_. Do not change
them without careful consideration, or the unit tests may not run properly.

You can run all tests and view coverage by running
the following command in the project root directory.

::

    pytest --cov --cov-report term-missing -rf

Refer to `pytest <https://docs.pytest.org/>`__ documentation for other options, such as running single tests.

If you develop a new feature for the project, make sure you write
a comprehensive set of unit tests which cover happy paths,
points of failure, edge cases, and so on.

Do not test private methods directly, but only their effects on the public methods that call them.

Similarly, if you fix a bug, write a test that would have failed prior to your fix,
so you can be sure that the bug wil not be reintroduced later.

Please note that the empty `conftest.py <https://github.com/iqm-finland/KQCircuits/blob/main/conftest.py>`_ file in the project root is required
so that pytest can follow imports to source code.
