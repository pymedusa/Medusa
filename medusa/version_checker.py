# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals

import datetime
import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import tarfile
import time
from builtins import object
from builtins import str
from logging import DEBUG, WARNING

from medusa import app, db, helpers, notifiers, ui
from medusa.github_client import get_github_repo
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSafeSession


ERROR_MESSAGE = ('Unable to find your git executable. Set git executable path in Advanced Settings '
                 'OR shutdown application and delete your .git folder and run from source to enable updates.')

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class CheckVersion(object):
    """Version check class meant to run as a thread object with the sr scheduler."""

    def __init__(self):
        self.updater = None
        self.install_type = None
        self.amActive = False
        self.install_type = self.find_install_type()
        if self.install_type == 'git':
            self.updater = GitUpdateManager()
        elif self.install_type == 'source':
            self.updater = SourceUpdateManager()

        self.session = MedusaSafeSession()

    def run(self, force=False):

        self.amActive = True

        # Update remote branches and store in app.GIT_REMOTE_BRANCHES
        self.list_remote_branches()

        if self.updater:
            # set current branch version
            app.BRANCH = self.get_branch()

            if self.check_for_new_version(force):
                if app.AUTO_UPDATE:
                    log.info(u'New update found, starting auto-updater ...')
                    ui.notifications.message('New update found, starting auto-updater')
                    if self.run_backup_if_safe():
                        if app.version_check_scheduler.action.update():
                            log.info(u'Update was successful!')
                            ui.notifications.message('Update was successful')
                            app.events.put(app.events.SystemEvent.RESTART)
                        else:
                            log.info(u'Update failed!')
                            ui.notifications.message('Update failed!')

            self.check_for_new_news(force)

        self.amActive = False

    def run_backup_if_safe(self):
        return self.safe_to_update() is True and self._runbackup() is True

    def _runbackup(self):
        # Do a system backup before update
        log.info(u'Config backup in progress...')
        ui.notifications.message('Backup', 'Config backup in progress...')
        try:
            backupDir = os.path.join(app.DATA_DIR, app.BACKUP_DIR)
            if not os.path.isdir(backupDir):
                os.mkdir(backupDir)

            if self._keeplatestbackup(backupDir) and self._backup(backupDir):
                log.info(u'Config backup successful, updating...')
                ui.notifications.message('Backup', 'Config backup successful, updating...')
                return True
            else:
                log.warning(u'Config backup failed, aborting update')
                ui.notifications.message('Backup', 'Config backup failed, aborting update')
                return False
        except Exception as e:
            log.error(u'Update: Config backup failed. Error: {0!r}', e)
            ui.notifications.message('Backup', 'Config backup failed, aborting update')
            return False

    @staticmethod
    def _keeplatestbackup(backupDir=None):
        if not backupDir:
            return False

        import glob
        files = glob.glob(os.path.join(backupDir, '*.zip'))
        if not files:
            return True

        now = time.time()
        newest = files[0], now - os.path.getctime(files[0])
        for f in files[1:]:
            age = now - os.path.getctime(f)
            if age < newest[1]:
                newest = f, age
        files.remove(newest[0])

        for f in files:
            os.remove(f)

        return True

    # TODO: Merge with backup in helpers
    @staticmethod
    def _backup(backupDir=None):
        if not backupDir:
            return False
        source = [
            os.path.join(app.DATA_DIR, app.APPLICATION_DB),
            app.CONFIG_FILE,
            os.path.join(app.DATA_DIR, app.FAILED_DB),
            os.path.join(app.DATA_DIR, app.CACHE_DB)
        ]
        target = os.path.join(backupDir, app.BACKUP_FILENAME.format(timestamp=time.strftime('%Y%m%d%H%M%S')))

        for (path, dirs, files) in os.walk(app.CACHE_DIR, topdown=True):
            for dirname in dirs:
                if path == app.CACHE_DIR and dirname not in ['images']:
                    dirs.remove(dirname)
            for filename in files:
                source.append(os.path.join(path, filename))

        return helpers.backup_config_zip(source, target, app.DATA_DIR)

    def safe_to_update(self):

        def db_safe(self):
            message = {
                'equal': {
                    'type': DEBUG,
                    'text': u'We can proceed with the update. New update has same DB version'},
                'upgrade': {
                    'type': WARNING,
                    'text': u"We can't proceed with the update. New update has a new DB version. Please manually update"},
                'downgrade': {
                    'type': WARNING,
                    'text': u"We can't proceed with the update. New update has a old DB version. It's not possible to downgrade"},
            }
            try:
                result = self.getDBcompare()
                if result in message:
                    log.log(message[result]['type'], message[result]['text'])  # unpack the result message into a log entry
                else:
                    log.warning(u"We can't proceed with the update. Unable to check remote DB version. Error: {0}", result)
                return result in ['equal']  # add future True results to the list
            except Exception as error:
                log.error(u"We can't proceed with the update. Unable to compare DB version. Error: {0!r}", error)
                return False

        def postprocessor_safe():
            if not app.auto_post_processor_scheduler.action.amActive:
                log.debug(u'We can proceed with the update. Post-Processor is not running')
                return True
            else:
                log.debug(u"We can't proceed with the update. Post-Processor is running")
                return False

        def showupdate_safe():
            if not app.show_update_scheduler.action.amActive:
                log.debug(u'We can proceed with the update. Shows are not being updated')
                return True
            else:
                log.debug(u"We can't proceed with the update. Shows are being updated")
                return False

        db_safe = db_safe(self)
        postprocessor_safe = postprocessor_safe()
        showupdate_safe = showupdate_safe()

        if db_safe and postprocessor_safe and showupdate_safe:
            log.debug(u'Proceeding with auto update')
            return True
        else:
            log.debug(u'Auto update aborted')
            return False

    def getDBcompare(self):
        """
        Compare the current DB version with the new branch version.

        :return: 'upgrade', 'equal', or 'downgrade'
        """
        try:
            self.updater.need_update()
            cur_hash = str(self.updater.get_newest_commit_hash())
            assert len(cur_hash) == 40, 'Commit hash wrong length: {length} hash: {hash}'.format(
                length=len(cur_hash), hash=cur_hash)

            check_url = 'http://cdn.rawgit.com/{org}/{repo}/{commit}/medusa/databases/main_db.py'.format(
                org=app.GIT_ORG, repo=app.GIT_REPO, commit=cur_hash)
            response = self.session.get(check_url)

            # Get remote DB version
            match_max_db = re.search(r'MAX_DB_VERSION\s*=\s*(?P<version>\d{2,3})', response.text)
            new_branch_major_db_version = int(match_max_db.group('version')) if match_max_db else None
            match_minor_db = re.search(r'CURRENT_MINOR_DB_VERSION\s*=\s*(?P<version>\d{1,2})', response.text)
            new_branch_min_db_version = int(match_minor_db.group('version')) if match_minor_db else None

            # Check local DB version
            main_db_con = db.DBConnection()
            cur_branch_major_db_version, cur_branch_minor_db_version = main_db_con.checkDBVersion()

            if any([cur_branch_major_db_version is None, cur_branch_minor_db_version is None,
                    new_branch_major_db_version is None, new_branch_min_db_version is None]):
                return 'Could not compare database versions, aborting'

            if new_branch_major_db_version > cur_branch_major_db_version:
                return 'upgrade'
            elif new_branch_major_db_version == cur_branch_major_db_version:
                if new_branch_min_db_version < cur_branch_minor_db_version:
                    return 'downgrade'
                elif new_branch_min_db_version > cur_branch_minor_db_version:
                    return 'upgrade'
                return 'equal'
            else:
                return 'downgrade'
        except Exception as e:
            return repr(e)

    @staticmethod
    def find_install_type():
        """
        Determines how this copy of sr was installed.

        :return: type of installation. Possible values are:
            'win': any compiled windows build
            'git': running from source using git
            'source': running from source without git
        """
        # check if we're a windows build
        if app.BRANCH.startswith('build '):
            install_type = 'win'
        elif os.path.isdir(os.path.join(app.PROG_DIR, u'.git')):
            install_type = 'git'
        else:
            install_type = 'source'

        return install_type

    def check_for_new_version(self, force=False):
        """
        Check the internet for a newer version.

        :force: if true the VERSION_NOTIFY setting will be ignored and a check will be forced
        :return: bool, True for new version or False for no new version.
        """
        if not self.updater or (not app.VERSION_NOTIFY and not app.AUTO_UPDATE and not force):
            log.info(u'Version checking is disabled, not checking for the newest version')
            app.NEWEST_VERSION_STRING = None
            return False

        # checking for updates
        if not app.AUTO_UPDATE:
            log.info(u'Checking for updates using {0}', self.install_type.upper())

        if not self.updater.need_update():
            app.NEWEST_VERSION_STRING = None

            if force:
                ui.notifications.message('No update needed')
                log.info(u'No update needed')

            # no updates needed
            return False

        # found updates
        self.updater.set_newest_text()
        return self.updater.can_update()

    def check_for_new_news(self, force=False):
        """
        Check GitHub for the latest news.

        :return: unicode, a copy of the news
        :force: ignored
        """
        # Grab a copy of the news
        log.debug(u'Checking GitHub for latest news.')
        response = self.session.get(app.NEWS_URL)
        if not response or not response.text:
            log.debug(u'Could not load news from URL: %s', app.NEWS_URL)
            return

        try:
            last_read = datetime.datetime.strptime(app.NEWS_LAST_READ, '%Y-%m-%d')
        except ValueError:
            log.warning(u'Invalid news last read date: %s', app.NEWS_LAST_READ)
            last_read = 0

        news = response.text
        app.NEWS_UNREAD = 0
        got_latest = False
        for match in re.finditer(r'^####\s*(\d{4}-\d{2}-\d{2})\s*####', news, re.M):
            if not got_latest:
                got_latest = True
                app.NEWS_LATEST = match.group(1)

            try:
                if datetime.datetime.strptime(match.group(1), '%Y-%m-%d') > last_read:
                    app.NEWS_UNREAD += 1
            except ValueError:
                log.warning(u'Unable to match latest news date. Repository news date: %s', match.group(1))
                pass

        return news

    def need_update(self):
        if self.updater:
            return self.updater.need_update()

    def update(self):
        if self.updater:
            # update branch with current config branch value
            self.updater.branch = app.BRANCH

            # check for updates
            if self.updater.need_update():
                return self.updater.update()

    def list_remote_branches(self):
        if self.updater:
            app.GIT_REMOTE_BRANCHES = self.updater.list_remote_branches()
        return app.GIT_REMOTE_BRANCHES

    def get_branch(self):
        if self.updater:
            return self.updater.branch


