import sys
import tempfile
import os
import zipfile
import datetime
import time
import subprocess
import stat
import distutils.dist
import distutils.command.install_egg_info

try:
    from unittest import mock
except ImportError:
    import mock

from pkg_resources import (
    DistInfoDistribution, Distribution, EggInfoDistribution,
)

import pytest

import pkg_resources


def timestamp(dt):
    """
    Return a timestamp for a local, naive datetime instance.
    """
    try:
        return dt.timestamp()
    except AttributeError:
        # Python 3.2 and earlier
        return time.mktime(dt.timetuple())


class EggRemover(str):
    def __call__(self):
        if self in sys.path:
            sys.path.remove(self)
        if os.path.exists(self):
            os.remove(self)


class TestZipProvider:
    finalizers = []

    ref_time = datetime.datetime(2013, 5, 12, 13, 25, 0)
    "A reference time for a file modification"

    @classmethod
    def setup_class(cls):
        "create a zip egg and add it to sys.path"
        egg = tempfile.NamedTemporaryFile(suffix='.egg', delete=False)
        zip_egg = zipfile.ZipFile(egg, 'w')
        zip_info = zipfile.ZipInfo()
        zip_info.filename = 'mod.py'
        zip_info.date_time = cls.ref_time.timetuple()
        zip_egg.writestr(zip_info, 'x = 3\n')
        zip_info = zipfile.ZipInfo()
        zip_info.filename = 'data.dat'
        zip_info.date_time = cls.ref_time.timetuple()
        zip_egg.writestr(zip_info, 'hello, world!')
        zip_info = zipfile.ZipInfo()
        zip_info.filename = 'subdir/mod2.py'
        zip_info.date_time = cls.ref_time.timetuple()
        zip_egg.writestr(zip_info, 'x = 6\n')
        zip_info = zipfile.ZipInfo()
        zip_info.filename = 'subdir/data2.dat'
        zip_info.date_time = cls.ref_time.timetuple()
        zip_egg.writestr(zip_info, 'goodbye, world!')
        zip_egg.close()
        egg.close()

        sys.path.append(egg.name)
        subdir = os.path.join(egg.name, 'subdir')
        sys.path.append(subdir)
        cls.finalizers.append(EggRemover(subdir))
        cls.finalizers.append(EggRemover(egg.name))

    @classmethod
    def teardown_class(cls):
        for finalizer in cls.finalizers:
            finalizer()

    def test_resource_listdir(self):
        import mod
        zp = pkg_resources.ZipProvider(mod)

        expected_root = ['data.dat', 'mod.py', 'subdir']
        assert sorted(zp.resource_listdir('')) == expected_root

        expected_subdir = ['data2.dat', 'mod2.py']
        assert sorted(zp.resource_listdir('subdir')) == expected_subdir
        assert sorted(zp.resource_listdir('subdir/')) == expected_subdir

        assert zp.resource_listdir('nonexistent') == []
        assert zp.resource_listdir('nonexistent/') == []

        import mod2
        zp2 = pkg_resources.ZipProvider(mod2)

        assert sorted(zp2.resource_listdir('')) == expected_subdir

        assert zp2.resource_listdir('subdir') == []
        assert zp2.resource_listdir('subdir/') == []

    def test_resource_filename_rewrites_on_change(self):
        """
        If a previous call to get_resource_filename has saved the file, but
        the file has been subsequently mutated with different file of the
        same size and modification time, it should not be overwritten on a
        subsequent call to get_resource_filename.
        """
        import mod
        manager = pkg_resources.ResourceManager()
        zp = pkg_resources.ZipProvider(mod)
        filename = zp.get_resource_filename(manager, 'data.dat')
        actual = datetime.datetime.fromtimestamp(os.stat(filename).st_mtime)
        assert actual == self.ref_time
        f = open(filename, 'w')
        f.write('hello, world?')
        f.close()
        ts = timestamp(self.ref_time)
        os.utime(filename, (ts, ts))
        filename = zp.get_resource_filename(manager, 'data.dat')
        with open(filename) as f:
            assert f.read() == 'hello, world!'
        manager.cleanup_resources()


