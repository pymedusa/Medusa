import os
import locale
import json
import sys
from pkg_resources import get_distribution
import xml.etree.ElementTree as ET
from ctypes import *

if sys.version_info < (3,):
    import urlparse
else:
    import urllib.parse as urlparse

__version__ = get_distribution("pymediainfo").version

class Track(object):
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
        data = {}
        for k, v in self.__dict__.items():
            if k != 'xml_dom_fragment':
                data[k] = v
        return data


class MediaInfo(object):
    def __init__(self, xml):
        self.xml_dom = MediaInfo.parse_xml_data_into_dom(xml)

    @staticmethod
    def parse_xml_data_into_dom(xml_data):
        try:
            return ET.fromstring(xml_data.encode("utf-8"))
        except:
            return None
    @staticmethod
    def _get_library():
        if os.name in ("nt", "dos", "os2", "ce"):
            return windll.MediaInfo
        elif sys.platform == "darwin":
            try:
                return CDLL("libmediainfo.0.dylib")
            except OSError:
                return CDLL("libmediainfo.dylib")
        else:
            return CDLL("libmediainfo.so.0")
    @classmethod
    def can_parse(cls):
        try:
            cls._get_library()
            return True
        except:
            return False
    @classmethod
    def parse(cls, filename):
        lib = cls._get_library()
        url = urlparse.urlparse(filename)
        # Test whether the filename is actually a URL
        if url.scheme is None:
            # Test file is readable
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
        # Create a MediaInfo handle
        handle = lib.MediaInfo_New()
        lib.MediaInfo_Option(handle, "CharSet", "UTF-8")
        # Fix for https://github.com/sbraz/pymediainfo/issues/22
        # Python 2 does not change LC_CTYPE
        # at startup: https://bugs.python.org/issue6203
        if (sys.version_info < (3,) and os.name == "posix"
                and locale.getlocale() == (None, None)):
            locale.setlocale(locale.LC_CTYPE, locale.getdefaultlocale())
        lib.MediaInfo_Option(None, "Inform", "XML")
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
        if not hasattr(self, "_tracks"):
            self._tracks = []
        if len(self._tracks) == 0:
            self._populate_tracks()
        return self._tracks
    def to_data(self):
        data = {'tracks': []}
        for track in self.tracks:
            data['tracks'].append(track.to_data())
        return data
    def to_json(self):
        return json.dumps(self.to_data())
