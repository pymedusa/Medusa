# coding=utf-8

from __future__ import unicode_literals

import logging
import os
import shutil
import stat
import tarfile

from github import GithubException

from medusa import app, helpers, notifiers
from medusa.github_client import get_github_repo
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSafeSession
from medusa.updater.update_manager import UpdateManager


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class DockerUpdateManager(UpdateManager):
    def __init__(self):
        super(DockerUpdateManager, self).__init__()
        self.github_org = self.get_github_org()
        self.github_repo = self.get_github_repo()

        self.branch = app.BRANCH
        if app.BRANCH == '':
            self.branch = self._find_installed_branch()

        self._cur_commit_hash = app.CUR_COMMIT_HASH
        self._newest_commit_hash = None
        self._num_commits_behind = 0
        self._num_commits_ahead = 0

        self.session = MedusaSafeSession()

    @staticmethod
    def _find_installed_branch():
        return app.CUR_COMMIT_BRANCH if app.CUR_COMMIT_BRANCH else 'master'

    def get_cur_commit_hash(self):
        return self._cur_commit_hash

    def get_newest_commit_hash(self):
        return self._newest_commit_hash

    @staticmethod
    def get_cur_version():
        return ''

    @staticmethod
    def get_newest_version():
        return ''

    def get_num_commits_behind(self):
        return self._num_commits_behind

    def get_num_commits_ahead(self):
        return self._num_commits_ahead

    def need_update(self):
        # need this to run first to set self._newest_commit_hash
        try:
            self._check_github_for_update()
        except Exception as error:
            log.warning(u"Unable to contact github, can't check for update: {0!r}", error)
            return False

        if self.branch != self._find_installed_branch():
            log.debug(u'Branch checkout: {0}->{1}', self._find_installed_branch(), self.branch)
            return True

        if not self._cur_commit_hash or self._num_commits_behind > 0 or self._num_commits_ahead > 0:
            return True

        return False

    def can_update(self):
        """Whether or not the update can be performed.

        :return:
        :rtype: bool
        """
        return True

    def _check_github_for_update(self):
        """Use pygithub to ask github if there is a newer version..

        If there is a newer version it sets application's version text.

        commit_hash: hash that we're checking against
        """

        self._num_commits_behind = 0
        self._newest_commit_hash = None

        gh = get_github_repo(app.GIT_ORG, app.GIT_REPO)
        # try to get newest commit hash and commits behind directly by comparing branch and current commit
        if self._cur_commit_hash:
            try:
                branch_compared = gh.compare(base=self.branch, head=self._cur_commit_hash)
                self._newest_commit_hash = branch_compared.base_commit.sha
                self._num_commits_behind = branch_compared.behind_by
                self._num_commits_ahead = branch_compared.ahead_by
            except Exception:  # UnknownObjectException
                self._newest_commit_hash = ''
                self._num_commits_behind = 0
                self._num_commits_ahead = 0
                self._cur_commit_hash = ''

        # fall back and iterate over last 100 (items per page in gh_api) commits
        if not self._newest_commit_hash:

            for curCommit in gh.get_commits():
                if not self._newest_commit_hash:
                    self._newest_commit_hash = curCommit.sha
                    if not self._cur_commit_hash:
                        break

                if curCommit.sha == self._cur_commit_hash:
                    break

                # when _cur_commit_hash doesn't match anything _num_commits_behind == 100
                self._num_commits_behind += 1

        log.debug(u'cur_commit = {0}, newest_commit = {1}, num_commits_behind = {2}',
                  self._cur_commit_hash, self._newest_commit_hash, self._num_commits_behind)

    def set_newest_text(self):
        """Set an update text, when running in a docker container."""
        app.NEWEST_VERSION_STRING = None

        if not self._cur_commit_hash or self._num_commits_behind > 0:
            log.debug(u'There is an update available, Medusa is running in a docker container, so auto updating is disabled.')
            app.NEWEST_VERSION_STRING = 'There is an update available: please pull the latest docker image, ' \
                                        'and rebuild your container to update'

    def update(self):
        """
        Downloads the latest source tarball from github and installs it over the existing version.
        """

        tar_download_url = 'http://github.com/' + self.github_org + '/' + self.github_repo + '/tarball/' + self.branch

        try:
            # prepare the update dir
            app_update_dir = os.path.join(app.PROG_DIR, u'sr-update')

            if os.path.isdir(app_update_dir):
                log.info(u'Clearing out update folder {0!r} before extracting', app_update_dir)
                shutil.rmtree(app_update_dir)

            log.info(u'Clearing update folder {0!r} before extracting', app_update_dir)
            os.makedirs(app_update_dir)

            # retrieve file
            log.info(u'Downloading update from {0!r}', tar_download_url)
            tar_download_path = os.path.join(app_update_dir, u'sr-update.tar')
            helpers.download_file(tar_download_url, tar_download_path, session=self.session)

            if not os.path.isfile(tar_download_path):
                log.warning(u"Unable to retrieve new version from {0!r}, can't update", tar_download_url)
                return False

            if not tarfile.is_tarfile(tar_download_path):
                log.warning(u"Retrieved version from {0!r} is corrupt, can't update", tar_download_url)
                return False

            # extract to sr-update dir
            log.info(u'Extracting file {0}', tar_download_path)
            tar = tarfile.open(tar_download_path)
            tar.extractall(app_update_dir)
            tar.close()

            # delete .tar.gz
            log.info(u'Deleting file {0}', tar_download_path)
            os.remove(tar_download_path)

            # find update dir name
            update_dir_contents = [x for x in os.listdir(app_update_dir) if
                                   os.path.isdir(os.path.join(app_update_dir, x))]
            if len(update_dir_contents) != 1:
                log.warning(u'Invalid update data, update failed: {0}', update_dir_contents)
                return False
            content_dir = os.path.join(app_update_dir, update_dir_contents[0])

            # walk temp folder and move files to main folder
            log.info(u'Moving files from {0} to {1}', content_dir, app.PROG_DIR)
            for dirname, _, filenames in os.walk(content_dir):  # @UnusedVariable
                dirname = dirname[len(content_dir) + 1:]
                for curfile in filenames:
                    old_path = os.path.join(content_dir, dirname, curfile)
                    new_path = os.path.join(app.PROG_DIR, dirname, curfile)

                    # Avoid DLL access problem on WIN32/64
                    # These files needing to be updated manually
                    # or find a way to kill the access from memory
                    extension = os.path.splitext(curfile)[1]
                    if extension == '.dll':
                        try:
                            log.debug(u'Special handling for {0}', curfile)
                            os.chmod(new_path, stat.S_IWRITE)
                            os.remove(new_path)
                            os.renames(old_path, new_path)
                        except Exception as e:
                            log.debug(u'Unable to update {0}: {1!r}', new_path, e)
                            os.remove(old_path)  # Trash the updated file without moving in new path
                        continue

                    if os.path.isfile(new_path):
                        os.remove(new_path)
                    os.renames(old_path, new_path)

            app.CUR_COMMIT_HASH = self._newest_commit_hash
            app.CUR_COMMIT_BRANCH = self.branch

        except Exception as e:
            log.exception(u'Error while trying to update: {0}', e)
            return False

        # Notify update successful
        try:
            notifiers.notify_git_update(app.CUR_COMMIT_HASH or '')
        except Exception:
            log.debug(u'Unable to send update notification. Continuing the update process')
        return True

    @staticmethod
    def list_remote_branches():
        try:
            gh = get_github_repo(app.GIT_ORG, app.GIT_REPO)
            return [x.name for x in gh.get_branches() if x]
        except GithubException as error:
            log.warning(u"Unable to contact github, can't check for update: {0!r}", error)
            return []
