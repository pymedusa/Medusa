import os
import stat
from shutil import SpecialFileError, _samefile
try:
    from shutil import SameFileError
except ImportError:
    from shutil import Error as SameFileError

try:
    O_BINARY = os.O_BINARY  # Windows
except AttributeError:
    O_BINARY = 0


READ_FLAGS = os.O_RDONLY | O_BINARY
WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | O_BINARY
BUFFER_SIZE = 128*1024


def copyfile_custom(src, dst):
    """Copy data from src to dst."""
    def special_file(fn):
        try:
            st = os.stat(fn)
        except OSError:  # File most likely does not exist
            pass
        else:
            if stat.S_ISFIFO(st.st_mode):
                raise SpecialFileError("`%s` is a named pipe" % fn)

    fdin = os.open(src, READ_FLAGS)
    fdout = os.open(dst, WRITE_FLAGS)
    with os.fdopen(fdin) as fin, os.fdopen(fdout) as fout:
        if _samefile(src, dst):
            raise SameFileError("`%s` and `%s` are the same file" % (src, dst))

        special_file(src)
        special_file(dst)

        while True:
            data = fin.read(BUFFER_SIZE)
            if data == '':
                break
            fout.write(data)
