# vim: set fileencoding=utf-8 :
import os
import re
import locale
import json
import sys
from pkg_resources import get_distribution, DistributionNotFound
import xml.etree.ElementTree as ET
from ctypes import *

try:
    import pathlib
except ImportError:
    pathlib = None

if sys.version_info < (3,):
    import urlparse
else:
    import urllib.parse as urlparse

try:
    __version__ = get_distribution("pymediainfo").version
except DistributionNotFound:
    __version__ = '3.2.1'
    pass

class Track(object):
    """
    An object associated with a media file track.

    Each :class:`Track` attribute corresponds to attributes parsed from MediaInfo's output.
    All attributes are lower case. Attributes that are present several times such as Duration
    yield a second attribute starting with `other_` which is a list of all alternative attribute values.

    When a non-existing attribute is accessed, `None` is returned.

    Example:

    >>> t = mi.tracks[0]
    >>> t
    <Track track_id='None', track_type='General'>
    >>> t.duration
    3000
    >>> t.to_data()["other_duration"]
    ['3 s 0 ms', '3 s 0 ms', '3 s 0 ms',
        '00:00:03.000', '00:00:03.000']
    >>> type(t.non_existing)
    NoneType

    All available attributes can be obtained by calling :func:`to_data`.
    """
    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except:
            pass
        return None
    def __init__(self, xml_dom_fragment):
        self.xml_dom_fragment = xml_dom_fragment
        self.track_type = xml_dom_fragment.attrib['type']
        for el in self.xml_dom_fragment:
            node_name = el.tag.lower().strip().strip('_')
            if node_name == 'id':
                node_name = 'track_id'
            node_value = el.text
            other_node_name = "other_%s" % node_name
            if getattr(self, node_name) is None:
                setattr(self, node_name, node_value)
            else:
                if getattr(self, other_node_name) is None:
                    setattr(self, other_node_name, [node_value, ])
                else:
                    getattr(self, other_node_name).append(node_value)

        for o in [d for d in self.__dict__.keys() if d.startswith('other_')]:
            try:
                primary = o.replace('other_', '')
                setattr(self, primary, int(getattr(self, primary)))
            except:
                for v in getattr(self, o):
                    try:
                        current = getattr(self, primary)
                        setattr(self, primary, int(v))
                        getattr(self, o).append(current)
                        break
                    except:
                        pass
    def __repr__(self):
        return("<Track track_id='{0}', track_type='{1}'>".format(self.track_id, self.track_type))
    def to_data(self):
        """
        Returns a dict representation of the track attributes.

        Example:

        >>> sorted(track.to_data().keys())[:3]
        ['codec', 'codec_extensions_usually_used', 'codec_url']
        >>> t.to_data()["file_size"]
        5988


        :rtype: dict
        """
        data = {}
        for k, v in self.__dict__.items():
            if k != 'xml_dom_fragment':
                data[k] = v
        return data


