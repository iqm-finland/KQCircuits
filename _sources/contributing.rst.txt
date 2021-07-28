..
  comment: this file is under docs/ so that it is discoverable by GitHub.
  See https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors#adding-a-contributing-file


Contributing
============

Contributions to KQC are welcome from the community. Contributors are expected to accept IQM
Individual Contributor License Agreement by filling `a form at IQM website
<https://meetiqm.com/developers/clas>`__.

IQM developers will carefully review, approve and merge your PR. We use fast-forward merge strategy
to maintain a linear history. Please organize your code into a small number of commits with
meaningful commit messages.

We try to adhere to the PEP 8 style guide with 120 character long code lines permitted. See
:ref:`style`.

Versioning
^^^^^^^^^^

KQCircuits follows PEP 440 version scheme as implemented by `miniver
<https://github.com/jbweston/miniver>`_: ``<public version identifier>[+<local version label>]``.
The public version identifier needs to be set by ``git tag -a`` to ``v<major>.<minor>.<micro>``
whenever needed by bumping the appropriate version level:

* major when making a new official release
* minor when making a new Salt package
* micro when making any *incompatible change*

By *incompatible change* we mean one or more of these:

* backwards-incompatible API change
* any change that could break the code of other users
* API addition needed by code using KQC
* serious non-cosmetic geometry change that affects functionality
