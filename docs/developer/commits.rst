Commits
^^^^^^^

Follow the `Conventional Commits specification <https://www.conventionalcommits.org/en/v1.0.0/>`__
for all commit comments. According to these specifications,
the commit structure should be structured as follows:

::

    [optional scope]: <description>
    <blank line>
    [optional body]
    <blank line>
    #<issue id>-<type>
    [optional footer(s)]

Type must be one of the following:

-  **feat**: New feature
-  **fix**: Bug fix
-  **docs**: Documentation only changes
-  **style**: Changes that do not affect the meaning of the code
   (i.e. white-space, formatting, missing semi-colons)
-  **refactor**: Code change that neither fixes a bug nor adds a feature
-  **perf**: Code change that improves performance
-  **test**: Adding missing tests
-  **chore**: Changes to the build process or auxiliary tools and
   libraries such as documentation generation

The description contains a short summary of the code changes. Limit the description line
to 50 characters. This is mandatory, github will truncate otherwise making the commit
hard to read. No line may exceed 100 characters. This makes it easier to read the message
on GHE as well as in various git tools. Also, if you are used to making frequent
work-in-progress commits, make sure you indicate this in the description section (i.e. WIP).

It is highly recommended to include a footer which contains a reference to
the corresponding issue via hash and id.
