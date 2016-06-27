"""unit tests module for ndg.httpsclient.urllib2_build_opener module

PyOpenSSL utility to make a httplib-like interface suitable for use with 
urllib2
"""
__author__ = "P J Kershaw (STFC)"
__date__ = "06/01/12"
__copyright__ = "(C) 2012 Science and Technology Facilities Council"
__license__ = "BSD - see LICENSE file in top-level directory"
__contact__ = "Philip.Kershaw@stfc.ac.uk"
__revision__ = '$Id$'
import sys

if sys.version_info[0] > 2:
    from urllib.error import URLError as URLError_
else:
    from urllib2 import URLError as URLError_
    
import unittest

from OpenSSL import SSL
from ndg.httpsclient.test import Constants
from ndg.httpsclient.urllib2_build_opener import build_opener


class Urllib2TestCase(unittest.TestCase):
    """Unit tests for urllib2 functionality"""
    
    def test01_urllib2_build_opener(self):     
        opener = build_opener()
        self.assertTrue(opener)

    def test02_open(self):
        opener = build_opener()
        res = opener.open(Constants.TEST_URI)
        self.assertTrue(res)
        print("res = %s" % res.read())

    def test03_open_fails_unknown_loc(self):
        opener = build_opener()
        self.assertRaises(URLError_, opener.open, Constants.TEST_URI2)
        
    def test04_open_peer_cert_verification_fails(self):
        # Explicitly set empty CA directory to make verification fail
        ctx = SSL.Context(SSL.TLSv1_METHOD)
        verify_callback = lambda conn, x509, errnum, errdepth, preverify_ok: \
            preverify_ok 
            
        ctx.set_verify(SSL.VERIFY_PEER, verify_callback)
        ctx.load_verify_locations(None, './')
        opener = build_opener(ssl_context=ctx)
        self.assertRaises(SSL.Error, opener.open, Constants.TEST_URI)
        
        
if __name__ == "__main__":
    unittest.main()