class TestResourceManager:
    def test_get_cache_path(self):
        mgr = pkg_resources.ResourceManager()
        path = mgr.get_cache_path('foo')
        type_ = str(type(path))
        message = "Unexpected type from get_cache_path: " + type_
        assert isinstance(path, str), message

    def test_get_cache_path_race(self, tmpdir):
        # Patch to os.path.isdir to create a race condition
        def patched_isdir(dirname, unpatched_isdir=pkg_resources.isdir):
            patched_isdir.dirnames.append(dirname)

            was_dir = unpatched_isdir(dirname)
            if not was_dir:
                os.makedirs(dirname)
            return was_dir

        patched_isdir.dirnames = []

        # Get a cache path with a "race condition"
        mgr = pkg_resources.ResourceManager()
        mgr.set_extraction_path(str(tmpdir))

        archive_name = os.sep.join(('foo', 'bar', 'baz'))
        with mock.patch.object(pkg_resources, 'isdir', new=patched_isdir):
            mgr.get_cache_path(archive_name)

        # Because this test relies on the implementation details of this
        # function, these assertions are a sentinel to ensure that the
        # test suite will not fail silently if the implementation changes.
        called_dirnames = patched_isdir.dirnames
        assert len(called_dirnames) == 2
        assert called_dirnames[0].split(os.sep)[-2:] == ['foo', 'bar']
        assert called_dirnames[1].split(os.sep)[-1:] == ['foo']

    """
    Tests to ensure that pkg_resources runs independently from setuptools.
    """

    def test_setuptools_not_imported(self):
        """
        In a separate Python environment, import pkg_resources and assert
        that action doesn't cause setuptools to be imported.
        """
        lines = (
            'import pkg_resources',
            'import sys',
            (
                'assert "setuptools" not in sys.modules, '
                '"setuptools was imported"'
            ),
        )
        cmd = [sys.executable, '-c', '; '.join(lines)]
        subprocess.check_call(cmd)


def make_test_distribution(metadata_path, metadata):
    """
    Make a test Distribution object, and return it.

    :param metadata_path: the path to the metadata file that should be
        created. This should be inside a distribution directory that should
        also be created. For example, an argument value might end with
        "<project>.dist-info/METADATA".
    :param metadata: the desired contents of the metadata file, as bytes.
    """
    dist_dir = os.path.dirname(metadata_path)
    os.mkdir(dist_dir)
    with open(metadata_path, 'wb') as f:
        f.write(metadata)
    dists = list(pkg_resources.distributions_from_metadata(dist_dir))
    dist, = dists

    return dist


def test_get_metadata__bad_utf8(tmpdir):
    """
    Test a metadata file with bytes that can't be decoded as utf-8.
    """
    filename = 'METADATA'
    # Convert the tmpdir LocalPath object to a string before joining.
    metadata_path = os.path.join(str(tmpdir), 'foo.dist-info', filename)
    # Encode a non-ascii string with the wrong encoding (not utf-8).
    metadata = 'née'.encode('iso-8859-1')
    dist = make_test_distribution(metadata_path, metadata=metadata)

    with pytest.raises(UnicodeDecodeError) as excinfo:
        dist.get_metadata(filename)

    exc = excinfo.value
    actual = str(exc)
    expected = (
        # The error message starts with "'utf-8' codec ..." However, the
        # spelling of "utf-8" can vary (e.g. "utf8") so we don't include it
        "codec can't decode byte 0xe9 in position 1: "
        'invalid continuation byte in METADATA file at path: '
    )
    assert expected in actual, 'actual: {}'.format(actual)
    assert actual.endswith(metadata_path), 'actual: {}'.format(actual)


def make_distribution_no_version(tmpdir, basename):
    """
    Create a distribution directory with no file containing the version.
    """
    dist_dir = tmpdir / basename
    dist_dir.ensure_dir()
    # Make the directory non-empty so distributions_from_metadata()
    # will detect it and yield it.
    dist_dir.join('temp.txt').ensure()

    if sys.version_info < (3, 6):
        dist_dir = str(dist_dir)

    dists = list(pkg_resources.distributions_from_metadata(dist_dir))
    assert len(dists) == 1
    dist, = dists

    return dist, dist_dir


@pytest.mark.parametrize(
    'suffix, expected_filename, expected_dist_type',
    [
        ('egg-info', 'PKG-INFO', EggInfoDistribution),
        ('dist-info', 'METADATA', DistInfoDistribution),
    ],
)
def test_distribution_version_missing(
        tmpdir, suffix, expected_filename, expected_dist_type):
    """
    Test Distribution.version when the "Version" header is missing.
    """
    basename = 'foo.{}'.format(suffix)
    dist, dist_dir = make_distribution_no_version(tmpdir, basename)

    expected_text = (
        "Missing 'Version:' header and/or {} file at path: "
    ).format(expected_filename)
    metadata_path = os.path.join(dist_dir, expected_filename)

    # Now check the exception raised when the "version" attribute is accessed.
    with pytest.raises(ValueError) as excinfo:
        dist.version

    err = str(excinfo.value)
    # Include a string expression after the assert so the full strings
    # will be visible for inspection on failure.
    assert expected_text in err, str((expected_text, err))

    # Also check the args passed to the ValueError.
    msg, dist = excinfo.value.args
    assert expected_text in msg
    # Check that the message portion contains the path.
    assert metadata_path in msg, str((metadata_path, msg))
    assert type(dist) == expected_dist_type


