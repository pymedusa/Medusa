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

import datetime
import os
import platform
import re
import shutil
import stat
import subprocess
import tarfile
import time
import traceback

from . import app, db, helpers, logger, notifiers, ui
from .github_client import get_github_repo
from .helper.exceptions import ex


class CheckVersion(object):
    """
    Version check class meant to run as a thread object with the sr scheduler.
    """

    def __init__(self):
        self.updater = None
        self.install_type = None
        self.amActive = False
        self.install_type = self.find_install_type()
        if self.install_type == 'git':
            self.updater = GitUpdateManager()
        elif self.install_type == 'source':
            self.updater = SourceUpdateManager()

        self.session = helpers.make_session()

    def run(self, force=False):

        self.amActive = True

        # Update remote branches and store in app.GIT_REMOTE_BRANCHES
        self.list_remote_branches()

        if self.updater:
            # set current branch version
            app.BRANCH = self.get_branch()

            if self.check_for_new_version(force):
                if app.AUTO_UPDATE:
                    logger.log(u'New update found, starting auto-updater ...')
                    ui.notifications.message('New update found, starting auto-updater')
                    if self.run_backup_if_safe():
                        if app.versionCheckScheduler.action.update():
                            logger.log(u'Update was successful!')
                            ui.notifications.message('Update was successful')
                            app.events.put(app.events.SystemEvent.RESTART)
                        else:
                            logger.log(u'Update failed!')
                            ui.notifications.message('Update failed!')

            self.check_for_new_news(force)

        self.amActive = False

    def run_backup_if_safe(self):
        return self.safe_to_update() is True and self._runbackup() is True

    def _runbackup(self):
        # Do a system backup before update
        logger.log(u'Config backup in progress...')
        ui.notifications.message('Backup', 'Config backup in progress...')
        try:
            backupDir = os.path.join(app.DATA_DIR, app.BACKUP_DIR)
            if not os.path.isdir(backupDir):
                os.mkdir(backupDir)

            if self._keeplatestbackup(backupDir) and self._backup(backupDir):
                logger.log(u'Config backup successful, updating...')
                ui.notifications.message('Backup', 'Config backup successful, updating...')
                return True
            else:
                logger.log(u'Config backup failed, aborting update', logger.WARNING)
                ui.notifications.message('Backup', 'Config backup failed, aborting update')
                return False
        except Exception as e:
            logger.log(u'Update: Config backup failed. Error: %s' % ex(e), logger.ERROR)
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
                    'type': logger.DEBUG,
                    'text': u'We can proceed with the update. New update has same DB version'},
                'upgrade': {
                    'type': logger.WARNING,
                    'text': u"We can't proceed with the update. New update has a new DB version. Please manually update"},
                'downgrade': {
                    'type': logger.WARNING,
                    'text': u"We can't proceed with the update. New update has a old DB version. It's not possible to downgrade"},
            }
            try:
                result = self.getDBcompare()
                if result in message:
                    logger.log(message[result]['text'], message[result]['type'])  # unpack the result message into a log entry
                else:
                    logger.log(u"We can't proceed with the update. Unable to check remote DB version. Error: %s" % result, logger.WARNING)
                return result in ['equal']  # add future True results to the list
            except Exception as error:
                logger.log(u"We can't proceed with the update. Unable to compare DB version. Error: %s" % repr(error), logger.ERROR)
                return False

        def postprocessor_safe():
            if not app.autoPostProcessorScheduler.action.amActive:
                logger.log(u'We can proceed with the update. Post-Processor is not running', logger.DEBUG)
                return True
            else:
                logger.log(u"We can't proceed with the update. Post-Processor is running", logger.DEBUG)
                return False

        def showupdate_safe():
            if not app.showUpdateScheduler.action.amActive:
                logger.log(u'We can proceed with the update. Shows are not being updated', logger.DEBUG)
                return True
            else:
                logger.log(u"We can't proceed with the update. Shows are being updated", logger.DEBUG)
                return False

        db_safe = db_safe(self)
        postprocessor_safe = postprocessor_safe()
        showupdate_safe = showupdate_safe()

        if db_safe and postprocessor_safe and showupdate_safe:
            logger.log(u'Proceeding with auto update', logger.DEBUG)
            return True
        else:
            logger.log(u'Auto update aborted', logger.DEBUG)
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
            response = helpers.get_url(check_url, session=self.session, returns='response')

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

        returns: type of installation. Possible values are:
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
        Checks the internet for a newer version.

        returns: bool, True for new version or False for no new version.

        force: if true the VERSION_NOTIFY setting will be ignored and a check will be forced
        """

        if not self.updater or (not app.VERSION_NOTIFY and not app.AUTO_UPDATE and not force):
            logger.log(u'Version checking is disabled, not checking for the newest version')
            return False

        # checking for updates
        if not app.AUTO_UPDATE:
            logger.log(u'Checking for updates using {0}'.format(self.install_type.upper()))

        if not self.updater.need_update():
            app.NEWEST_VERSION_STRING = None

            if force:
                ui.notifications.message('No update needed')
                logger.log(u'No update needed')

            # no updates needed
            return False

        # found updates
        self.updater.set_newest_text()
        return self.updater.can_update()

    def check_for_new_news(self, force=False):
        """
        Checks GitHub for the latest news.

        returns: unicode, a copy of the news

        force: ignored
        """

        # Grab a copy of the news
        logger.log(u'check_for_new_news: Checking GitHub for latest news.', logger.DEBUG)
        try:
            news = helpers.get_url(app.NEWS_URL, session=self.session, returns='text')
        except Exception:
            logger.log(u'check_for_new_news: Could not load news from repo.', logger.WARNING)
            news = ''

        if not news:
            return ''

        try:
            last_read = datetime.datetime.strptime(app.NEWS_LAST_READ, '%Y-%m-%d')
        except Exception:
            last_read = 0

        app.NEWS_UNREAD = 0
        gotLatest = False
        for match in re.finditer(r'^####\s*(\d{4}-\d{2}-\d{2})\s*####', news, re.M):
            if not gotLatest:
                gotLatest = True
                app.NEWS_LATEST = match.group(1)

            try:
                if datetime.datetime.strptime(match.group(1), '%Y-%m-%d') > last_read:
                    app.NEWS_UNREAD += 1
            except Exception:
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

    @staticmethod
    def _git_error():
        error_message = ('Unable to find your git executable - Shutdown the application and EITHER set git_path '
                         'in your config.ini OR delete your .git folder and run from source to enable updates.')
        app.NEWEST_VERSION_STRING = error_message

    def _find_working_git(self):
        test_cmd = 'version'

        if app.GIT_PATH:
            main_git = '"' + app.GIT_PATH + '"'
        else:
            main_git = 'git'

        logger.log(u'Checking if we can use git commands: {0} {1}'.format(main_git, test_cmd), logger.DEBUG)
        _, _, exit_status = self._run_git(main_git, test_cmd)

        if exit_status == 0:
            logger.log(u'Using: {0}'.format(main_git), logger.DEBUG)
            return main_git
        else:
            logger.log(u'Not using: {0}'.format(main_git), logger.DEBUG)

        # trying alternatives

        alternative_git = []

        # osx people who start sr from launchd have a broken path, so try a hail-mary attempt for them
        if platform.system().lower() == 'darwin':
            alternative_git.append('/usr/local/git/bin/git')

        if platform.system().lower() == 'windows':
            if main_git != main_git.lower():
                alternative_git.append(main_git.lower())

        if alternative_git:
            logger.log(u'Trying known alternative git locations', logger.DEBUG)

            for cur_git in alternative_git:
                logger.log(u'Checking if we can use git commands: {0} {1}'.format(cur_git, test_cmd), logger.DEBUG)
                _, _, exit_status = self._run_git(cur_git, test_cmd)

                if exit_status == 0:
                    logger.log(u'Using: {0}'.format(cur_git), logger.DEBUG)
                    return cur_git
                else:
                    logger.log(u'Not using: {0}'.format(cur_git), logger.DEBUG)

        # Still haven't found a working git
        error_message = ('Unable to find your git executable - Shutdown the application and EITHER set git_path '
                         'in your config.ini OR delete your .git folder and run from source to enable updates.')
        app.NEWEST_VERSION_STRING = error_message

        return None

    @staticmethod
    def _run_git(git_path, args):

        output = err = exit_status = None

        if not git_path:
            logger.log(u"No git specified, can't use git commands", logger.WARNING)
            exit_status = 1
            return output, err, exit_status

        cmd = git_path + ' ' + args

        try:
            logger.log(u'Executing {cmd} with your shell in {dir}'.format(cmd=cmd, dir=app.PROG_DIR), logger.DEBUG)
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 shell=True, cwd=app.PROG_DIR)
            output, err = p.communicate()
            exit_status = p.returncode

            if output:
                output = output.strip()

        except OSError:
            logger.log(u"Command {cmd} didn't work".format(cmd=cmd))
            exit_status = 1

        if exit_status == 0:
            logger.log(u'{cmd} : returned successful'.format(cmd=cmd), logger.DEBUG)
            exit_status = 0

        elif exit_status == 1:
            if output:
                if 'stash' in output:
                    logger.log(u"Enable 'git reset' in settings or stash your changes in local files", logger.WARNING)
                else:
                    logger.log(u'{cmd} returned : {output}'.format(cmd=cmd, output=output), logger.WARNING)
            else:
                    logger.log(u'{cmd} returned no data', logger.WARNING)
            exit_status = 1

        elif exit_status == 128 or 'fatal:' in output or err:
            logger.log(u'{cmd} returned : {output}'.format(cmd=cmd, output=output), logger.WARNING)
            exit_status = 128

        else:
            logger.log(u'{cmd} returned : {output}. Treat as error for now'.format
                       (cmd=cmd, output=output), logger.WARNING)
            exit_status = 1

        return output, err, exit_status

    def _find_installed_version(self):
        """Attempt to find the currently installed version of the application.

        Uses git show to get commit version.

        Returns: True for success or False for failure
        """

        output, _, exit_status = self._run_git(self._git_path, 'rev-parse HEAD')  # @UnusedVariable

        if exit_status == 0 and output:
            cur_commit_hash = output.strip()
            if not re.match('^[a-z0-9]+$', cur_commit_hash):
                logger.log(u"Output doesn't look like a hash, not using it", logger.WARNING)
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
        output, _, exit_status = self._run_git(self._git_path, 'fetch %s' % app.GIT_REMOTE)
        if not exit_status == 0:
            logger.log(u"Unable to contact github, can't check for update", logger.WARNING)
            return

        # get latest commit_hash from remote
        output, _, exit_status = self._run_git(self._git_path, 'rev-parse --verify --quiet "@{upstream}"')

        if exit_status == 0 and output:
            cur_commit_hash = output.strip()

            if not re.match('^[a-z0-9]+$', cur_commit_hash):
                logger.log(u"Output doesn't look like a hash, not using it", logger.DEBUG)
                return

            else:
                self._newest_commit_hash = cur_commit_hash
        else:
            logger.log(u"git didn't return newest commit hash", logger.DEBUG)
            return

        # get number of commits behind and ahead (option --count not supported git < 1.7.2)
        output, _, exit_status = self._run_git(self._git_path, 'rev-list --left-right "@{upstream}"...HEAD')
        if exit_status == 0 and output:

            try:
                self._num_commits_behind = int(output.count("<"))
                self._num_commits_ahead = int(output.count(">"))

            except Exception:
                logger.log(u"git didn't return numbers for behind and ahead, not using it", logger.DEBUG)
                return

        logger.log(u'cur_commit = %s, newest_commit = %s, num_commits_behind = %s, num_commits_ahead = %s' %
                   (self._cur_commit_hash, self._newest_commit_hash, self._num_commits_behind, self._num_commits_ahead), logger.DEBUG)

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
            logger.log(newest_text, logger.WARNING)

        else:
            return

        app.NEWEST_VERSION_STRING = newest_text

    def need_update(self):

        if self.branch != self._find_installed_branch():
            logger.log(u'Branch checkout: {0}->{1}'.format(self._find_installed_branch(), self.branch), logger.DEBUG)
            return True

        self._find_installed_version()
        if not self._cur_commit_hash:
            return True
        else:
            try:
                self._check_github_for_update()
            except Exception as e:
                logger.log(u"Unable to contact github, can't check for update: {0}".format(repr(e)), logger.WARNING)
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
                    logger.log(u'Unable to send update notification. Continuing the update process', logger.DEBUG)
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
        folders = (app.LIB_FOLDER, app.SRC_FOLDER, app.STATIC_FOLDER) + app.LEGACY_SRC_FOLDERS
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
        if app.GIT_USERNAME:
            if app.DEVELOPER:
                self._run_git(self._git_path, 'config remote.%s.pushurl %s' % (app.GIT_REMOTE, app.GIT_REMOTE_URL))
            else:
                self._run_git(self._git_path, 'config remote.%s.pushurl %s' % (app.GIT_REMOTE, app.GIT_REMOTE_URL.replace(app.GIT_ORG, app.GIT_USERNAME, 1)))


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

        self.session = helpers.make_session()

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
        except Exception as e:
            logger.log(u"Unable to contact github, can't check for update: {0}".format(repr(e)), logger.WARNING)
            return False

        if self.branch != self._find_installed_branch():
            logger.log(u'Branch checkout: {0}->{1}'.format(self._find_installed_branch(), self.branch), logger.DEBUG)
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

        logger.log(u'cur_commit = {0}, newest_commit = {1}, num_commits_behind = {2}'.format
                   (self._cur_commit_hash, self._newest_commit_hash, self._num_commits_behind), logger.DEBUG)

    def set_newest_text(self):

        # if we're up to date then don't set this
        app.NEWEST_VERSION_STRING = None

        if not self._cur_commit_hash:
            logger.log(u"Unknown current version number, don't know if we should update or not", logger.DEBUG)

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
                logger.log(u'Clearing out update folder {0} before extracting'.format(app_update_dir))
                shutil.rmtree(app_update_dir)

            logger.log(u'Clearing update folder {0} before extracting'.format(app_update_dir))
            os.makedirs(app_update_dir)

            # retrieve file
            logger.log(u'Downloading update from {0}'.format(repr(tar_download_url)))
            tar_download_path = os.path.join(app_update_dir, u'sr-update.tar')
            helpers.download_file(tar_download_url, tar_download_path, session=self.session)

            if not os.path.isfile(tar_download_path):
                logger.log(u"Unable to retrieve new version from {0}, can't update".format
                           (tar_download_url), logger.WARNING)
                return False

            if not tarfile.is_tarfile(tar_download_path):
                logger.log(u"Retrieved version from {0} is corrupt, can't update".format(tar_download_url), logger.WARNING)
                return False

            # extract to sr-update dir
            logger.log(u'Extracting file {0}'.format(tar_download_path))
            tar = tarfile.open(tar_download_path)
            tar.extractall(app_update_dir)
            tar.close()

            # delete .tar.gz
            logger.log(u'Deleting file {0}'.format(tar_download_path))
            os.remove(tar_download_path)

            # find update dir name
            update_dir_contents = [x for x in os.listdir(app_update_dir) if
                                   os.path.isdir(os.path.join(app_update_dir, x))]
            if len(update_dir_contents) != 1:
                logger.log(u'Invalid update data, update failed: {0}'.format(update_dir_contents), logger.WARNING)
                return False
            content_dir = os.path.join(app_update_dir, update_dir_contents[0])

            # walk temp folder and move files to main folder
            logger.log(u'Moving files from {0} to {1}'.format(content_dir, app.PROG_DIR))
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
                            logger.log(u'Special handling for {0}'.format(curfile), logger.DEBUG)
                            os.chmod(new_path, stat.S_IWRITE)
                            os.remove(new_path)
                            os.renames(old_path, new_path)
                        except Exception as e:
                            logger.log(u'Unable to update {0}: {1}'.format(new_path, ex(e)), logger.DEBUG)
                            os.remove(old_path)  # Trash the updated file without moving in new path
                        continue

                    if os.path.isfile(new_path):
                        os.remove(new_path)
                    os.renames(old_path, new_path)

            app.CUR_COMMIT_HASH = self._newest_commit_hash
            app.CUR_COMMIT_BRANCH = self.branch

        except Exception as e:
            logger.log(u'Traceback: {0}'.format(traceback.format_exc()), logger.DEBUG)
            logger.log(u'Error while trying to update: {0}'.format(ex(e)), logger.ERROR)
            return False

        # Notify update successful
        try:
            notifiers.notify_git_update(app.CUR_COMMIT_HASH or "")
        except Exception:
            logger.log(u'Unable to send update notification. Continuing the update process', logger.DEBUG)
        return True

    @staticmethod
    def list_remote_branches():
        gh = get_github_repo(app.GIT_ORG, app.GIT_REPO)
        return [x.name for x in gh.get_branches() if x]
