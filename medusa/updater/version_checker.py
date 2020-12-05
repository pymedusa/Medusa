# coding=utf-8

from __future__ import unicode_literals

import datetime
import logging
import os
import re
import time
from builtins import object
from builtins import str
from logging import DEBUG, WARNING

from medusa import app, db, helpers, ui
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSafeSession
from medusa.updater.docker_updater import DockerUpdateManager
from medusa.updater.github_updater import GitUpdateManager
from medusa.updater.source_updater import SourceUpdateManager


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class CheckVersion(object):
    """Version check class meant to run as a thread object with the sr scheduler."""

    def __init__(self):
        self.amActive = False
        self.updater = self.find_install_type()
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
                        if self.update():
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
                log.info(u'Config backup successful')
                ui.notifications.message('Backup', 'Config backup successful')
                return True
            else:
                log.warning(u'Config backup failed')
                ui.notifications.message('Backup', 'Config backup failed')
                return False
        except Exception as e:
            log.error(u'Update: Config backup failed. Error: {0!r}', e)
            ui.notifications.message('Backup', 'Config backup failed')
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
                    'type': DEBUG,
                    'text': u'We can proceed with the update. New update has a new DB version'},
                'downgrade': {
                    'type': WARNING,
                    'text': u"We can't proceed with the update. New update has an old DB version. It's not possible to downgrade"},
            }
            try:
                result = self.getDBcompare()
                if result in message:
                    log.log(message[result]['type'], message[result]['text'])  # unpack the result message into a log entry
                else:
                    log.warning(u"We can't proceed with the update. Unable to check remote DB version. Error: {0}", result)
                return result in ['equal', 'upgrade']  # add future True results to the list
            except Exception as error:
                log.error(u"We can't proceed with the update. Unable to compare DB version. Error: {0!r}", error)
                return False

        def postprocessor_safe():
            if not app.post_processor_scheduler.action.amActive:
                log.debug(u'We can proceed with the update. Post-Processor is not running')
                return True
            else:
                log.debug(u"We can't proceed with the update. Post-Processor is running")
                return False

        def showupdate_safe():
            if app.show_update_scheduler.action.amActive:
                log.debug(u"We can't proceed with the update. Shows are being updated")
                return False

            if app.episode_update_scheduler.action.amActive:
                log.debug(u"We can't proceed with the update. Episodes are being updated")
                return False

            log.debug(u'We can proceed with the update. Shows or episodes are not being updated')
            return True

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
            cur_hash = str(self.updater.newest_commit_hash)
            assert len(cur_hash) == 40, 'Commit hash wrong length: {length} hash: {hash}'.format(
                length=len(cur_hash), hash=cur_hash)

            check_url = 'http://rawcdn.githack.com/{org}/{repo}/{commit}/medusa/databases/main_db.py'.format(
                org=app.GIT_ORG, repo=app.GIT_REPO, commit=cur_hash)
            response = self.session.get(check_url)

            # Get remote DB version
            match_max_db = re.search(r'MAX_DB_VERSION\s*=\s*(?P<version>\d{2,3})', response.text)
            new_branch_major_db_version = int(match_max_db.group('version')) if match_max_db else None

            # Check local DB version
            main_db_con = db.DBConnection()
            cur_branch_major_db_version, cur_branch_minor_db_version = main_db_con.checkDBVersion()

            if any([cur_branch_major_db_version is None, cur_branch_minor_db_version is None,
                    new_branch_major_db_version is None]):
                return 'Could not compare database versions, aborting'

            if new_branch_major_db_version > cur_branch_major_db_version:
                return 'upgrade'
            elif new_branch_major_db_version == cur_branch_major_db_version:
                return 'equal'
            else:
                return 'downgrade'
        except Exception as e:
            return repr(e)

    def find_install_type(self):
        """
        Determine how this copy of Medusa was installed.

        :return: type of installation. Possible values are:
            'docker': any docker build
            'git': running from source using git
            'source': running from source without git
        """
        if self.runs_in_docker():
            return DockerUpdateManager()
        elif os.path.isdir(os.path.join(app.PROG_DIR, u'.git')):
            return GitUpdateManager()

        return SourceUpdateManager()

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
            log.info(u'Checking for updates using {0}', self.updater)

        if not self.updater.need_update():
            app.NEWEST_VERSION_STRING = None

            if force:
                ui.notifications.message('No update needed')
                log.info(u'No update needed')

            # no updates needed
            return False

        # found updates
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
            log.debug(u'Could not load news from URL: {0}', app.NEWS_URL)
            return

        try:
            last_read = datetime.datetime.strptime(app.NEWS_LAST_READ, '%Y-%m-%d')
        except ValueError:
            log.warning(u'Invalid news last read date: {0}', app.NEWS_LAST_READ)
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
                log.warning(u'Unable to match latest news date. Repository news date: {0}', match.group(1))
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
            if self.updater.need_update() and self.updater.can_update():
                return self.updater.update()

        return False

    def list_remote_branches(self):
        if self.updater:
            app.GIT_REMOTE_BRANCHES = self.updater.list_remote_branches()
        return app.GIT_REMOTE_BRANCHES

    def get_branch(self):
        if self.updater:
            return self.updater.branch

    @staticmethod
    def runs_in_docker():
        """
        Check if Medusa is run in a docker container.

        If run in a container, we don't want to use the auto update feature, but just want to inform the user
        there is an update available. The user can update through getting the latest docker tag.
        """
        if app.RUNS_IN_DOCKER is not None:
            return app.RUNS_IN_DOCKER

        path = '/proc/{pid}/cgroup'.format(pid=os.getpid())
        try:
            if not os.path.isfile(path):
                return False

            with open(path) as f:
                for line in f:
                    if re.match(r'\d+:[\w=]+:/docker(-[ce]e)?/\w+', line):
                        log.debug(u'Running in a docker container')
                        app.RUNS_IN_DOCKER = True
                        return True
                return False
        except (EnvironmentError, OSError) as error:
            log.info(u'Tried to check the path {path} if we are running in a docker container, '
                     u'but an error occurred: {error}', {'path': path, 'error': error})
            return False
