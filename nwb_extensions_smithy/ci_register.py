#!/usr/bin/env python
import os
import requests
import time
import sys

from . import github


# https://circleci.com/docs/api#add-environment-variable

# curl -X POST --header "Content-Type: application/json" -d '{"name":"foo", "value":"bar"}'
# https://circleci.com/api/v1/project/:username/:project/envvar?circle-token=:token

try:
    with open(os.path.expanduser("~/.nwb-extensions-smithy/circle.token"), "r") as fh:
        circle_token = fh.read().strip()
    if not circle_token:
        raise ValueError()
except (IOError, ValueError):
    print(
        "No circle token.  Create a token at https://circleci.com/account/api and\n"
        "put it in ~/.nwb-extensions-smithy/circle.token"
    )


def add_project_to_circle(user, project):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url_template = (
        "https://circleci.com/api/v1.1/project/github/{component}?"
        "circle-token={token}"
    )

    # Note, we used to check to see whether the project was already registered, but it started
    # timing out once we had too many repos, so now the approach is simply "add it always".

    url = url_template.format(
        component="{}/{}/follow".format(user, project).lower(),
        token=circle_token,
    )
    response = requests.post(url, headers={})
    # It is a strange response code, but is doing what was asked...
    if response.status_code != 400:
        response.raise_for_status()

    # Note, here we are using a non-public part of the API and may change
    # Enable building PRs from forks
    url = url_template.format(
        component="{}/{}/settings".format(user, project).lower(),
        token=circle_token,
    )
    # Disable CircleCI secrets in builds of forked PRs explicitly.
    response = requests.put(
        url,
        headers=headers,
        json={"feature_flags": {"forks-receive-secret-env-vars": False}},
    )
    if response.status_code != 200:
        response.raise_for_status()
    # Enable CircleCI builds on forked PRs.
    response = requests.put(
        url, headers=headers, json={"feature_flags": {"build-fork-prs": True}}
    )
    if response.status_code != 200:
        response.raise_for_status()

    print(" * {}/{} enabled on CircleCI".format(user, project))


def add_project_to_azure(user, project):
    from . import azure_ci_utils

    if azure_ci_utils.repo_registered(user, project):
        print(
            " * {}/{} already enabled on azure pipelines".format(user, project)
        )
    else:
        azure_ci_utils.register_repo(user, project)
        print(
            " * {}/{} has been enabled on azure pipelines".format(
                user, project
            )
        )


def get_conda_hook_info(hook_url, events):
    payload = {
        "name": "web",
        "active": True,
        "events": events,
        "config": {"url": hook_url, "content_type": "json"},
    }

    return hook_url, payload


def add_conda_forge_webservice_hooks(user, repo):
    if user != "conda-forge":
        print(
            "Unable to register {}/{} for conda-linting at this time as only "
            "conda-forge repos are supported.".format(user, repo)
        )

    headers = {"Authorization": "token {}".format(github.gh_token())}
    url = "https://api.github.com/repos/{}/{}/hooks".format(user, repo)

    # Get the current hooks to determine if anything needs doing.
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    registered = response.json()
    hook_by_url = {
        hook["config"].get("url"): hook
        for hook in registered
        if "url" in hook["config"]
    }

    hooks = []
    '''
        get_conda_hook_info(
            "https://conda-forge.herokuapp.com/conda-linting/hook",
            ["pull_request"],
        ),
        get_conda_hook_info(
            "https://conda-forge.herokuapp.com/conda-forge-feedstocks/hook",
            ["push", "repository"],
        ),
        get_conda_hook_info(
            "https://conda-forge.herokuapp.com/conda-forge-teams/hook",
            ["push", "repository"],
        ),
        get_conda_hook_info(
            "https://conda-forge.herokuapp.com/conda-forge-command/hook",
            [
                "pull_request_review",
                "pull_request",
                "pull_request_review_comment",
                "issue_comment",
                "issues",
            ],
        ),
    ]
    '''

    for hook in hooks:
        hook_url, payload = hook
        if hook_url not in hook_by_url:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                response.raise_for_status()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("user")
    parser.add_argument("project")
    args = parser.parse_args()

    #    add_project_to_circle(args.user, args.project)
    add_conda_forge_webservice_hooks(args.user, args.project)
    print("Done")
