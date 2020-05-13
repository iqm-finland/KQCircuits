Issues
^^^^^^

The title of an issue should consist of a short and concise description of the problem
that it addresses. If possible, the description used in the corresponding branch name
should be shorter, and it may be abbreviated if appropriate. The title of the pull request (PR)
created from the branch should describe what has changed rather than repeating the issue description. This is useful for cases when an issue is solved in stages via multiple PRs.

In order to follow these guidelines, a new repository must be setup with predefined label definitions.
Since there is no in-built Github support for this, we need to use a batch script for standardizing
this process.

Each new issue will be tagged with upto four different categories of labels to indicate
``type``, ``priority``, and optionally ``effort``. Each label will be prefixed
with its corresponding category so that the resulting label format will be
``category:{value}``, for example ``type:bug``. Category values are restricted to
a set of allowed values for each type. Lowercase letters should be used for both the category
prefixes and values. Only one of each category labels may be applied to an issue.

In addition to the above recommendations, feel free to use additional issue labels as needed.

.. raw:: html

    <style> .red {color:#e6194B} </style>
    <style> .green {color:#3cb44b} </style>
    <style> .yellow {color:#ffe119} </style>
    <style> .blue {color:#4363d8} </style>
    <style> .orange {color:#f58231} </style>
    <style> .brown {color:#9A6324} </style>
    <style> .gray {color:#a9a9a9} </style>

.. role:: red

.. role:: green

.. role:: yellow

.. role:: blue

.. role:: orange

.. role:: brown

.. role:: gray

Type
,,,,

The ``type`` labels listed below are quite general, and a project may require more specific types.
In this case, additional ``type`` labels may be used in an ad-hoc manner as long as
these labels are lowercase and limited to single words.

.. csv-table::
   :header: "Category", "Value", "Color"
   :widths: 15, 15, 30

   "type", "bug", :red:`███` red (#e6194B)
   "type", "feature", :green:`███` green (#3cb44b)
   "type", "discussion", :blue:`███` blue (#4363d8)
   "type", "refactoring", :orange:`███` orange (#f58231)
   "type", "testing", :yellow:`███` yellow (#ffe119)
   "type", "documentation", :brown:`███` brown (#9A6324)

Impact
,,,,,,

.. csv-table::
   :header: "Category", "Value", "Color"
   :widths: 15, 15, 30

   "impact", "low", :green:`███` green (#3cb44b)
   "impact", "medium", :yellow:`███` yellow (#ffe119)
   "impact", "high", :orange:`███` orange (#f58231)
   "impact", "critical", :red:`███` red (#e6194B)

Effort
,,,,,,

The ``effort`` label is optional, and it should be used when applicable
and/or needed to help with prioritizing issues.

.. csv-table::
   :header: "Category", "Value", "Color"
   :widths: 15, 15, 30

   "effort", "unknown", :gray:`███` gray (#a9a9a9)
   "effort", "low", :green:`███` green (#3cb44b)
   "effort", "medium", :yellow:`███` yellow (#ffe119)
   "effort", "high", :red:`███` red (#e6194B)