class UpdateManager(object):
    @staticmethod
    def get_github_org():
        return app.GIT_ORG

    @staticmethod
    def get_github_repo():
        return app.GIT_REPO

    @staticmethod
    def get_update_url():
        return app.WEB_ROOT + "/home/update/?pid=" + str(app.PID)


class GitUpdateManager(UpdateManager):
    def __init__(self):
        self._git_path = self._find_working_git()
        self.github_org = self.get_github_org()
        self.github_repo = self.get_github_repo()

        self.branch = app.BRANCH = self._find_installed_branch()

        self._cur_commit_hash = None
        self._newest_commit_hash = None
        self._num_commits_behind = 0
        self._num_commits_ahead = 0
        self._cur_version = ''

    def get_cur_commit_hash(self):
        return self._cur_commit_hash

    def get_newest_commit_hash(self):
        return self._newest_commit_hash

    def get_cur_version(self):
        if self._cur_commit_hash or self._find_installed_version():
            self._cur_version = self._run_git(self._git_path, 'describe --tags --abbrev=0 {0}'.format(self._cur_commit_hash))[0]
        return self._cur_version

    def get_newest_version(self):
        if self._newest_commit_hash:
            self._cur_version = self._run_git(self._git_path, "describe --tags --abbrev=0 " + self._newest_commit_hash)[0]
        else:
            self._cur_version = self._run_git(self._git_path, "describe --tags --abbrev=0 " + self._cur_commit_hash)[0]
        return self._cur_version

    def get_num_commits_behind(self):
        return self._num_commits_behind

    def get_num_commits_ahead(self):
        return self._num_commits_ahead

    def _find_working_git(self):
        test_cmd = 'version'

        if app.GIT_PATH:
            main_git = '"' + app.GIT_PATH + '"'
        else:
            main_git = 'git'

        log.debug(u'Checking if we can use git commands: {0} {1}', main_git, test_cmd)
        _, _, exit_status = self._run_git(main_git, test_cmd)

        if exit_status == 0:
            log.debug(u'Using: {0}', main_git)
            return main_git
        else:
            log.debug(u'Not using: {0}', main_git)

        # trying alternatives

        alternative_git = []

        # osx people who start sr from launchd have a broken path, so try a hail-mary attempt for them
        if platform.system().lower() == 'darwin':
            alternative_git.append('/usr/local/git/bin/git')

        if platform.system().lower() == 'windows':
            if main_git != main_git.lower():
                alternative_git.append(main_git.lower())

        if alternative_git:
            log.debug(u'Trying known alternative git locations')

            for cur_git in alternative_git:
                log.debug(u'Checking if we can use git commands: {0} {1}', cur_git, test_cmd)
                _, _, exit_status = self._run_git(cur_git, test_cmd)

                if exit_status == 0:
                    log.debug(u'Using: {0}', cur_git)
                    return cur_git
                else:
                    log.debug(u'Not using: {0}', cur_git)

        # Still haven't found a working git
        # Warn user only if he has version check enabled
        if app.VERSION_NOTIFY:
            app.NEWEST_VERSION_STRING = ERROR_MESSAGE

        return None

    @staticmethod
    def _run_git(git_path, args):

        output = err = exit_status = None

        if not git_path:
            log.warning(u"No git specified, can't use git commands")
            app.NEWEST_VERSION_STRING = ERROR_MESSAGE
            exit_status = 1
            return output, err, exit_status

        # If we have a valid git remove the git warning
        # String will be updated as soon we check github
        app.NEWEST_VERSION_STRING = None

        cmd = git_path + ' ' + args

        try:
            log.debug(u'Executing {cmd} with your shell in {dir}', {'cmd': cmd, 'dir': app.PROG_DIR})
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 shell=True, cwd=app.PROG_DIR)
            output, err = p.communicate()
            exit_status = p.returncode

            if output:
                output = output.strip()

        except OSError:
            log.info(u"Command {cmd} didn't work", {'cmd': cmd})
            exit_status = 1

        if exit_status == 0:
            log.debug(u'{cmd} : returned successful', {'cmd': cmd})
            exit_status = 0

        elif exit_status == 1:
            if output:
                if 'stash' in output:
                    log.warning(u"Enable 'git reset' in settings or stash your changes in local files")
                else:
                    log.warning(u'{cmd} returned : {output}', {'cmd': cmd, 'output': output})
            else:
                log.warning(u'{cmd} returned no data', {'cmd': cmd})
            exit_status = 1

        elif exit_status == 128 or 'fatal:' in output or err:
            log.warning(u'{cmd} returned : {output}', {'cmd': cmd, 'output': output})
            exit_status = 128

        else:
            log.warning(u'{cmd} returned : {output}. Treat as error for now', {'cmd': cmd, 'output': output})
            exit_status = 1

        return output, err, exit_status

    def _find_installed_version(self):
        """Attempt to find the currently installed version of the application.

        Uses git show to get commit version.

        :return: True for success or False for failure
        """
        output, _, exit_status = self._run_git(self._git_path, 'rev-parse HEAD')  # @UnusedVariable

        if exit_status == 0 and output:
            cur_commit_hash = output.strip()
            if not re.match('^[a-z0-9]+$', cur_commit_hash):
                log.warning(u"Output doesn't look like a hash, not using it")
                return False
            self._cur_commit_hash = cur_commit_hash
            app.CUR_COMMIT_HASH = str(cur_commit_hash)
            return True
        else:
            return False

    def _find_installed_branch(self):
        branch_info, _, exit_status = self._run_git(self._git_path, 'symbolic-ref -q HEAD')  # @UnusedVariable
        if exit_status == 0 and branch_info:
            branch = branch_info.strip().replace('refs/heads/', '', 1)
            if branch:
                app.BRANCH = branch
                return branch
        return ""

    def _check_github_for_update(self):
        """
        Uses git commands to check if there is a newer version that the provided
        commit hash. If there is a newer version it sets _num_commits_behind.
        """

        self._num_commits_behind = 0
        self._num_commits_ahead = 0

        # update remote origin url
        self.update_remote_origin()

        # get all new info from github
        output, _, exit_status = self._run_git(self._git_path, 'fetch --prune %s' % app.GIT_REMOTE)
        if not exit_status == 0:
            log.warning(u"Unable to contact github, can't check for update")
            return

        # get latest commit_hash from remote
        output, _, exit_status = self._run_git(self._git_path, 'rev-parse --verify --quiet "@{upstream}"')

        if exit_status == 0 and output:
            cur_commit_hash = output.strip()

            if not re.match('^[a-z0-9]+$', cur_commit_hash):
                log.debug(u"Output doesn't look like a hash, not using it")
                return

            else:
                self._newest_commit_hash = cur_commit_hash
        else:
            log.debug(u"git didn't return newest commit hash")
            return

        # get number of commits behind and ahead (option --count not supported git < 1.7.2)
        output, _, exit_status = self._run_git(self._git_path, 'rev-list --left-right "@{upstream}"...HEAD')
        if exit_status == 0 and output:

            try:
                self._num_commits_behind = int(output.count("<"))
                self._num_commits_ahead = int(output.count(">"))

            except Exception:
                log.debug(u"git didn't return numbers for behind and ahead, not using it")
                return

        log.debug(u'cur_commit = {0}, newest_commit = {1}, num_commits_behind = {2}, num_commits_ahead = {3}',
                  self._cur_commit_hash, self._newest_commit_hash, self._num_commits_behind, self._num_commits_ahead)

    def set_newest_text(self):

        # if we're up to date then don't set this
        app.NEWEST_VERSION_STRING = None

        if self._num_commits_behind > 0 or self._is_hard_reset_allowed():

            base_url = 'http://github.com/' + self.github_org + '/' + self.github_repo
            if self._newest_commit_hash:
                url = base_url + '/compare/' + self._cur_commit_hash + '...' + self._newest_commit_hash
            else:
                url = base_url + '/commits/'

            newest_text = 'There is a <a href="' + url + '" onclick="window.open(this.href); return false;">newer version available</a> '
            newest_text += " (you're " + str(self._num_commits_behind) + " commit"
            if self._num_commits_behind > 1:
                newest_text += 's'
            newest_text += ' behind'
            if self._num_commits_ahead > 0:
                newest_text += ' and {ahead} commit{s} ahead'.format(ahead=self._num_commits_ahead,
                                                                     s='s' if self._num_commits_ahead > 1 else '')
            newest_text += ')' + "&mdash; <a href=\"" + self.get_update_url() + "\">Update Now</a>"

        elif self._num_commits_ahead > 0:
            newest_text = u'Local branch is ahead of {0}. Automatic update not possible'.format(self.branch)
            log.warning(newest_text)

        else:
            return

        app.NEWEST_VERSION_STRING = newest_text

    def need_update(self):

        if self.branch != self._find_installed_branch():
            log.debug(u'Branch checkout: {0}->{1}', self._find_installed_branch(), self.branch)
            return True

        self._find_installed_version()
        if not self._cur_commit_hash:
            return True
        else:
            try:
                self._check_github_for_update()
            except Exception as e:
                log.warning(u"Unable to contact github, can't check for update: {0!r}", e)
                return False

            if self._num_commits_behind > 0 or self._num_commits_ahead > 0:
                return True

        return False

    def can_update(self):
        """Return whether update can be executed.

        :return:
        :rtype: bool
        """
        return self._num_commits_ahead <= 0 or self._is_hard_reset_allowed()

    def update(self):
        """Call git pull origin <branch> in order to update the application.

        Returns a bool depending on the call's success.
        """
        # update remote origin url
        self.update_remote_origin()

        # remove untracked files and performs a hard reset on git branch to avoid update issues
        if self._is_hard_reset_allowed():
            self.reset()

        # Executing git clean before updating
        self.clean()

        if self.branch == self._find_installed_branch():
            _, _, exit_status = self._run_git(self._git_path, 'pull -f %s %s' % (app.GIT_REMOTE, self.branch))  # @UnusedVariable
        else:
            _, _, exit_status = self._run_git(self._git_path, 'checkout -f ' + self.branch)  # @UnusedVariable

        # Executing git clean after updating
        self.clean()

        if exit_status == 0:
            self._find_installed_version()
            # Notify update successful
            if app.NOTIFY_ON_UPDATE:
                try:
                    notifiers.notify_git_update(app.CUR_COMMIT_HASH or "")
                except Exception:
                    log.debug(u'Unable to send update notification. Continuing the update process')
            return True

        else:
            return False

    @staticmethod
    def _is_hard_reset_allowed():
        """Return whether git hard reset is allowed or not.

        :return:
        :rtype: bool
        """
        return app.GIT_RESET and (not app.GIT_RESET_BRANCHES or
                                  app.BRANCH in app.GIT_RESET_BRANCHES)

    def clean(self):
        """Call git clean to remove all untracked files.

        It only affects source folders and the lib folder,
        to prevent deleting untracked user data not known by .gitignore

        :return:
        :rtype: int
        """
        # Fixes: goo.gl/tr8Awf - to be removed in the next release
        root_dir = os.path.basename(app.PROG_DIR)
        helper_folder = os.path.join(root_dir, 'helper')
        helpers_folder = os.path.join(root_dir, 'helpers')

        folders = (app.LIB_FOLDER, app.EXT_FOLDER, app.SRC_FOLDER, app.STATIC_FOLDER,
                   helper_folder, helpers_folder) + app.LEGACY_SRC_FOLDERS
        _, _, exit_status = self._run_git(self._git_path, 'clean -d -f -x {0}'.format(' '.join(folders)))

        return exit_status

    def reset(self):
        """
        Calls git reset --hard to perform a hard reset. Returns a bool depending
        on the call's success.
        """
        _, _, exit_status = self._run_git(self._git_path, 'reset --hard {0}/{1}'.format
                                          (app.GIT_REMOTE, app.BRANCH))  # @UnusedVariable
        if exit_status == 0:
            return True

    def list_remote_branches(self):
        # update remote origin url
        self.update_remote_origin()
        app.BRANCH = self._find_installed_branch()

        branches, _, exit_status = self._run_git(self._git_path, 'ls-remote --heads %s' % app.GIT_REMOTE)  # @UnusedVariable
        if exit_status == 0 and branches:
            if branches:
                return re.findall(r'refs/heads/(.*)', branches)
        return []

    def update_remote_origin(self):
        self._run_git(self._git_path, 'config remote.%s.url %s' % (app.GIT_REMOTE, app.GIT_REMOTE_URL))
        self._run_git(self._git_path, 'config remote.%s.pushurl %s' % (app.GIT_REMOTE, app.GIT_REMOTE_URL))


