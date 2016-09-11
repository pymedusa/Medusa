# coding=utf-8
"""Github client module."""

import logging

import github

logger = logging.getLogger(__name__)


def authenticate(username, password, quiet=False):
    """Github authentication.

    :param username:
    :type username: string
    :param password:
    :type password: string
    :param quiet:
    :type quiet: bool
    :return:
    :rtype: Github or None
    """
    try:
        if username or password:
            gh = github.MainClass.Github(login_or_token=username, password=password, user_agent='Medusa')

            # Make a simple request to validate username and password
            gh.get_rate_limit()

            return gh
    except github.BadCredentialsException:
        if not quiet:
            logger.warning('Invalid Github credentials. Please check your Github credentials in Medusa settings.')


def get_github_repo(organization, repo, gh=None):
    """Return the github repository.

    :param organization:
    :type organization: string
    :param repo:
    :type repo: string
    :param gh:
    :type gh: Github
    :return:
    :rtype github.Repository.Repository
    """
    gh = gh or github.MainClass.Github(user_agent='Medusa')

    return gh.get_organization(organization).get_repo(repo)
