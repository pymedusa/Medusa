# coding=utf-8
import os
import site
import sys

from medusa import app


def _get_lib_location(relative_path):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', relative_path))


def _configure_syspath():
    """Add the vendored libraries into `sys.path`."""
    # Note: These paths will be inserted into `sys.path` in reverse order (LIFO)
    # So the last path on this list will be inserted as the first path on `sys.path`
    # right after the current working dir.
    # For example: [ cwd, pathN, ..., path1, path0, <rest_of_sys.path> ]

    paths_to_insert = [
        _get_lib_location(app.LIB_FOLDER),
        _get_lib_location(app.EXT_FOLDER)
    ]

    if sys.version_info[0] == 2:
        # Add Python 2-only vendored libraries
        paths_to_insert.extend([
            _get_lib_location(app.LIB2_FOLDER),
            _get_lib_location(app.EXT2_FOLDER)
        ])
    elif sys.version_info[0] == 3:
        # Add Python 3-only vendored libraries
        paths_to_insert.extend([
            _get_lib_location(app.LIB3_FOLDER),
            _get_lib_location(app.EXT3_FOLDER)
        ])

    # Insert paths into `sys.path` and handle `.pth` files
    # Inspired by: https://bugs.python.org/issue7744
    for dirpath in paths_to_insert:
        # Clear `sys.path`
        sys.path, remainder = sys.path[:1], sys.path[1:]
        # Add directory as a site-packages directory and handle `.pth` files
        site.addsitedir(dirpath)
        # Restore rest of `sys.path`
        sys.path.extend(remainder)


_configure_syspath()

sys._called_from_test = True
