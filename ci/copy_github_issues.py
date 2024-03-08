# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# https://www.gnu.org/licenses/gpl-3.0.html.
#
# The software distribution should follow IQM trademark policy for open-source software
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


"""
This file gets two files as input stream.
The first is a json with existing github issues,
the second is a json with existing gitlab issues. Preferably only the ones with the 'github' label.

It checks for every github issue if there is a corresponding gitlab issue.
If not it outputs the attributes to create a new gitlab issue.

"""

import sys
from http import HTTPStatus, client
import requests

if len(sys.argv) <= 1:
    raise ValueError("Gitlab token not provided (first argument in python call)")
if len(sys.argv) == 2:
    raise ValueError("Gitlab url to REST endpoint not provided (second argument in python call")

gitlab_token = sys.argv[1]
gitlab_url = sys.argv[2]
labels = len(sys.argv) > 3 and "github," + sys.argv[3] or "github"

github_url = "https://api.github.com/repos/iqm-finland/KQCircuits/issues"

# Get the issues from github
github_request = requests.get(github_url)
if github_request.status_code != HTTPStatus.OK:
    raise requests.exceptions.HTTPError(
        f"HTTP Error {github_request.status_code}: {client.responses[github_request.status_code]}"
    )

# Get the open issues from gitlab
gitlab_header = {"PRIVATE-TOKEN": gitlab_token}
gitlab_request = requests.get(gitlab_url, headers=gitlab_header, params={"labels": "github"})
if gitlab_request.status_code != HTTPStatus.OK:
    raise requests.exceptions.HTTPError(
        f"HTTP Error {gitlab_request.status_code}: {client.responses[gitlab_request.status_code]}"
    )

github_issues = github_request.json()
gitlab_issues = gitlab_request.json()

new_issue_found = False
for gh_issue in github_issues:
    issue_number = gh_issue["number"]
    url = gh_issue["html_url"]
    for gl_issue in gitlab_issues:
        if url in gl_issue["description"]:
            break
    else:  # URL not found in existing gitlab issues, so corresponding issue does not exist. Make it
        new_issue_found = True
        title = gh_issue["title"]
        user = gh_issue["user"]
        header = (
            f"This issue was automatically copied from GitHub by the CI/CD. \n"
            f"Original {url}  \n"
            f"Original GitHub reporter: [{user['login']}]({user['html_url']})  \n"
            f"Do not remove or edit this header or the `GitHub` label to avoid duplicating the issue.  \n"
            f"Original (unedited) description below. Feel free to edit anything below the following line.\n\n"
            f"---\n\n"
        )

        description = f"{header}{gh_issue['body']}"

        post_attributes = {"title": title, "description": description, "labels": labels}

        print("New issue found, posting to gitlab")
        print("Title: " + title)
        gitlab_post = requests.post(gitlab_url, headers=gitlab_header, data=post_attributes)
        if gitlab_post.status_code == HTTPStatus.CREATED:
            print("Issue successfully created")
            print(f"Issue can be found at {gitlab_post.json()['web_url']}")
            print("---")
        else:
            print("Error creating the issue")
            raise requests.exceptions.HTTPError(
                f"HTTP Error {gitlab_post.status_code}: {client.responses[gitlab_post.status_code]}"
            )

if not new_issue_found:
    print("No new issues found")
