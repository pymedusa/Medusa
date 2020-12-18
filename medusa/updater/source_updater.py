# coding=utf-8

from __future__ import unicode_literals

import logging
import os
import shutil
import stat
import sys
import tarfile

from github import GithubException

from medusa import app, helpers, notifiers
from medusa.common import VERSION
from medusa.github_client import get_github_repo, get_latest_release
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSafeSession
from medusa.updater.update_manager import UpdateManager

from requests.exceptions import RequestException

from six import text_type


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SourceUpdateManager(UpdateManager):
    def __init__(self):
        super(SourceUpdateManager, self).__init__()
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

    def __str__(self):
        return 'Source Updater'

    @staticmethod
    def _find_installed_branch():
        return app.CUR_COMMIT_BRANCH if app.CUR_COMMIT_BRANCH else 'master'

    @property
    def current_commit_hash(self):
        return self._cur_commit_hash

    @property
    def newest_commit_hash(self):
        return self._newest_commit_hash

    @property
    def current_version(self):
        return VERSION

    @property
    def newest_version(self):
        latest_release = get_latest_release(self.github_org, self.github_repo)
        return latest_release.tag_name.lstrip('v')

    @property
    def commits_behind(self):
        return self._num_commits_behind

    @property
    def commits_ahead(self):
        return self._num_commits_ahead

    def need_update(self):
        if self.branch != self._find_installed_branch():
            log.debug(u'Branch checkout: {0}->{1}', self._find_installed_branch(), self.branch)
            return True

        # need this to run first to set self._newest_commit_hash
        try:
            self.check_for_update()
        except Exception as error:
            log.warning(u"Unable to contact github, can't check for update: {0!r}", error)
            return False

        # This will be used until the first update
        if self.branch == 'master' and not self._cur_commit_hash:
            if self.is_latest_version():
                app.CUR_COMMIT_HASH = self._newest_commit_hash
                app.CUR_COMMIT_BRANCH = self.branch
                return False
            else:
                self._set_update_text()
                return True

        elif self._num_commits_behind > 0 or self._num_commits_ahead > 0:
            self._set_update_text()
            return True

        return False

    def can_update(self):
        """Whether or not the update can be performed.

        :return:
        :rtype: bool
        """
        # Version 0.4.6 is the last version which will run on python 2.7.13.
        if sys.version_info.major == 2:
            return False

        return True

    def check_for_update(self):
        """Use pygithub to ask github if there is a newer version..

        If there is a newer version it sets application's version text.

        commit_hash: hash that we're checking against
        """
        gh = get_github_repo(app.GIT_ORG, app.GIT_REPO)

        # try to get the newest commit hash and commits by comparing branch and current commit
        if self._cur_commit_hash:
            try:
                branch_compared = gh.compare(base=self.branch, head=self._cur_commit_hash)
                self._newest_commit_hash = branch_compared.base_commit.sha
                self._num_commits_behind = branch_compared.behind_by
                self._num_commits_ahead = branch_compared.ahead_by
            except Exception:
                self._newest_commit_hash = None
                self._num_commits_behind = 0
                self._num_commits_ahead = 0

        # fall back and iterate over last 100 (items per page in gh_api) commits
        if not self._newest_commit_hash:
            for cur_commit in gh.get_commits():
                if not self._newest_commit_hash:
                    self._newest_commit_hash = cur_commit.sha
                    if not self._cur_commit_hash:
                        break

                if cur_commit.sha == self._cur_commit_hash:
                    break

                # when _cur_commit_hash doesn't match anything _num_commits_behind == 100
                self._num_commits_behind += 1

        log.debug(u'cur_commit = {0}, newest_commit = {1}, num_commits_behind = {2}',
                  self._cur_commit_hash, self._newest_commit_hash, self._num_commits_behind)

    def _set_update_text(self):
        if self._num_commits_behind > 0:
            base_url = 'http://github.com/' + self.github_org + '/' + self.github_repo
            if self._newest_commit_hash:
                url = base_url + '/compare/' + self._cur_commit_hash + '...' + self._newest_commit_hash
            else:
                url = base_url + '/commits/'

            newest_text = 'There is a <a href="' + url + '" onclick="window.open(this.href); return false;">newer version available</a>'
            newest_text += " (you're " + text_type(self._num_commits_behind) + ' commit'
            if self._num_commits_behind > 1:
                newest_text += 's'
            newest_text += ' behind) &mdash; <a href="' + self.get_update_url() + '">Update Now</a>'
        else:
            url = 'http://github.com/' + self.github_org + '/' + self.github_repo + '/releases'
            newest_text = 'There is a <a href="' + url + '" onclick="window.open(this.href); return false;">newer version available</a>'
            newest_text += ' (' + self.newest_version + ') &mdash; <a href="' + self.get_update_url() + '">Update Now</a>'

        app.NEWEST_VERSION_STRING = newest_text

    def update(self):
        """Download the latest source tarball from github and installs it over the existing version."""
        tar_download_url = 'http://github.com/' + self.github_org + '/' + self.github_repo + '/tarball/' + self.branch

        try:
            # prepare the update dir
            app_update_dir = os.path.join(app.PROG_DIR, u'medusa-update')

            if os.path.isdir(app_update_dir):
                log.info(u'Clearing out update folder {0!r} before extracting', app_update_dir)
                shutil.rmtree(app_update_dir)

            log.info(u'Clearing update folder {0!r} before extracting', app_update_dir)
            os.makedirs(app_update_dir)

            # retrieve file
            log.info(u'Downloading update from {0!r}', tar_download_url)
            tar_download_path = os.path.join(app_update_dir, u'medusa-update.tar')
            helpers.download_file(tar_download_url, tar_download_path, session=self.session)

            if not os.path.isfile(tar_download_path):
                log.warning(u"Unable to retrieve new version from {0!r}, can't update", tar_download_url)
                return False

            if not tarfile.is_tarfile(tar_download_path):
                log.warning(u"Retrieved version from {0!r} is corrupt, can't update", tar_download_url)
                return False

            # extract to medusa-update dir
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
        except (GithubException, RequestException) as error:
            log.warning(u"Unable to contact github, can't check for update: {0!r}", error)
            return []
