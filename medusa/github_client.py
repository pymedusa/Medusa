# coding=utf-8
"""Github client module."""
from __future__ import unicode_literals

import logging

import github

logger = logging.getLogger(__name__)

OPTIONS = {
    'user_agent': 'Medusa',
    'per_page': 100,
}


def authenticate(username, password):
    """Github authentication.

    :param username:
    :type username: string
    :param password:
    :type password: string
    :return:
    :rtype: Github or None
    """
    try:
        if username or password:
            gh = github.MainClass.Github(login_or_token=username, password=password, **OPTIONS)

            # Make a simple request to validate username and password
            gh.get_rate_limit()

            return gh
    except github.BadCredentialsException:
        logger.warning('Invalid Github credentials. Please check your Github credentials in Medusa settings.')
    except github.GithubException as e:
        logger.debug('Unable to contact Github: {ex!r}', ex=e)
        raise


def token_authenticate(token):
    """Github authentication.

    :param token:
    :type token: string
    :return:
    :rtype: Github or None
    """
    try:
        if token:
            gh = github.MainClass.Github(login_or_token=token, **OPTIONS)

            # Make a simple request to validate username and password
            gh.get_rate_limit()

            return gh
    except github.BadCredentialsException:
        logger.warning('Invalid Github credentials. Please check your Github credentials in Medusa settings.')
    except github.TwoFactorException:
        logger.warning('Invalid Github token. Please check your Github token in Medusa settings.')
    except github.GithubException as e:
        logger.debug('Unable to contact Github: {ex!r}', ex=e)
        raise


def get_user(gh=None):
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
    try:
        gh = gh or github.MainClass.Github(**OPTIONS)
        return gh.get_user().login
    except github.GithubException as e:
        logger.debug('Unable to contact Github: {ex!r}', ex=e)
        raise


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
    try:
        gh = gh or github.MainClass.Github(**OPTIONS)
        return gh.get_organization(organization).get_repo(repo)
    except github.GithubException as e:
        logger.debug('Unable to contact Github: {ex!r}', ex=e)
        raise


def get_latest_release(organization, repo, gh=None):
    """Return the latest release of a repository.

    :param repo:
    :type repo: string
    :param gh:
    :type gh: Github
    :return:
    :rtype github.GitRelease.GitRelease
    """
    try:
        gh = gh or github.MainClass.Github(**OPTIONS)
        return gh.get_organization(organization).get_repo(repo).get_latest_release()
    except github.GithubException as e:
        logger.debug('Unable to contact Github: {ex!r}', ex=e)
        raise