class SourceUpdateManager(UpdateManager):
    def __init__(self):
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
        return app.CUR_COMMIT_BRANCH if app.CUR_COMMIT_BRANCH else "master"

    def get_cur_commit_hash(self):
        return self._cur_commit_hash

    def get_newest_commit_hash(self):
        return self._newest_commit_hash

    @staticmethod
    def get_cur_version():
        return ""

    @staticmethod
    def get_newest_version():
        return ""

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
                self._newest_commit_hash = ""
                self._num_commits_behind = 0
                self._num_commits_ahead = 0
                self._cur_commit_hash = ""

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

        # if we're up to date then don't set this
        app.NEWEST_VERSION_STRING = None

        if not self._cur_commit_hash:
            log.debug(u"Unknown current version number, don't know if we should update or not")

            newest_text = "Unknown current version number: If you've never used the application " \
                          "upgrade system before then current version is not set."
            newest_text += "&mdash; <a href=\"" + self.get_update_url() + "\">Update Now</a>"

        elif self._num_commits_behind > 0:
            base_url = 'http://github.com/' + self.github_org + '/' + self.github_repo
            if self._newest_commit_hash:
                url = base_url + '/compare/' + self._cur_commit_hash + '...' + self._newest_commit_hash
            else:
                url = base_url + '/commits/'

            newest_text = 'There is a <a href="' + url + '" onclick="window.open(this.href); return false;">newer version available</a>'
            newest_text += " (you're " + str(self._num_commits_behind) + " commit"
            if self._num_commits_behind > 1:
                newest_text += "s"
            newest_text += " behind)" + "&mdash; <a href=\"" + self.get_update_url() + "\">Update Now</a>"
        else:
            return

        app.NEWEST_VERSION_STRING = newest_text

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
            notifiers.notify_git_update(app.CUR_COMMIT_HASH or "")
        except Exception:
            log.debug(u'Unable to send update notification. Continuing the update process')
        return True

    @staticmethod
    def list_remote_branches():
        gh = get_github_repo(app.GIT_ORG, app.GIT_REPO)
        return [x.name for x in gh.get_branches() if x]
