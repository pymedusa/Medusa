"""Check Medusa app version before release"""
from __future__ import print_function, unicode_literals

import os
import re
import subprocess
import sys

VERSION_FILE = 'medusa/common.py'
VERSION_LINE_REGEXP = re.compile(r"VERSION = '([0-9.]+)'")
TRAVIS = os.environ.get('TRAVIS', False)

if TRAVIS:
    TRAVIS_PULL_REQUEST = os.environ['TRAVIS_PULL_REQUEST']  # 'false' if not a PR, otherwise - the PR number
    TRAVIS_PR_TARGET_BRANCH = os.environ['TRAVIS_BRANCH']
    TRAVIS_PR_SOURCE_BRANCH = os.environ['TRAVIS_PULL_REQUEST_BRANCH']
    TRAVIS_BUILD_DIR = os.environ['TRAVIS_BUILD_DIR']
    TRAVIS_COMMIT_MESSAGE = os.environ['TRAVIS_COMMIT_MESSAGE']
else:
    TRAVIS_PULL_REQUEST = '1234'
    TRAVIS_PR_TARGET_BRANCH = 'master'
    TRAVIS_PR_SOURCE_BRANCH = 'develop'  # or 'release/release-0.2.3'
    TRAVIS_BUILD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    TRAVIS_COMMIT_MESSAGE = 'whatever'  # or have [disable-version-check] to disable this check

TRAVIS_PR_TARGET_BRANCH = TRAVIS_PR_TARGET_BRANCH.lower()
TRAVIS_PR_SOURCE_BRANCH = TRAVIS_PR_SOURCE_BRANCH.lower()


class Version(object):
    def __init__(self, version_string):
        self.version = tuple()
        if version_string.startswith('v'):
            version_string = version_string[1:]
        self.version = tuple(map(int, version_string.split('.')))

    def __cmp__(self, other):
        if self.version == other.version:
            return 0
        if self.version > other.version:
            return 1
        if self.version < other.version:
            return -1

    def __str__(self):
        return str('.'.join(map(str, self.version)))

    def __repr__(self):
        return repr(self.version)


def search_file_for_version():
    version_file = VERSION_FILE.split('/')
    filename = os.path.abspath(os.path.join(TRAVIS_BUILD_DIR, *version_file))
    with open(filename, 'r') as fh:
        data = fh.readlines()

    for line in data:
        match = VERSION_LINE_REGEXP.findall(line)
        if match:
            return Version(match[0])


if '[disable-version-check]' in TRAVIS_COMMIT_MESSAGE:
    print('Skipping version check due to commit message.')
# Are we merging either develop or a release branch into master in a pull request?
elif all((
        TRAVIS_PULL_REQUEST != 'false',
        TRAVIS_PR_TARGET_BRANCH == 'master',
        TRAVIS_PR_SOURCE_BRANCH == 'develop' or TRAVIS_PR_SOURCE_BRANCH.startswith('release/')
        )):
    # Get lastest git tag on master branch
    proc = subprocess.call(['git', 'fetch', 'origin', 'master:master'])
    if proc > 0:
        print('Failed to fetch')

    proc = subprocess.Popen(['git', 'describe', '--tags', '--abbrev=0', 'master'], stdout=subprocess.PIPE)
    (output, err) = proc.communicate()
    latest_tag = output.strip()
    if err or not latest_tag:
        print('Error while getting latest tag commit hash')
        sys.exit(1)

    git_version = Version(latest_tag)
    file_version = search_file_for_version()
    print('GIT Version: {}'.format(git_version))
    print('APP Version: {}'.format(file_version))
    version_compare = file_version > git_version
    if not version_compare:
        print('Please update app version in {file}'.format(file=VERSION_FILE))
        sys.exit(1)

# If we got here, then everything is correct!
sys.exit(0)
