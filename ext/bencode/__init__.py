# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Petru Paler

"""bencode.py - bencode encoder + decoder."""

from bencode.BTL import BTFailure
from bencode.exceptions import BencodeDecodeError

from collections import deque
import sys

try:
    from typing import Dict, List, Tuple, Deque, Union, TextIO, BinaryIO, Any
except ImportError:
    Dict = List = Tuple = Deque = Union = TextIO = BinaryIO = Any = None

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = None

try:
    import pathlib
except ImportError:
    pathlib = None

__all__ = (
    'BTFailure',
    'BencodeDecodeError',
    'bencode',
    'bdecode',
    'bread',
    'bwrite',
    'encode',
    'decode'
)


def decode_int(x, f):
    # type: (bytes, int) -> Tuple[int, int]
    f += 1
    newf = x.index(b'e', f)
    n = int(x[f:newf])

    if x[f:f + 1] == b'-':
        if x[f + 1:f + 2] == b'0':
            raise ValueError
    elif x[f:f + 1] == b'0' and newf != f + 1:
        raise ValueError

    return n, newf + 1


def decode_string(x, f, try_decode_utf8=True, force_decode_utf8=False):
    # type: (bytes, int, bool, bool) -> Tuple[bytes, int]
    """Decode torrent bencoded 'string' in x starting at f.

    An attempt is made to convert the string to a python string from utf-8.
    However, both string and non-string binary data is intermixed in the
    torrent bencoding standard. So we have to guess whether the byte
    sequence is a string or just binary data. We make this guess by trying
    to decode (from utf-8), and if that fails, assuming it is binary data.
    There are some instances where the data SHOULD be a string though.
    You can check enforce this by setting force_decode_utf8 to True. If the
    decoding from utf-8 fails, an UnidcodeDecodeError is raised. Similarly,
    if you know it should not be a string, you can skip the decoding
    attempt by setting try_decode_utf8=False.
    """
    colon = x.index(b':', f)
    n = int(x[f:colon])

    if x[f:f + 1] == b'0' and colon != f + 1:
        raise ValueError

    colon += 1
    s = x[colon:colon + n]

    if try_decode_utf8:
        try:
            return s.decode('utf-8'), colon + n
        except UnicodeDecodeError:
            if force_decode_utf8:
                raise

    return bytes(s), colon + n


def decode_list(x, f):
    # type: (bytes, int) -> Tuple[List, int]
    r, f = [], f + 1

    while x[f:f + 1] != b'e':
        v, f = decode_func[x[f:f + 1]](x, f)
        r.append(v)

    return r, f + 1


def decode_dict_py26(x, f):
    # type: (bytes, int) -> Tuple[Dict[str, Any], int]
    r, f = {}, f + 1

    while x[f] != 'e':
        k, f = decode_string(x, f)
        r[k], f = decode_func[x[f]](x, f)

    return r, f + 1


def decode_dict(x, f, force_sort=True):
    # type: (bytes, int, bool) -> Tuple[OrderedDict[str, Any], int]
    """Decode bencoded data to an OrderedDict.

    The BitTorrent standard states that:
        Keys must be strings and appear in sorted order (sorted as raw
        strings, not alphanumerics)
    - http://www.bittorrent.org/beps/bep_0003.html

    Therefore, this function will force the keys to be strings (decoded
    from utf-8), and by default the keys are (re)sorted after reading.
    Set force_sort to False to keep the order of the dictionary as
    represented in x, as many other encoders and decoders do not force this
    property.
    """

    r, f = OrderedDict(), f + 1

    while x[f:f + 1] != b'e':
        k, f = decode_string(x, f, force_decode_utf8=True)
        r[k], f = decode_func[x[f:f + 1]](x, f)

    if force_sort:
        r = OrderedDict(sorted(r.items()))

    return r, f + 1


# noinspection PyDictCreation
decode_func = {}
decode_func[b'l'] = decode_list
decode_func[b'i'] = decode_int
decode_func[b'0'] = decode_string
decode_func[b'1'] = decode_string
decode_func[b'2'] = decode_string
decode_func[b'3'] = decode_string
decode_func[b'4'] = decode_string
decode_func[b'5'] = decode_string
decode_func[b'6'] = decode_string
decode_func[b'7'] = decode_string
decode_func[b'8'] = decode_string
decode_func[b'9'] = decode_string

if sys.version_info[0] == 2 and sys.version_info[1] == 6:
    decode_func[b'd'] = decode_dict_py26
else:
    decode_func[b'd'] = decode_dict


def bdecode(value):
    # type: (bytes) -> Union[Tuple, List, OrderedDict, bool, int, str, bytes]
    """
    Decode bencode formatted byte string ``value``.

    :param value: Bencode formatted string
    :type value: bytes

    :return: Decoded value
    :rtype: object
    """
    try:
        r, l = decode_func[value[0:1]](value, 0)
    except (IndexError, KeyError, TypeError, ValueError):
        raise BencodeDecodeError("not a valid bencoded string")

    if l != len(value):
        raise BencodeDecodeError("invalid bencoded value (data after valid prefix)")

    return r


