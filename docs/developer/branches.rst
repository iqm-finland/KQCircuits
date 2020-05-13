Branches
^^^^^^^^

Master Branch
,,,,,,,,,,,,,

The repository has one base branch named ``master``.
The ``master`` branch always represents the latest changes.
Developers must branch from and merge to _master_.
The ``master`` branch must always be stable and deployable.

Issue Branches
,,,,,,,,,,,,,,

Issue branches are used for concurrent development, tracking progress with features and bugs,
and fixing live production problems. Unlike the master branch, these branches will always
have a limited life time because they will be removed eventually.

This approach to branching is typically referred to as a ``branch-per-issue`` workflow.
As implied by the name, the idea is to create a development branch for each issue you work on.
All implementation and testing work is done within this branch. On completion,
a pull request is created for code review and subsequent merging back to the ``master`` branch.

Such branches are typically referred to as ``feature`` branches in literature,
and in guidelines which promote the ``branch-per-issue`` workflow, such as Atlassian,
they are referred to as ``task`` branches to emphasize that they are not limited to
feature development only. Herein they are referred to as ``issue`` branches to emphasize
their one-to-one connection to GHE issues.

Any and all changes to ``master`` should be merged into the relevant ``issue`` branch
before merging back to ``master``. This can be done at various times during development,
but time to handle merge conflicts should be accounted for.

* Must branch from: ``master``
* Must merge back into: ``master``
* Branch naming convention: ``[id]-[type]-[description]`` (i.e. 16-bug-add-division-by-zero-check)

If the branch does not exist yet, it should be created both locally and remotely on GHE.
Development should never be done local only. Periodically, changes in ``master`` (if any)
should be merged back into the ``issue`` branch. When development on the issue is complete,
changes should be merged into ``master`` and then the ``issue`` branch should be deleted.

Each issue should be small enough to be assigned to a single developer.
If an issue is larger in scope, it should be treated as an epic and broken down into
smaller stories.
