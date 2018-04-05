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
    XML output can be obtained using the `XML` output format on versions older than v17.10
    and the `OLDXML` format on newer versions.

    Using such an XML file, we can create a :class:`MediaInfo` object:

    >>> with open("output.xml") as f:
    ...     mi = pymediainfo.MediaInfo(f.read())

    :param str xml: XML output obtained from MediaInfo
    """
    def __init__(self, xml):
        self.xml_dom = MediaInfo._parse_xml_data_into_dom(xml)

    @staticmethod
    def _parse_xml_data_into_dom(xml_data):
        try:
            return ET.fromstring(xml_data.encode("utf-8"))
        except:
            return None
    @staticmethod
    def _get_library(library_file=None):
        os_is_nt = os.name in ("nt", "dos", "os2", "ce")
        if library_file is not None:
            if os_is_nt:
                return WinDLL(library_file)
            else:
                return CDLL(library_file)
        elif os_is_nt:
            return windll.MediaInfo
        elif sys.platform == "darwin":
            try:
                return CDLL("libmediainfo.0.dylib")
            except OSError:
                return CDLL("libmediainfo.dylib")
        else:
            return CDLL("libmediainfo.so.0")
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
    def parse(cls, filename, library_file=None):
        """
        Analyze a media file using libmediainfo.
        If libmediainfo is located in a non-standard location, the `library_file` parameter can be used:

        >>> pymediainfo.MediaInfo.parse("tests/data/sample.mkv",
        ...     library_file="/path/to/libmediainfo.dylib")

        :param filename: path to the media file which will be analyzed.
        :param str library_file: path to the libmediainfo library, this should only be used if the library cannot be auto-detected.
        :type filename: str or pathlib.Path
        :rtype: MediaInfo
        """
        lib = cls._get_library(library_file)
        if pathlib is not None and isinstance(filename, pathlib.PurePath):
            filename = str(filename)
        else:
            url = urlparse.urlparse(filename)
            # Test whether the filename is actually a URL
            if url.scheme is None:
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
        lib_version = [int(_) for _ in re.search("^MediaInfoLib - v(\S+)", lib_version).group(1).split(".")]
        # The XML option was renamed starting with version 17.10
        if lib_version >= [17, 10]:
            xml_option = "OLDXML"
        else:
            xml_option = "XML"
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
        lib.MediaInfo_Open(handle, filename)
        xml = lib.MediaInfo_Inform(handle, 0)
        # Delete the handle
        lib.MediaInfo_Close(handle)
        lib.MediaInfo_Delete(handle)
        return cls(xml)
    def _populate_tracks(self):
        if self.xml_dom is None:
            return
        iterator = "getiterator" if sys.version_info < (2, 7) else "iter"
        for xml_track in getattr(self.xml_dom, iterator)("track"):
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
            self._tracks = []
        if len(self._tracks) == 0:
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
        Returns a json representation of the object's :py:class:`Tracks <Track>`.

        :rtype: str
        """
        return json.dumps(self.to_data())
