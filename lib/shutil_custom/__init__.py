import os
import stat
from io import open
from shutil import SpecialFileError, _samefile
try:
    from shutil import SameFileError
except ImportError:
    from shutil import Error as SameFileError


BUFFER_SIZE = 1024 * 1024 if os.name == 'nt' else 16 * 1024


def copyfile_custom(src, dst):
    """Copy data from src to dst."""
    def special_file(fn):
        try:
            st = os.stat(fn)
        except OSError:
            # File most likely does not exist
            pass
        else:
            if stat.S_ISFIFO(st.st_mode):
                raise SpecialFileError("{!r} is a named pipe".format(fn))

    if _samefile(src, dst):
        raise SameFileError("{!r} and {!r} are the same file".format(src, dst))

    special_file(src)
    special_file(dst)

    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        while True:
            buf = fsrc.read(BUFFER_SIZE)
            if not buf:
                break
            fdst.write(buf)
