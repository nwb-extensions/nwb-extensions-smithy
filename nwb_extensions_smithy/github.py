import os
import os.path
from random import choice

from git import Repo

from github import Github
from github.GithubException import GithubException
from github.Team import Team
import github

from .metadata import MetaData


def gh_token():
    try:
        with open(os.path.expanduser("~/.nwb-extensions-smithy/github.token"), "r") as fh:
            token = fh.read().strip()
        if not token:
            raise ValueError()
    except (IOError, ValueError):
        msg = (
            "No GitHub token. Go to https://github.com/settings/tokens/new and generate\n"
            "a token with repo access. Put it in ~/.nwb-extensions-smithy/github.token"
        )
        raise RuntimeError(msg)
    return token


def create_team(org, name, description, repo_names=[]):
    team = org.create_team(name, repo_names=repo_names, privacy="closed", description=description)
    return team


def has_in_members(team, member):
    status, headers, data = team._requester.requestJson(
        "GET", team.url + "/members/" + member
    )
    return status == 204


# TODO do not use cached team
def get_cached_team(org, team_name, description=""):
    cached_file = os.path.expanduser(
        "~/.nwb-extensions-smithy/{}-{}-team".format(org.login, team_name)
    )
    try:
        with open(cached_file, "r") as fh:
            team_id = int(fh.read().strip())
            return org.get_team(team_id)
    except IOError:
        pass

    try:
        repo = org.get_repo("{}-record".format(team_name))
        team = next((team for team in repo.get_teams() if team.name == team_name), None)
        if team:
            return team
    except GithubException:
        pass

    team = next((team for team in org.get_teams() if team.name == team_name), None)
    if not team:
        if description:
            team = create_team(org, team_name, description, [])
        else:
            raise RuntimeError("Couldn't find team {}".format(team_name))

    with open(cached_file, "w") as fh:
        fh.write(str(team.id))

    return team


def get_github_exception_msg(exception):
    return exception.data.get("errors", [{}])[0].get("message", "")


def create_github_repo(args):
    token = gh_token()
    meta = MetaData(args.record_directory)
    namespace = meta.name()

    gh = Github(token)
    org = gh.get_organization(args.organization)

    repo_name = "{}-record".format(namespace)
    try:
        gh_repo = org.create_repo(
            repo_name,
            has_wiki=False,
            description="An NWB Extension Catalog record for the extension {}.".format(namespace),
        )
        print("Created {} on GitHub".format(gh_repo.full_name))
    except GithubException as gh_except:
        if get_github_exception_msg(gh_except) != u"name already exists on this account":
            raise
        gh_repo = org.get_repo(repo_name)
        print("GitHub repository already exists.")

    # Now add this new repo as a remote on the local clone.
    repo = Repo(args.record_directory)
    remote_name = args.remote_name.strip()
    if remote_name:
        if remote_name in [remote.name for remote in repo.remotes]:
            existing_remote = repo.remotes[remote_name]
            if existing_remote.url != gh_repo.ssh_url:
                print(
                    "Remote {} already exists, and doesn't point to {} "
                    "(it points to {}).".format(
                        remote_name, gh_repo.ssh_url, existing_remote.url
                    )
                )
        else:
            repo.create_remote(remote_name, gh_repo.ssh_url)
            print("Setting remote %s to %s" % (remote_name, gh_repo.ssh_url))

    if args.add_self_collaborator:
        gh_repo.add_to_collaborators(gh.get_user().login, "push")
        print("Adding self (%s) to %s" % (gh.get_user().login, gh_repo.full_name))

    if args.extra_admin_users is not None:
        for user in args.extra_admin_users:
            gh_repo.add_to_collaborators(user, "admin")
            print("Adding user %s as admin to %s" % (gh.get_user().login, gh_repo.full_name))

    if args.add_teams:
        configure_github_team(meta, gh_repo, org, namespace, gh)


def accept_all_repository_invitations(gh):
    user = gh.get_user()
    invitations = github.PaginatedList.PaginatedList(
        github.Invitation.Invitation,
        user._requester,
        user.url + "/repository_invitations",
        None,
    )
    for invite in invitations:
        invite._requester.requestJsonAndCheck("PATCH", invite.url)


def remove_from_project(gh, org, project):
    user = gh.get_user()
    repo = gh.get_repo("{}/{}".format(org, project))
    repo.remove_from_collaborators(user.login)


def configure_github_team(meta, gh_repo, org, namespace, gh):

    # Add a team for this repo and add the maintainers to it.
    superlative = [
        "awesome",
        "slick",
        "formidable",
        "awe-inspiring",
        "breathtaking",
        "magnificent",
        "wonderous",
        "stunning",
        "astonishing",
        "superb",
        "splendid",
        "impressive",
        "unbeatable",
        "excellent",
        "amazing",
        "outstanding",
        "exalted",
        "standout",
        "smashing",
    ]

    maintainers = set(meta.meta.get("maintainers", []))
    maintainers = set(maintainer.lower() for maintainer in maintainers)
    maintainer_teams = set(m for m in maintainers if "/" in m)
    maintainers = set(m for m in maintainers if "/" not in m)

    # Try to get team or create it if it doesn't exist.
    team_name = namespace
    current_maintainer_teams = list(gh_repo.get_teams())
    team = next(
        (team for team in current_maintainer_teams if team.name == team_name), None
    )
    current_maintainers = set()
    if not team:
        try:
            team = create_team(
                org,
                team_name,
                "The {} {} contributors!".format(choice(superlative), team_name),
            )
            team.add_to_repos(gh_repo)
        except GithubException as gh_except:
            if get_github_exception_msg(gh_except) == u"Name has already been taken":
                raise RuntimeError(
                    f"Team {team_name} already exists on organization {org.login}."
                )
            else:
                raise
    else:
        current_maintainers = set([e.login.lower() for e in team.get_members()])

    # Get the all-members team
    description = "All of the awesome {} contributors!".format(org.login)
    all_members_team = get_cached_team(org, "all-members", description)
    new_org_members = set()

    # Add only the new maintainers to the team.
    # Also add the new maintainers to all-members if not already included.
    for new_maintainer in maintainers - current_maintainers:
        print(
            "Adding a new member ({}) to team {}.".format(new_maintainer, team_name)
        )
        new_maintainer_user = gh.get_user(new_maintainer)
        team.add_membership(new_maintainer_user)

        if not has_in_members(all_members_team, new_maintainer):
            print(
                "Adding a new member ({}) to organization {}. Welcome! :)".format(
                    new_maintainer, org.login
                )
            )
            all_members_team.add_membership(new_maintainer_user)
            new_org_members.add(new_maintainer)

    # Mention any maintainers that need to be removed (unlikely here).
    for old_maintainer in current_maintainers - maintainers:
        print(
            "AN OLD MEMBER ({}) NEEDS TO BE REMOVED FROM {}".format(
                old_maintainer, gh_repo
            )
        )

    # Add any new maintainer team
    maintainer_teams = set(
        m.split("/")[1] for m in maintainer_teams if m.startswith(str(org.login))
    )
    current_maintainer_teams = [team.name for team in current_maintainer_teams]
    for maintainer_team in maintainer_teams - set(current_maintainer_teams):
        print(
            "Adding a new team ({}) to {}. Welcome! :)".format(
                maintainer_team, org.login
            )
        )

        team = get_cached_team(org, maintainer_team)
        team.add_to_repos(gh_repo)

    return maintainers, current_maintainers, new_org_members
