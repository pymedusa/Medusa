# coding=utf-8

from __future__ import unicode_literals

import logging
import os
import platform
import re
import subprocess
import sys

from medusa import app, notifiers
from medusa.logger.adapters.style import BraceAdapter
from medusa.updater.update_manager import UpdateManager

from six import text_type


ERROR_MESSAGE = ('Unable to find your git executable. Set git executable path in Advanced Settings '
                 'OR shutdown application and delete your .git folder and run from source to enable updates.')

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class GitUpdateManager(UpdateManager):
    def __init__(self):
        super(GitUpdateManager, self).__init__()
        self._git_path = self._find_working_git()
        self.github_org = self.get_github_org()
        self.github_repo = self.get_github_repo()
        self.branch = self._find_installed_branch()

        self._cur_commit_hash = None
        self._newest_commit_hash = None
        self._num_commits_behind = 0
        self._num_commits_ahead = 0

    def __str__(self):
        return 'GitHub Updater'

    @property
    def current_commit_hash(self):
        return self._cur_commit_hash

    @property
    def newest_commit_hash(self):
        return self._newest_commit_hash

    @property
    def current_version(self):
        self.update_commit_hash()
        cur_version = self._run_git(self._git_path, 'describe --tags --abbrev=0 {0}'.format(
            self._cur_commit_hash))[0]
        if cur_version:
            return cur_version.lstrip('v')

    @property
    def newest_version(self):
        self.update_newest_commit_hash()
        new_version = self._run_git(self._git_path, 'describe --tags --abbrev=0 {0}'.format(
            self._newest_commit_hash))[0]
        if new_version:
            return new_version.lstrip('v')

    @property
    def commits_behind(self):
        return self._num_commits_behind

    @property
    def commits_ahead(self):
        return self._num_commits_ahead

    def _find_working_git(self):
        test_cmd = 'version'
        main_git = app.GIT_PATH or 'git'

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

    def _run_git(self, git_path, args):
        output = err = exit_status = None

        if not git_path:
            git_path = self._find_working_git()
            if git_path:
                self._git_path = git_path
            else:
                # Warn user only if he has version check enabled
                if app.VERSION_NOTIFY:
                    log.warning(u"No git specified, can't use git commands")
                    app.NEWEST_VERSION_STRING = ERROR_MESSAGE
                exit_status = 1
                return output, err, exit_status

        if git_path != 'git' and not os.path.isfile(git_path):
            log.warning(u"Invalid git specified, can't use git commands")
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

            # Convert bytes to string in python3
            if isinstance(output, (bytes, bytearray)):
                output = output.decode('utf-8')

            if output:
                output = output.strip()

        except OSError:
            log.info(u"Command {cmd} didn't work", {'cmd': cmd})
            exit_status = 1

        if exit_status == 0:
            log.debug(u'{cmd} : returned successful', {'cmd': cmd})

        elif exit_status == 1:
            if output:
                if 'stash' in output:
                    log.warning(u"Enable 'git reset' in settings or stash your changes in local files")
                else:
                    log.warning(u'{cmd} returned : {output}', {'cmd': cmd, 'output': output})
            else:
                log.warning(u'{cmd} returned no data', {'cmd': cmd})

        elif exit_status == 128:
            log.warning('{cmd} returned ({status}) : {output}',
                        {'cmd': cmd, 'status': exit_status, 'output': output})

        elif exit_status == 129:
            if 'unknown option' in output and 'set-upstream-to' in output:
                log.info("Can't set upstream to origin/{0} because you're running an old version of git."
                         '\nPlease upgrade your git installation to its latest version.', app.BRANCH)
            else:
                log.warning('{cmd} returned ({status}) : {output}',
                            {'cmd': cmd, 'status': exit_status, 'output': output})

        else:
            log.warning(u'{cmd} returned : {output}. Treat as error for now', {'cmd': cmd, 'output': output})
            exit_status = 1

        return output, err, exit_status

    def update_commit_hash(self):
        """Attempt to set the hash of the currently installed version of the application.

        Uses git to get commit version.
        """
        output, _, exit_status = self._run_git(self._git_path, 'rev-parse HEAD')

        if exit_status == 0 and output:
            cur_commit_hash = output.strip()
            if not re.match('^[a-z0-9]+$', cur_commit_hash):
                log.warning(u"Output doesn't look like a hash, not using it")
                return False

            self._cur_commit_hash = cur_commit_hash
            app.CUR_COMMIT_HASH = cur_commit_hash
            return True

        return False

    def update_newest_commit_hash(self):
        # update remote origin url
        self.update_remote_origin()

        # Configure local branch with upstream
        self.set_upstream_branch()

        # get all new info from github
        output, _, exit_status = self._run_git(self._git_path, 'fetch --prune {0}'.format(app.GIT_REMOTE))
        if not exit_status == 0:
            log.warning(u"Unable to contact github, can't check for update")
            return False

        # get latest commit_hash from remote
        output, _, exit_status = self._run_git(self._git_path, 'rev-parse --verify --quiet "@{upstream}"')

        if exit_status == 0 and output:
            cur_commit_hash = output.strip()
            if not re.match('^[a-z0-9]+$', cur_commit_hash):
                log.debug(u"Output doesn't look like a hash, not using it")
                return False
            else:
                self._newest_commit_hash = cur_commit_hash
                return True
        else:
            log.debug(u"git didn't return newest commit hash")
            return False

    def _find_installed_branch(self):
        branch_info, _, exit_status = self._run_git(self._git_path, 'symbolic-ref -q HEAD')
        if exit_status == 0 and branch_info:
            branch = branch_info.strip().replace('refs/heads/', '', 1)
            if branch:
                app.BRANCH = branch
                return branch
        return ''

    def check_for_update(self):
        """Use git commands to check if there is a newer version that the provided commit hash."""
        self.update_commit_hash()
        self.update_newest_commit_hash()

        # get number of commits behind and ahead (option --count not supported git < 1.7.2)
        output, _, exit_status = self._run_git(self._git_path, 'rev-list --left-right "@{upstream}"...HEAD')
        if exit_status == 0 and output:
            try:
                self._num_commits_behind = int(output.count('<'))
                self._num_commits_ahead = int(output.count('>'))
            except Exception:
                log.debug(u"git didn't return numbers for behind and ahead, not using it")
                return False

        log.debug(u'cur_commit = {0}, newest_commit = {1}, num_commits_behind = {2}, num_commits_ahead = {3}',
                  self._cur_commit_hash, self._newest_commit_hash, self._num_commits_behind, self._num_commits_ahead)

    def need_update(self):
        if self.branch != self._find_installed_branch():
            log.debug(u'Branch checkout: {0}->{1}', self._find_installed_branch(), self.branch)
            return True

        try:
            self.check_for_update()
        except Exception as e:
            log.warning(u"Unable to contact github, can't check for update: {0!r}", e)
            return False

        if self._num_commits_behind > 0 or self._num_commits_ahead > 0:
            self._set_update_text()
            return True

        return False

    def _set_update_text(self):
        if self._num_commits_behind > 0 or self._is_hard_reset_allowed():
            base_url = 'http://github.com/' + self.github_org + '/' + self.github_repo
            if self._newest_commit_hash:
                url = base_url + '/compare/' + self._cur_commit_hash + '...' + self._newest_commit_hash
            else:
                url = base_url + '/commits/'

            newest_text = 'There is a <a href="' + url + '" onclick="window.open(this.href); return false;">newer version available</a> '
            newest_text += " (you're " + text_type(self._num_commits_behind) + ' commit'
            if self._num_commits_behind > 1:
                newest_text += 's'
            newest_text += ' behind'
            if self._num_commits_ahead > 0:
                newest_text += ' and {ahead} commit{s} ahead'.format(ahead=self._num_commits_ahead,
                                                                     s='s' if self._num_commits_ahead > 1 else '')
            newest_text += ') &mdash; <a href="' + self.get_update_url() + '">Update Now</a>'

        elif self._num_commits_ahead > 0:
            newest_text = u'Local branch is ahead of {0}. Automatic update not possible'.format(self.branch)
            log.warning(newest_text)
        else:
            return

        app.NEWEST_VERSION_STRING = newest_text

    def can_update(self):
        """Return whether update can be executed.

        :return:
        :rtype: bool
        """
        # Version 0.4.6 is the last version which will run on python 2.7.13.
        if sys.version_info.major == 2:
            return False

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

        current_branch = self._find_installed_branch()
        if self.branch == current_branch:
            _, _, exit_status = self._run_git(self._git_path, 'pull -f {0} {1}'.format(app.GIT_REMOTE, self.branch))
        else:
            log.warning(
                u"Couldn't determine current branch or current branch {current}"
                u" doesn't match desired branch {desired}.\n"
                u'Checkout the desired branch or try again later.', {
                    'current': current_branch,
                    'desired': self.branch
                })
            return False

        # Executing git clean after updating
        self.clean()

        if exit_status == 0:
            self.update_commit_hash()
            # Notify update successful
            if app.NOTIFY_ON_UPDATE:
                try:
                    notifiers.notify_git_update(app.CUR_COMMIT_HASH or '')
                except Exception:
                    log.debug(u'Unable to send update notification. Continuing the update process')
            return True

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

        It only affects source folders and libX and extX folders,
        to prevent deleting untracked user data not known by .gitignore

        :return:
        :rtype: int
        """
        folders = (app.LIB_FOLDER, app.LIB2_FOLDER, app.LIB3_FOLDER, app.EXT_FOLDER,
                   app.EXT2_FOLDER, app.EXT3_FOLDER, app.SRC_FOLDER, app.STATIC_FOLDER) + app.LEGACY_SRC_FOLDERS
        _, _, exit_status = self._run_git(self._git_path, 'clean -d -f -x {0}'.format(' '.join(folders)))

        return exit_status

    def reset(self):
        """Call git reset --hard to perform a hard reset."""
        _, _, exit_status = self._run_git(self._git_path, 'reset --hard {0}/{1}'.format(app.GIT_REMOTE, app.BRANCH))
        if exit_status == 0:
            return True

    def list_remote_branches(self):
        # update remote origin url
        self.update_remote_origin()
        app.BRANCH = self._find_installed_branch()

        branches, _, exit_status = self._run_git(self._git_path, 'ls-remote --heads {0}'.format(app.GIT_REMOTE))
        if exit_status == 0 and branches:
            return re.findall(r'refs/heads/(.*)', branches)
        return []

    def update_remote_origin(self):
        self._run_git(self._git_path, 'config remote.{0}.url {1}'.format(app.GIT_REMOTE, app.GIT_REMOTE_URL))
        self._run_git(self._git_path, 'config remote.{0}.pushurl {1}'.format(app.GIT_REMOTE, app.GIT_REMOTE_URL))

    def set_upstream_branch(self):
        self._run_git(self._git_path, 'branch {0} --set-upstream-to origin/{1}'.format(app.BRANCH, app.BRANCH))
