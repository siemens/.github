"""
A helper script to create issues in all repositories in a GitHub organization
before adding default organization-wide community files.

Use with the following environment variables:

GH_ORG: The GitHub organization to create the issues in
GH_TOKEN: GitHub token to use to authenticate and create the issues
GH_COMMUNITY_FILE: Existing community file. Skips issue creation in repositories where present.
GH_ISSUE_TITLE: Title of the issue to create or update
GH_ISSUE_DESCRIPTION: Description to create or update existing issue with
"""

import os
import sys

from github import Auth, Github
from github.GithubException import GithubException, UnknownObjectException
from loguru import logger


def get_contents_if_exists(repo, path):
    try:
        return repo.get_contents(path)
    except UnknownObjectException:
        return []
    except GithubException as e:
        # Handle empty repositories as well
        if e.status == 404:
            return []
        raise e


def main():
    try:
        issue_title = os.environ["GH_ISSUE_TITLE"]
        issue_description = os.environ["GH_ISSUE_DESCRIPTION"]
        token = os.environ["GH_TOKEN"]
        org_name = os.environ["GH_ORG"]
    except KeyError as e:
        sys.exit(f"Missing environment variable: {e}")

    auth = Auth.Token(token)
    gh = Github(auth=auth)
    dry_run = os.getenv("DRY_RUN") == "true"
    existing_file = os.getenv("GH_COMMUNITY_FILE")

    org = gh.get_organization(org_name)

    for repo in org.get_repos(type="sources"):
        logger.info(f"Processing {repo.html_url}")

        contents = (
            get_contents_if_exists(repo, ".")
            + get_contents_if_exists(repo, "docs")
            + get_contents_if_exists(repo, ".github")
        )

        if repo.archived:
            logger.info(f"{repo.html_url} is archived, skipping.")
            continue

        if not repo.has_issues:
            logger.info(f"{repo.html_url} has disabled issues, skipping.")
            continue

        if existing_file and any([f.path.endswith(existing_file) for f in contents]):
            logger.info(f"{repo.html_url} contains existing {existing_file}, skipping.")
            continue

        try:
            existing_issue = next(
                iter(
                    gh.search_issues(
                        f"is:issue repo:{repo.full_name} in:title {issue_title}"
                    )
                ),
                None,
            )
            if existing_issue:
                if dry_run:
                    logger.info(f"Would update existing issue in {repo.html_url}")
                    continue

                existing_issue.edit(body=issue_description)
                logger.info(f"Updated existing issue {existing_issue.html_url}")
                continue

            if dry_run:
                logger.info(f"Would create issue {repo.html_url}")
                continue

            issue = repo.create_issue(title=issue_title, body=issue_description)
            logger.info(f"Created issue {issue.html_url}")

        except GithubException:
            logger.warning(f"Failed to create issue in {repo.html_url}")


if __name__ == "__main__":
    main()
