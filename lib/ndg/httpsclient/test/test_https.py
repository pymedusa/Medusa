"""unit tests module for ndg.httpsclient.https.HTTPSconnection class

PyOpenSSL utility to make a httplib-like interface suitable for use with 
urllib2
"""
__author__ = "P J Kershaw (STFC)"
__date__ = "06/01/12"
__copyright__ = "(C) 2012 Science and Technology Facilities Council"
__license__ = "BSD - see LICENSE file in top-level directory"
__contact__ = "Philip.Kershaw@stfc.ac.uk"
__revision__ = '$Id$'
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
import unittest
import socket

from OpenSSL import SSL

from ndg.httpsclient.test import Constants
from ndg.httpsclient.https import HTTPSConnection
from ndg.httpsclient.ssl_peer_verification import ServerSSLCertVerification


class TestHTTPSConnection(unittest.TestCase):
    '''Test ndg HTTPS client HTTPSConnection class'''

    def test01_open(self):
        conn = HTTPSConnection(Constants.HOSTNAME, port=Constants.PORT)
        conn.connect()
        conn.request('GET', '/')
        resp = conn.getresponse()
        print('Response = %s' % resp.read())
        conn.close()

    def test02_open_fails(self):
        conn = HTTPSConnection(Constants.HOSTNAME, port=Constants.PORT2)
        self.assertRaises(socket.error, conn.connect)

    def test03_ssl_verification_of_peer_fails(self):
        ctx = SSL.Context(SSL.TLSv1_METHOD)
        
        def verify_callback(conn, x509, errnum, errdepth, preverify_ok): 
            log.debug('SSL peer certificate verification failed for %r',
                      x509.get_subject())
            return preverify_ok 
            
        ctx.set_verify(SSL.VERIFY_PEER, verify_callback)
        ctx.set_verify_depth(9)
        
        # Set bad location - unit test dir has no CA certs to verify with
        ctx.load_verify_locations(None, Constants.UNITTEST_DIR)
        
        conn = HTTPSConnection(Constants.HOSTNAME, port=Constants.PORT,
                               ssl_context=ctx)
        conn.connect()        
        self.assertRaises(SSL.Error, conn.request, 'GET', '/')

    def test03_ssl_verification_of_peer_succeeds(self):
        ctx = SSL.Context(SSL.TLSv1_METHOD)
        
        verify_callback = lambda conn, x509, errnum, errdepth, preverify_ok: \
            preverify_ok 
            
        ctx.set_verify(SSL.VERIFY_PEER, verify_callback)
        ctx.set_verify_depth(9)
        
        # Set correct location for CA certs to verify with
        ctx.load_verify_locations(None, Constants.CACERT_DIR)
        
        conn = HTTPSConnection(Constants.HOSTNAME, port=Constants.PORT,
                               ssl_context=ctx)
        conn.connect()
        conn.request('GET', '/')
        resp = conn.getresponse()
        print('Response = %s' % resp.read())

    def test04_ssl_verification_with_subj_alt_name(self):
        ctx = SSL.Context(SSL.TLSv1_METHOD)
        
        verification = ServerSSLCertVerification(hostname='localhost')
        verify_callback = verification.get_verify_server_cert_func()
        
        ctx.set_verify(SSL.VERIFY_PEER, verify_callback)
        ctx.set_verify_depth(9)
        
        # Set correct location for CA certs to verify with
        ctx.load_verify_locations(None, Constants.CACERT_DIR)
        
        conn = HTTPSConnection(Constants.HOSTNAME, port=Constants.PORT,
                               ssl_context=ctx)
        conn.connect()
        conn.request('GET', '/')
        resp = conn.getresponse()
        print('Response = %s' % resp.read())

    def test04_ssl_verification_with_subj_common_name(self):
        ctx = SSL.Context(SSL.TLSv1_METHOD)
        
        # Explicitly set verification of peer hostname using peer certificate
        # subject common name
        verification = ServerSSLCertVerification(hostname='localhost',
                                                 subj_alt_name_match=False)

        verify_callback = verification.get_verify_server_cert_func()
        
        ctx.set_verify(SSL.VERIFY_PEER, verify_callback)
        ctx.set_verify_depth(9)
        
        # Set correct location for CA certs to verify with
        ctx.load_verify_locations(None, Constants.CACERT_DIR)
        
        conn = HTTPSConnection(Constants.HOSTNAME, port=Constants.PORT,
                               ssl_context=ctx)
        conn.connect()
        conn.request('GET', '/')
        resp = conn.getresponse()
        print('Response = %s' % resp.read())

        
if __name__ == "__main__":
    unittest.main()