def test_distribution_version_missing_undetected_path():
    """
    Test Distribution.version when the "Version" header is missing and
    the path can't be detected.
    """
    # Create a Distribution object with no metadata argument, which results
    # in an empty metadata provider.
    dist = Distribution('/foo')
    with pytest.raises(ValueError) as excinfo:
        dist.version

    msg, dist = excinfo.value.args
    expected = (
        "Missing 'Version:' header and/or PKG-INFO file at path: "
        '[could not detect]'
    )
    assert msg == expected


@pytest.mark.parametrize('only', [False, True])
def test_dist_info_is_not_dir(tmp_path, only):
    """Test path containing a file with dist-info extension."""
    dist_info = tmp_path / 'foobar.dist-info'
    dist_info.touch()
    assert not pkg_resources.dist_factory(str(tmp_path), str(dist_info), only)


class TestDeepVersionLookupDistutils:
    @pytest.fixture
    def env(self, tmpdir):
        """
        Create a package environment, similar to a virtualenv,
        in which packages are installed.
        """

        class Environment(str):
            pass

        env = Environment(tmpdir)
        tmpdir.chmod(stat.S_IRWXU)
        subs = 'home', 'lib', 'scripts', 'data', 'egg-base'
        env.paths = dict(
            (dirname, str(tmpdir / dirname))
            for dirname in subs
        )
        list(map(os.mkdir, env.paths.values()))
        return env

    def create_foo_pkg(self, env, version):
        """
        Create a foo package installed (distutils-style) to env.paths['lib']
        as version.
        """
        ld = "This package has unicode metadata! ❄"
        attrs = dict(name='foo', version=version, long_description=ld)
        dist = distutils.dist.Distribution(attrs)
        iei_cmd = distutils.command.install_egg_info.install_egg_info(dist)
        iei_cmd.initialize_options()
        iei_cmd.install_dir = env.paths['lib']
        iei_cmd.finalize_options()
        iei_cmd.run()

    def test_version_resolved_from_egg_info(self, env):
        version = '1.11.0.dev0+2329eae'
        self.create_foo_pkg(env, version)

        # this requirement parsing will raise a VersionConflict unless the
        # .egg-info file is parsed (see #419 on BitBucket)
        req = pkg_resources.Requirement.parse('foo>=1.9')
        dist = pkg_resources.WorkingSet([env.paths['lib']]).find(req)
        assert dist.version == version

    @pytest.mark.parametrize(
        'unnormalized, normalized',
        [
            ('foo', 'foo'),
            ('foo/', 'foo'),
            ('foo/bar', 'foo/bar'),
            ('foo/bar/', 'foo/bar'),
        ],
    )
    def test_normalize_path_trailing_sep(self, unnormalized, normalized):
        """Ensure the trailing slash is cleaned for path comparison.

        See pypa/setuptools#1519.
        """
        result_from_unnormalized = pkg_resources.normalize_path(unnormalized)
        result_from_normalized = pkg_resources.normalize_path(normalized)
        assert result_from_unnormalized == result_from_normalized

    @pytest.mark.skipif(
        os.path.normcase('A') != os.path.normcase('a'),
        reason='Testing case-insensitive filesystems.',
    )
    @pytest.mark.parametrize(
        'unnormalized, normalized',
        [
            ('MiXeD/CasE', 'mixed/case'),
        ],
    )
    def test_normalize_path_normcase(self, unnormalized, normalized):
        """Ensure mixed case is normalized on case-insensitive filesystems.
        """
        result_from_unnormalized = pkg_resources.normalize_path(unnormalized)
        result_from_normalized = pkg_resources.normalize_path(normalized)
        assert result_from_unnormalized == result_from_normalized

    @pytest.mark.skipif(
        os.path.sep != '\\',
        reason='Testing systems using backslashes as path separators.',
    )
    @pytest.mark.parametrize(
        'unnormalized, expected',
        [
            ('forward/slash', 'forward\\slash'),
            ('forward/slash/', 'forward\\slash'),
            ('backward\\slash\\', 'backward\\slash'),
        ],
    )
    def test_normalize_path_backslash_sep(self, unnormalized, expected):
        """Ensure path seps are cleaned on backslash path sep systems.
        """
        result = pkg_resources.normalize_path(unnormalized)
        assert result.endswith(expected)
