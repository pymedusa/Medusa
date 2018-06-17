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

    with open(src, 'rb') as fin, open(dst, 'wb') as fout:
        if _samefile(src, dst):
            raise SameFileError("`%s` and `%s` are the same file" % (src, dst))

        special_file(src)
        special_file(dst)

        while True:
            data = fin.read(BUFFER_SIZE)
            if data == '':
                break
            fout.write(data)
