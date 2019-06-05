"""Check Medusa app version before release"""
from __future__ import print_function, unicode_literals

import io
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
else:
    TRAVIS_PULL_REQUEST = '1234'
    TRAVIS_PR_TARGET_BRANCH = 'master'
    TRAVIS_PR_SOURCE_BRANCH = 'develop'  # or 'release/release-0.2.3'
    TRAVIS_BUILD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

TRAVIS_PR_TARGET_BRANCH = TRAVIS_PR_TARGET_BRANCH.lower()
TRAVIS_PR_SOURCE_BRANCH = TRAVIS_PR_SOURCE_BRANCH.lower()


class Version(object):
    def __init__(self, version_string):
        self.version = tuple()
        if version_string.startswith('v'):
            version_string = version_string[1:]
        self.version = tuple(map(int, version_string.split('.')))

    def __eq__(self, other):
        return self.version == other.version

    def __ne__(self, other):
        return self.version != other.version

    def __lt__(self, other):
        return self.version < other.version

    def __le__(self, other):
        return self.version <= other.version

    def __gt__(self, other):
        return self.version > other.version

    def __ge__(self, other):
        return self.version >= other.version

    def __str__(self):
        return str('.'.join(map(str, self.version)))

    def __repr__(self):
        return repr(self.version)


def search_file_for_version():
    """Get the app version from the code."""
    version_file = VERSION_FILE.split('/')
    filename = os.path.abspath(os.path.join(TRAVIS_BUILD_DIR, *version_file))
    with io.open(filename, 'r', encoding='utf-8') as fh:
        for line in fh:
            match = VERSION_LINE_REGEXP.match(line)
            if match:
                return Version(match.group(1))

    raise ValueError('Failed to get the app version!')


# Are we merging either develop or a release branch into master in a pull request?
if all((
        TRAVIS_PULL_REQUEST != 'false',
        TRAVIS_PR_TARGET_BRANCH == 'master',
        TRAVIS_PR_SOURCE_BRANCH == 'develop' or TRAVIS_PR_SOURCE_BRANCH.startswith('release/')
)):
    # Get lastest git tag on master branch
    proc = subprocess.call(['git', 'fetch', 'origin', 'master:master'])
    if proc > 0:
        print('Failed to fetch')

    proc = subprocess.Popen(['git', 'describe', '--tags', '--abbrev=0', 'master'], stdout=subprocess.PIPE, universal_newlines=True)
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