class Bencached(object):
    __slots__ = ['bencoded']

    def __init__(self, s):
        self.bencoded = s


def encode_bencached(x, r):
    # type: (Bencached, Deque[bytes]) -> None
    r.append(x.bencoded)


def encode_int(x, r):
    # type: (int, Deque[bytes]) -> None
    r.extend((b'i', str(x).encode('utf-8'), b'e'))


def encode_bool(x, r):
    # type: (bool, Deque[bytes]) -> None
    if x:
        encode_int(1, r)
    else:
        encode_int(0, r)


def encode_bytes(x, r):
    # type: (bytes, Deque[bytes]) -> None
    r.extend((str(len(x)).encode('utf-8'), b':', x))


def encode_string(x, r):
    # type: (str, Deque[bytes]) -> None
    try:
        s = x.encode('utf-8')
    except UnicodeDecodeError:
        encode_bytes(x, r)
        return

    r.extend((str(len(s)).encode('utf-8'), b':', s))


def encode_list(x, r):
    # type: (List, Deque[bytes]) -> None
    r.append(b'l')

    for i in x:
        encode_func[type(i)](i, r)

    r.append(b'e')


def encode_dict(x, r):
    # type: (Dict, Deque[bytes]) -> None
    r.append(b'd')
    ilist = list(x.items())
    ilist.sort()

    for k, v in ilist:
        k = k.encode('utf-8')
        r.extend((str(len(k)).encode('utf-8'), b':', k))
        encode_func[type(v)](v, r)

    r.append(b'e')


# noinspection PyDictCreation
encode_func = {}
encode_func[Bencached] = encode_bencached

if sys.version_info[0] == 2:
    from types import DictType, IntType, ListType, LongType, StringType, TupleType, UnicodeType

    encode_func[DictType] = encode_dict
    encode_func[IntType] = encode_int
    encode_func[ListType] = encode_list
    encode_func[LongType] = encode_int
    encode_func[StringType] = encode_string
    encode_func[TupleType] = encode_list
    encode_func[UnicodeType] = encode_string

    if OrderedDict is not None:
        encode_func[OrderedDict] = encode_dict

    try:
        from types import BooleanType

        encode_func[BooleanType] = encode_bool
    except ImportError:
        pass
else:
    encode_func[OrderedDict] = encode_dict
    encode_func[bool] = encode_bool
    encode_func[dict] = encode_dict
    encode_func[int] = encode_int
    encode_func[list] = encode_list
    encode_func[str] = encode_string
    encode_func[tuple] = encode_list
    encode_func[bytes] = encode_bytes


def bencode(value):
    # type: (Union[Tuple, List, OrderedDict, Dict, bool, int, str, bytes]) -> bytes
    """
    Encode ``value`` into the bencode format.

    :param value: Value
    :type value: object

    :return: Bencode formatted string
    :rtype: str
    """
    r = deque()  # makes more sense for something with lots of appends

    # Encode provided value
    encode_func[type(value)](value, r)

    # Join parts
    return b''.join(r)


# Method proxies (for compatibility with other libraries)
decode = bdecode
encode = bencode


def bread(fd):
    # type: (Union[bytes, str, pathlib.Path, pathlib.PurePath, TextIO, BinaryIO]) -> bytes
    """Return bdecoded data from filename, file, or file-like object.

    if fd is a bytes/string or pathlib.Path-like object, it is opened and
    read, otherwise .read() is used. if read() not available, exception
    raised.
    """
    if isinstance(fd, (bytes, str)):
        with open(fd, 'rb') as fd:
            return bdecode(fd.read())
    elif pathlib is not None and isinstance(fd, (pathlib.Path, pathlib.PurePath)):
        with open(str(fd), 'rb') as fd:
            return bdecode(fd.read())
    else:
        return bdecode(fd.read())


def bwrite(data, fd):
    # type: (Union[Tuple, List, OrderedDict, Dict, bool, int, str, bytes], Union[bytes, str, pathlib.Path, pathlib.PurePath, TextIO, BinaryIO]) -> None
    """Write data in bencoded form to filename, file, or file-like object.

    if fd is bytes/string or pathlib.Path-like object, it is opened and
    written to, otherwise .write() is used. if write() is not available,
    exception raised.
    """
    if isinstance(fd, (bytes, str)):
        with open(fd, 'wb') as fd:
            fd.write(bencode(data))
    elif pathlib is not None and isinstance(fd, (pathlib.Path, pathlib.PurePath)):
        with open(str(fd), 'wb') as fd:
            fd.write(bencode(data))
    else:
        fd.write(bencode(data))