class MediaInfo(object):
    """
    An object containing information about a media file.


    :class:`MediaInfo` objects can be created by directly calling code from
    libmediainfo (in this case, the library must be present on the system):

    >>> pymediainfo.MediaInfo.parse("/path/to/file.mp4")

    Alternatively, objects may be created from MediaInfo's XML output.
    Such output can be obtained using the ``XML`` output format on versions older than v17.10
    and the ``OLDXML`` format on newer versions.

    Using such an XML file, we can create a :class:`MediaInfo` object:

    >>> with open("output.xml") as f:
    ...     mi = pymediainfo.MediaInfo(f.read())

    :param str xml: XML output obtained from MediaInfo.
    :param str encoding_errors: option to pass to :func:`str.encode`'s `errors`
        parameter before parsing `xml`.
    :raises xml.etree.ElementTree.ParseError: if passed invalid XML (Python ≥ 2.7).
    :raises xml.parsers.expat.ExpatError: if passed invalid XML (Python 2.6).
    """
    def __init__(self, xml, encoding_errors="strict"):
        self.xml_dom = MediaInfo._parse_xml_data_into_dom(xml, encoding_errors)
    @staticmethod
    def _parse_xml_data_into_dom(xml_data, encoding_errors="strict"):
        return ET.fromstring(xml_data.encode("utf-8", encoding_errors))
    @staticmethod
    def _get_library(library_file=None):
        os_is_nt = os.name in ("nt", "dos", "os2", "ce")
        if os_is_nt:
            lib_type = WinDLL
        else:
            lib_type = CDLL
        if library_file is None:
            if os_is_nt:
                library_names = ("MediaInfo.dll",)
            elif sys.platform == "darwin":
                library_names = ("libmediainfo.0.dylib", "libmediainfo.dylib")
            else:
                library_names = ("libmediainfo.so.0",)
            script_dir = os.path.dirname(__file__)
            # Look for the library file in the script folder
            for library in library_names:
                lib_path = os.path.join(script_dir, library)
                if os.path.isfile(lib_path):
                    # If we find it, don't try any other filename
                    library_names = (lib_path,)
                    break
        else:
            library_names = (library_file,)
        for i, library in enumerate(library_names, start=1):
            try:
                return lib_type(library)
            except OSError:
                # If we've tried all possible filenames
                if i == len(library_names):
                    raise
    @classmethod
    def can_parse(cls, library_file=None):
        """
        Checks whether media files can be analyzed using libmediainfo.

        :rtype: bool
        """
        try:
            cls._get_library(library_file)
            return True
        except:
            return False
    @classmethod
    def parse(cls, filename, library_file=None, cover_data=False,
            encoding_errors="strict", parse_speed=0.5):
        """
        Analyze a media file using libmediainfo.
        If libmediainfo is located in a non-standard location, the `library_file` parameter can be used:

        >>> pymediainfo.MediaInfo.parse("tests/data/sample.mkv",
        ...     library_file="/path/to/libmediainfo.dylib")

        :param filename: path to the media file which will be analyzed.
            A URL can also be used if libmediainfo was compiled
            with CURL support.
        :param str library_file: path to the libmediainfo library, this should only be used if the library cannot be auto-detected.
        :param bool cover_data: whether to retrieve cover data as base64.
        :param str encoding_errors: option to pass to :func:`str.encode`'s `errors`
            parameter before parsing MediaInfo's XML output.
        :param float parse_speed: passed to the library as `ParseSpeed`,
            this option takes values between 0 and 1.
            A higher value will yield more precise results in some cases
            but will also increase parsing time.
        :type filename: str or pathlib.Path
        :rtype: MediaInfo
        :raises FileNotFoundError: if passed a non-existent file
            (Python ≥ 3.3), does not work on Windows.
        :raises IOError: if passed a non-existent file (Python < 3.3),
            does not work on Windows.
        :raises RuntimeError: if parsing fails, this should not
            happen unless libmediainfo itself fails.
        """
        lib = cls._get_library(library_file)
        if pathlib is not None and isinstance(filename, pathlib.PurePath):
            filename = str(filename)
            url = False
        else:
            url = urlparse.urlparse(filename)
        # Try to open the file (if it's not a URL)
        # Doesn't work on Windows because paths are URLs
        if not (url and url.scheme):
            # Test whether the file is readable
            with open(filename, "rb"):
                pass
        # Define arguments and return types
        lib.MediaInfo_Inform.restype = c_wchar_p
        lib.MediaInfo_New.argtypes = []
        lib.MediaInfo_New.restype  = c_void_p
        lib.MediaInfo_Option.argtypes = [c_void_p, c_wchar_p, c_wchar_p]
        lib.MediaInfo_Option.restype = c_wchar_p
        lib.MediaInfo_Inform.argtypes = [c_void_p, c_size_t]
        lib.MediaInfo_Inform.restype = c_wchar_p
        lib.MediaInfo_Open.argtypes = [c_void_p, c_wchar_p]
        lib.MediaInfo_Open.restype = c_size_t
        lib.MediaInfo_Delete.argtypes = [c_void_p]
        lib.MediaInfo_Delete.restype  = None
        lib.MediaInfo_Close.argtypes = [c_void_p]
        lib.MediaInfo_Close.restype = None
        # Obtain the library version
        lib_version = lib.MediaInfo_Option(None, "Info_Version", "")
        lib_version = tuple(int(_) for _ in re.search("^MediaInfoLib - v(\\S+)", lib_version).group(1).split("."))
        # The XML option was renamed starting with version 17.10
        if lib_version >= (17, 10):
            xml_option = "OLDXML"
        else:
            xml_option = "XML"
        # Cover_Data is not extracted by default since version 18.03
        # See https://github.com/MediaArea/MediaInfoLib/commit/d8fd88a1c282d1c09388c55ee0b46029e7330690
        if cover_data and lib_version >= (18, 3):
            lib.MediaInfo_Option(None, "Cover_Data", "base64")
        # Create a MediaInfo handle
        handle = lib.MediaInfo_New()
        lib.MediaInfo_Option(handle, "CharSet", "UTF-8")
        # Fix for https://github.com/sbraz/pymediainfo/issues/22
        # Python 2 does not change LC_CTYPE
        # at startup: https://bugs.python.org/issue6203
        if (sys.version_info < (3,) and os.name == "posix"
                and locale.getlocale() == (None, None)):
            locale.setlocale(locale.LC_CTYPE, locale.getdefaultlocale())
        lib.MediaInfo_Option(None, "Inform", xml_option)
        lib.MediaInfo_Option(None, "Complete", "1")
        lib.MediaInfo_Option(None, "ParseSpeed", str(parse_speed))
        if lib.MediaInfo_Open(handle, filename) == 0:
            raise RuntimeError("An eror occured while opening {0}"
                    " with libmediainfo".format(filename))
        xml = lib.MediaInfo_Inform(handle, 0)
        # Delete the handle
        lib.MediaInfo_Close(handle)
        lib.MediaInfo_Delete(handle)
        return cls(xml, encoding_errors)
    def _populate_tracks(self):
        self._tracks = []
        iterator = "findall" if sys.version_info < (2, 7) else "iterfind"
        # This is the case for libmediainfo < 18.03
        # https://github.com/sbraz/pymediainfo/issues/57
        # https://github.com/MediaArea/MediaInfoLib/commit/575a9a32e6960ea34adb3bc982c64edfa06e95eb
        if self.xml_dom.tag == "File":
            xpath = "track"
        else:
            xpath = "File/track"
        for xml_track in getattr(self.xml_dom, iterator)(xpath):
            self._tracks.append(Track(xml_track))
    @property
    def tracks(self):
        """
        A list of :py:class:`Track` objects which the media file contains.

        For instance:

        >>> mi = pymediainfo.MediaInfo.parse("/path/to/file.mp4")
        >>> for t in mi.tracks:
        ...     print(t)
        <Track track_id='None', track_type='General'>
        <Track track_id='1', track_type='Text'>
        """
        if not hasattr(self, "_tracks"):
            self._populate_tracks()
        return self._tracks
    def to_data(self):
        """
        Returns a dict representation of the object's :py:class:`Tracks <Track>`.

        :rtype: dict
        """
        data = {'tracks': []}
        for track in self.tracks:
            data['tracks'].append(track.to_data())
        return data
    def to_json(self):
        """
        Returns a JSON representation of the object's :py:class:`Tracks <Track>`.

        :rtype: str
        """
        return json.dumps(self.to_data())
